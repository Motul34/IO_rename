@echo off
echo Installing PyInstaller...
uv add pyinstaller
echo Building EXE...
uv run pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." ^
 --exclude-module PyQt6.QtNetwork ^
 --exclude-module PyQt6.QtQml ^
 --exclude-module PyQt6.QtSql ^
 --exclude-module PyQt6.QtQuick ^
 --exclude-module PyQt6.QtWebEngine ^
 --exclude-module PyQt6.QtWebEngineCore ^
 --exclude-module PyQt6.QtWebEngineWidgets ^
 --exclude-module PyQt6.QtTest ^
 --exclude-module PyQt6.QtBluetooth ^
 --exclude-module PyQt6.QtSensors ^
 --exclude-module PyQt6.QtPrintSupport ^
 --exclude-module tkinter ^
 main.py -n IO_Editor
echo Build complete. Check the 'dist' folder.
pause
