"""Run this ONCE: python create_shortcut.py
Creates a 'Smart Study Monitor' shortcut on your Windows Desktop."""
import os
import subprocess

folder = os.path.dirname(os.path.abspath(__file__))
bat = os.path.join(folder, "start_monitor.bat")

ps = f'''
$desktop = [Environment]::GetFolderPath("Desktop")
$s = (New-Object -ComObject WScript.Shell).CreateShortcut("$desktop\\Smart Study Monitor.lnk")
$s.TargetPath = "{bat}"
$s.WorkingDirectory = "{folder}"
$s.WindowStyle = 7
$s.IconLocation = "$env:SystemRoot\\System32\\shell32.dll,168"
$s.Save()
Write-Output "Shortcut created on: $desktop"
'''
subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True)
