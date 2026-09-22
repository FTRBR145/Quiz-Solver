@echo off
title Auto Quiz Extractor & Solver
color 0A

echo ========================================================
echo        AUTO QUIZ EXTRACTOR & SOLVER (GEMINI 3.8 FLASH)
echo ========================================================
echo.

if not exist .env (
    echo [!] File .env belum ditemukan. Membuat dari template .env.example...
    copy .env.example .env
    echo [!] Silakan edit file .env dan isi GEMINI_API_KEY Anda.
    echo.
)

python main.py
if errorlevel 1 (
    echo.
    echo [!] Terjadi error saat menjalankan program.
    pause
)

