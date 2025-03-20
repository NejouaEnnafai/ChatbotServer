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
timeout /t 2 /nobreak

:: Ouvrir Chrome avec l'application Streamlit
echo Opening Chrome...
start chrome.exe --new-window "http://localhost:8503"