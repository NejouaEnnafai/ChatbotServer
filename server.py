from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import streamlit as st
import subprocess
import os
import sys
from pathlib import Path
import uvicorn

# Créer l'application FastAPI
app = FastAPI(title="Chatbot SQL")

# Configurer CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemin vers l'application Streamlit
STREAMLIT_APP_PATH = os.path.join(os.path.dirname(__file__), "streamlit", "app.py")

def start_streamlit():
    """Démarre l'application Streamlit en arrière-plan"""
    streamlit_port = int(os.getenv('STREAMLIT_PORT', '8503'))
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        STREAMLIT_APP_PATH,
        "--server.port", str(streamlit_port),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.serverAddress", "localhost",
        "--theme.base", "light"
    ]
    return subprocess.Popen(cmd)

@app.on_event("startup")
async def startup_event():
    """Démarre Streamlit quand FastAPI démarre"""
    app.state.streamlit_process = start_streamlit()

@app.on_event("shutdown")
async def shutdown_event():
    """Arrête Streamlit quand FastAPI s'arrête"""
    if hasattr(app.state, "streamlit_process"):
        app.state.streamlit_process.terminate()

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
        <head>
            <title>Chatbot SQL</title>
            <meta http-equiv="refresh" content="0;url=http://localhost:8503">
        </head>
        <body>
            <p>Redirection vers l'interface Streamlit...</p>
        </body>
    </html>
    """

if __name__ == "__main__":
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
    
    # Configuration du port
    port = int(os.getenv('FASTAPI_PORT', '8000'))
    
    print(f"Démarrage du serveur sur le port {port}")
    print("L'application Streamlit sera accessible via FastAPI")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=port,
        reload=True  # Active le rechargement automatique
    )