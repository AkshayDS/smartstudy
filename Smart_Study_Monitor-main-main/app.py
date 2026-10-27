import os
import time
import cv2
import cvzone
import pygame
from cvzone.FaceMeshModule import FaceMeshDetector
from ultralytics import YOLO

# Always work from this file's folder, so the desktop shortcut finds the audio/models
BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

# ---------------- AUDIO ----------------
pygame.mixer.init()
ALARMS = {
    "sleep": pygame.mixer.Sound("alarm.mp3"),    # sleeping
    "away":  pygame.mixer.Sound("faudio.mp3"),   # out of frame / face hidden
    "phone": pygame.mixer.Sound("paudio.mp3"),   # using mobile
    "yawn":  pygame.mixer.Sound("yawn.mp3"),     # yawning  <-- put your yawn audio here
}
MESSAGES = {
    "sleep": ("WAKE UP & STUDY!", (0, 0, 255)),
    "away":  ("COME BACK TO FRAME!", (0, 0, 255)),
    "phone": ("PUT THE PHONE AWAY!", (0, 165, 255)),
    "yawn":  ("YAWNING? TAKE A SHORT BREAK!", (0, 200, 255)),
}

# ---------------- SETTINGS (tune these) ----------------
EYE_CLOSED_RATIO = 80.0   # below this = eye closed
SLEEP_SECONDS = 2.0       # eyes closed this long = sleeping
AWAY_SECONDS = 3.0        # no face this long = out of frame
PHONE_SECONDS = 1.5       # phone visible this long = using phone
YAWN_MAR = 0.60           # mouth open ratio above this = wide open
YAWN_SECONDS = 1.2        # mouth wide open this long = yawn
PHONE_CONF = 0.5
YOLO_EVERY_N_FRAMES = 3
COCO_CELL_PHONE = 67

# Face mesh landmark indices
L_TOP, L_BOT, L_LEFT, L_RIGHT = 159, 145, 130, 243
R_TOP, R_BOT, R_LEFT, R_RIGHT = 386, 374, 359, 263
MOUTH_TOP, MOUTH_BOT, MOUTH_LEFT, MOUTH_RIGHT = 13, 14, 78, 308

# ---------------- INIT ----------------
cap = cv2.VideoCapture(0)
face_detector = FaceMeshDetector(maxFaces=1)
phone_model = YOLO("yolov8n.pt")

eyes_closed_since = None
face_missing_since = None
phone_seen_since = None
yawn_since = None

phone_box = None
frame_count = 0
current_alarm = None


def held_for(since, seconds):
    return since is not None and (time.time() - since) >= seconds


def ratio_of(face, a, b, c, d):
    v, _ = face_detector.findDistance(face[a], face[b])
    h, _ = face_detector.findDistance(face[c], face[d])
    return v / h if h else 0


while True:
    ok, img = cap.read()
    if not ok:
        break
    frame_count += 1
    now = time.time()

    # ---------- 1. FACE: sleep, yawn, out of frame ----------
    img, faces = face_detector.findFaceMesh(img, draw=False)

    if faces:
        face_missing_since = None
        face = faces[0]

        eye = (ratio_of(face, L_TOP, L_BOT, L_LEFT, L_RIGHT) +
               ratio_of(face, R_TOP, R_BOT, R_LEFT, R_RIGHT)) / 2 * 100
        mar = ratio_of(face, MOUTH_TOP, MOUTH_BOT, MOUTH_LEFT, MOUTH_RIGHT)
        cvzone.putTextRect(img, f"Eye: {eye:.1f}  Mouth: {mar:.2f}", (30, 40),
                           scale=1, thickness=1)

        mouth_wide = mar > YAWN_MAR
        if mouth_wide:
            if yawn_since is None:
                yawn_since = now
        else:
            yawn_since = None

        # Eyes squint during a yawn, so don't count that as sleeping
        if eye < EYE_CLOSED_RATIO and not mouth_wide:
            if eyes_closed_since is None:
                eyes_closed_since = now
        else:
            eyes_closed_since = None
    else:
        eyes_closed_since = None
        yawn_since = None
        if face_missing_since is None:
            face_missing_since = now

    # ---------- 2. PHONE (every N frames) ----------
    if frame_count % YOLO_EVERY_N_FRAMES == 0:
        phone_box = None
        results = phone_model.predict(img, classes=[COCO_CELL_PHONE],
                                      conf=PHONE_CONF, verbose=False)
        for r in results:
            if len(r.boxes):
                phone_box = tuple(map(int, r.boxes[0].xyxy[0]))
        if phone_box:
            if phone_seen_since is None:
                phone_seen_since = now
        else:
            phone_seen_since = None

    if phone_box:
        x1, y1, x2, y2 = phone_box
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 255), 2)

    # ---------- 3. DECIDE ALARM (away > sleep > yawn > phone) ----------
    if held_for(face_missing_since, AWAY_SECONDS):
        wanted = "away"
    elif held_for(eyes_closed_since, SLEEP_SECONDS):
        wanted = "sleep"
    elif held_for(yawn_since, YAWN_SECONDS):
        wanted = "yawn"
    elif held_for(phone_seen_since, PHONE_SECONDS):
        wanted = "phone"
    else:
        wanted = None

    if wanted:
        text, color = MESSAGES[wanted]
        cvzone.putTextRect(img, text, (50, 100), scale=2, thickness=3, colorR=color)
        if not pygame.mixer.get_busy():
            ALARMS[wanted].play()
            current_alarm = wanted
        elif current_alarm != wanted:
            pygame.mixer.stop()
            ALARMS[wanted].play()
            current_alarm = wanted
    else:
        if pygame.mixer.get_busy():
            pygame.mixer.stop()
        current_alarm = None

    cv2.imshow("Smart Study Monitor", img)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
