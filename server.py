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
import socket

# Créer l'application FastAPI
app = FastAPI(title="Chatbot SQL")

# Configurer CORS pour permettre toutes les origines
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chemin vers l'application Streamlit
STREAMLIT_APP_PATH = os.path.join(os.path.dirname(__file__), "streamlit", "app.py")

def get_local_ip():
    """Obtient l'adresse IP locale de la machine"""
    try:
        # Crée un socket UDP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Se connecte à un serveur externe (n'envoie pas réellement de données)
        s.connect(("8.8.8.8", 80))
        # Obtient l'adresse IP locale
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

def start_streamlit():
    """Démarre l'application Streamlit en arrière-plan"""
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    
    streamlit_port = int(os.getenv('STREAMLIT_PORT', '8503'))
    python_path = sys.executable
    local_ip = get_local_ip()
    
    cmd = [
        python_path, "-m", "streamlit", "run",
        STREAMLIT_APP_PATH,
        "--server.port", str(streamlit_port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.serverAddress", local_ip,
        "--theme.base", "light"
    ]
    
    # Copier les variables d'environnement actuelles
    env = os.environ.copy()
    env["STREAMLIT_SERVER_ADDRESS"] = "0.0.0.0"
    env["STREAMLIT_SERVER_PORT"] = str(streamlit_port)
    
    print(f"\nStreamlit sera accessible à : http://{local_ip}:{streamlit_port}")
    return subprocess.Popen(cmd, env=env)

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
    local_ip = get_local_ip()
    return f"""
    <html>
        <head>
            <title>Chatbot SQL</title>
            <meta http-equiv="refresh" content="0;url=http://{local_ip}:8503">
        </head>
        <body>
            <p>Redirection vers l'interface Streamlit...</p>
            <p>Si la redirection ne fonctionne pas, cliquez ici : <a href="http://{local_ip}:8503">http://{local_ip}:8503</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    # Charger les variables d'environnement
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    load_dotenv(env_path)
    
    # Récupérer le port depuis les variables d'environnement
    port = int(os.getenv('FASTAPI_PORT', '8000'))
    local_ip = get_local_ip()
    
    print(f"\nServeur FastAPI accessible à : http://{local_ip}:{port}")
    print(f"Interface Streamlit accessible à : http://{local_ip}:8503\n")
    
    # Démarrer le serveur sur toutes les interfaces
    uvicorn.run(app, host="0.0.0.0", port=port)