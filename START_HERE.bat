@echo off
title GELGOOG v2 System Boot
echo =================================================
echo 🤖 GELGOOG SYSTEM IS STARTING...
echo =================================================
echo Checking and installing required libraries...
pip install pyautogui opencv-python numpy pydirectinput mss keyboard >nul 2>&1
echo Libraries are ready!
echo.
python main.py
pause