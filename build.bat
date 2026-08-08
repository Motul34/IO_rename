@echo off
echo Installing PyInstaller...
uv add pyinstaller
echo Building EXE...
uv run pyinstaller --noconsole --onefile --icon=icon.ico --add-data "icon.ico;." main.py -n IO_Editor
echo Build complete. Check the 'dist' folder.
pause
