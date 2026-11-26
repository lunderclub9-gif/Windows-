@echo off
setlocal
echo ============================================
echo   DocuMaker DZ - Windows EXE Builder
echo ============================================

cd /d "%~dp0"

if not exist ".venv" (
    echo [1/4] Creating Python virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

if not exist "bin\ffmpeg.exe" (
    echo [Note] Place ffmpeg.exe and ffprobe.exe in documaker_dz\bin\ to bundle them inside the .exe.
)

echo [3/4] Building DocuMakerDZ.exe (no console window, custom icon)...
pyinstaller --clean --noconfirm documaker.spec

echo [4/4] Done! Output executable: dist\DocuMakerDZ.exe
pause
