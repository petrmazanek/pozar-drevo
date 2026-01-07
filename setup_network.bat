@echo off
chcp 65001 >nul
title Nastavení sítě pro Streamlit

:: Kontrola admin práv
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ==========================================
    echo   CHYBA: Spustte jako Administrator!
    echo ==========================================
    echo.
    echo   Klikni pravym tlacitkem na tento soubor
    echo   a vyber "Spustit jako spravce"
    echo.
    pause
    exit /b 1
)

echo ==========================================
echo   Nastaveni site pro Streamlit
echo ==========================================
echo.

:: Odstranit staré pravidlo pokud existuje
netsh interface portproxy delete v4tov4 listenport=8501 listenaddress=0.0.0.0 >nul 2>&1

:: Přidat port forwarding
echo [1/2] Nastavuji port forwarding...
netsh interface portproxy add v4tov4 listenport=8501 listenaddress=0.0.0.0 connectport=8501 connectaddress=localhost
if %errorlevel% equ 0 (
    echo       OK - Port 8501 presmerovan
) else (
    echo       CHYBA pri nastaveni port forwardingu
)

:: Přidat firewall pravidlo
echo [2/2] Nastavuji firewall...
netsh advfirewall firewall delete rule name="Streamlit Timber App" >nul 2>&1
netsh advfirewall firewall add rule name="Streamlit Timber App" dir=in action=allow protocol=tcp localport=8501 >nul
if %errorlevel% equ 0 (
    echo       OK - Firewall pravidlo pridano
) else (
    echo       CHYBA pri nastaveni firewallu
)

echo.
echo ==========================================
echo   Hotovo!
echo ==========================================
echo.

:: Zobrazit Windows IP
echo   Vase IP adresy:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    echo      %%a
)
echo.
echo   Ostatni zarizeni v siti mohou pristoupit na:
echo   http://VASE_IP:8501
echo.
echo   Ted spustte start.bat
echo.

pause
