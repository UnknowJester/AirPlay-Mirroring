@echo off
echo ==============================================
echo Compilazione di AirPlay.exe con PyInstaller
echo ==============================================
python -m pip install -r requirements.txt
pyinstaller --noconsole --onefile --icon=resources/icon.ico --name=AirPlay gui_app.py
if exist dist\AirPlay.exe (
    move /y dist\AirPlay.exe AirPlay.exe
    rd /s /q build
    rd /s /q dist
    del AirPlay.spec
    echo.
    echo Compilazione completata con successo: AirPlay.exe
) else (
    echo.
    echo Errore durante la compilazione!
)
pause
