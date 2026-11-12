@echo off
title Smart Pitch - Inicializador Rapido
:: Navega ate a raiz do projeto (uma pasta acima)
cd /d "%~dp0\.."

echo ==============================================================
echo   GESTAO AUTOMATIZADA DE ESTADIOS — SMART PITCH (SD)
echo ==============================================================
echo [1/2] Verificando e subindo o Broker MQTT (Docker)...
docker compose up -d

echo.
echo [2/2] Iniciando todos os modulos distribuidos...
py gramado\start_all.py 2>nul || "C:\Users\bryan\AppData\Local\Programs\Python\Python315\python.exe" gramado\start_all.py

echo.
echo Processos inicializados!
pause

