@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv_hybrid\Scripts\python.exe" (
  echo [1/3] Creating Python 3.11 environment...
  py -3.11 -m venv .venv_hybrid
  if errorlevel 1 (
    echo Python 3.11 belum ditemukan. Instal Python 3.11 dari python.org.
    pause
    exit /b 1
  )
  echo [2/3] Installing requirements (first run only)...
  ".venv_hybrid\Scripts\python.exe" -m pip install --upgrade pip
  ".venv_hybrid\Scripts\python.exe" -m pip install -r requirements-hybrid.txt
  if errorlevel 1 (
    echo Gagal menginstal dependensi.
    pause
    exit /b 1
  )
)
echo [3/3] Starting Hybrid Identity Studio...
".venv_hybrid\Scripts\python.exe" -m hybrid_studio
if errorlevel 1 pause
