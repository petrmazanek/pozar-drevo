@echo off
chcp 65001 >nul
title Posudek dřevěného nosníku

echo ==========================================
echo   Posudek dřevěného nosníku
echo   CSN EN 1995-1-1 / 1995-1-2
echo ==========================================
echo.

:: Zjistit Windows IP adresu
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP:~1%

echo   Lokalni pristup:  http://localhost:8501
echo   Sitovy pristup:   http://%IP%:8501
echo.
echo   (Pro sitovy pristup spust nejdrive setup_network.bat jako Admin)
echo.
echo ==========================================
echo.
echo Spoustim aplikaci...
echo.

:: Spustit Streamlit v WSL
wsl -e bash -c "cd /mnt/c/claude/pozar-drevo && pip install streamlit pyyaml fpdf2 -q --break-system-packages 2>/dev/null; streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true"

pause
