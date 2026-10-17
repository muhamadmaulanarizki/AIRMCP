@echo off
echo === AirMCP Solo Setup ===
echo.
pip install -r requirements.txt
if errorlevel 1 goto :err
if not exist .env (
  copy .env.example .env >nul
  echo [OK] .env dibuat dari .env.example - isi API key di dalamnya
) else (
  echo [OK] .env sudah ada
)
if not exist agents.json copy agents.example.json agents.json >nul
if not exist projects.json copy projects.example.json projects.json >nul
echo.
echo Setup selesai. Jalankan server: python mcp_server.py
goto :eof
:err
echo [!] pip install gagal - cek koneksi internet
