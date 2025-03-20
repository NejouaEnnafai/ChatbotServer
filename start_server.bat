@echo off
cd /d %~dp0
title Chatbot SQL Server
echo Starting Chatbot SQL Server...

:: Activer l'environnement Python
call venv\Scripts\activate.bat

:: Démarrer le serveur
echo Starting server...
start /B python server.py

:: Attendre que le serveur démarre
echo Waiting for server to start...
timeout /t 3 /nobreak

:: Obtenir l'adresse IP locale
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| find "IPv4"') do (
    set IP=%%a
    goto :found_ip
)
:found_ip
set IP=%IP: =%
echo.
echo Serveur accessible aux adresses :
echo - FastAPI  : http://%IP%:8000
echo - Streamlit: http://%IP%:8503
echo.
echo Appuyez sur une touche pour fermer le serveur...
pause > nul