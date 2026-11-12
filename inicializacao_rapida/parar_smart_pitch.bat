@echo off
title Smart Pitch - Encerramento Rapido
:: Navega ate a raiz do projeto (uma pasta acima)
cd /d "%~dp0\.."

echo ==============================================================
echo   ENCERRANDO SMART PITCH (GESTAO DE ESTADIOS)
echo ==============================================================

echo [1/2] Fechando janelas dos componentes Python...
taskkill /F /FI "WINDOWTITLE eq Controlador 1*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Controlador 2*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Controlador 3*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Middleware SD*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Atuadores MQTT*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Sensores MQTT*" /T 2>nul
taskkill /F /FI "WINDOWTITLE eq Cliente Smart Pitch*" /T 2>nul

echo.
echo [2/2] Parando o Broker Mosquitto MQTT (Docker)...
docker compose down

echo.
echo ==============================================================
echo   Todos os componentes foram encerrados com sucesso!
echo ==============================================================
pause

