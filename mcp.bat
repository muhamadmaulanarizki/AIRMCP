@echo off
setlocal
set "ROOT=%~dp0"
title AirMCP Solo - Launcher
color 0B
:menu
cls
echo ============================================
echo    AIR MCP SOLO - Launcher
echo ============================================
echo.
echo   [1] Web Dashboard  (browser visual)
echo   [2] Chat dengan AI + tools
echo   [3] Terminal UI
echo   [4] Jalankan semua test
echo   [5] Keluar
echo.
set /p pilih=Pilih menu (1-5):

if "%pilih%"=="1" goto dash
if "%pilih%"=="2" goto chat
if "%pilih%"=="3" goto tui
if "%pilih%"=="4" goto test
if "%pilih%"=="5" exit
goto menu

:dash
echo [%time%] Starting dashboard... browser akan terbuka otomatis
python "%ROOT%dashboard.py"
pause
goto menu

:chat
echo [%time%] Chat mode - ketik pertanyaan, 'q' untuk keluar
python "%ROOT%client.py" chat
pause
goto menu

:tui
python "%ROOT%ui\terminal_ui.py"
pause
goto menu

:test
echo [%time%] Menjalankan SEMUA test...
set PYEXE=python
if exist "%ROOT%.venv\Scripts\python.exe" set PYEXE="%ROOT%.venv\Scripts\python.exe"
for %%F in ("%ROOT%tests\test_*.py") do (
  echo --- %%F ---
  %PYEXE% "%%F"
)
pause
goto menu
