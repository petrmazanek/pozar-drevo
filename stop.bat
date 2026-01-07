@echo off
chcp 65001 >nul
title Zastavení aplikace

echo Zastavuji Streamlit...

:: Najít a ukončit streamlit proces ve WSL
wsl -e bash -c "pkill -f streamlit 2>/dev/null"

echo.
echo Aplikace zastavena.
echo.

pause
