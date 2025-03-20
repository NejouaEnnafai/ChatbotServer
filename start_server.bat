@echo off
cd /d %~dp0
title Chatbot SQL Server
echo Starting Chatbot SQL Server...

:: Activer l'environnement Python silencieusement
call venv\Scripts\activate >nul 2>&1

:: Démarrer le serveur en arrière-plan et masquer la fenêtre
start /B /MIN cmd /c venv\Scripts\python server.py >nul 2>&1

:: Attendre quelques secondes pour que le serveur démarre silencieusement
timeout /t 5 /nobreak >nul 2>&1

:: Ouvrir Chrome avec l'application Streamlit
start chrome http://localhost:8503