@echo off
rem DeskPet 桌面速记小企鹅 — 无控制台窗口启动
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" "run_deskpet.py"
