@echo off
cd /d %~dp0
title Chatbot SQL Server
echo Starting Chatbot SQL Server...

:: Activer l'environnement Python
call venv\Scripts\activate.bat

:: Démarrer le serveur
start /B python server.py

:: Attendre que le serveur démarre (2 secondes)
echo Waiting for server to start...
timeout /t 2 /nobreak

:: Ouvrir Chrome avec l'application Streamlit
echo Opening Chrome...
start chrome.exe --new-window "http://localhost:8503"