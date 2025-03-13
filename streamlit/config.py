import os
from dotenv import load_dotenv
from pathlib import Path

# Charger les variables d'environnement depuis le fichier .env parent
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration SQL Server
SQL_CONFIG = {
    'SERVER': os.getenv('DB_SERVER', '').strip('"'),  # Enlever les guillemets
    'DATABASE': os.getenv('DB_NAME', '').strip('"'),  # Enlever les guillemets
    'USERNAME': os.getenv('DB_USER'),
    'PASSWORD': os.getenv('DB_PASSWORD'),
    'PORT': os.getenv('DB_PORT', '1433'),
    'AUTH_TYPE': os.getenv('DB_AUTH_TYPE', 'windows').strip('"')  # Enlever les guillemets
}

def get_connection_string() -> str:
    """
    Construit la chaîne de connexion SQL Server en fonction du type d'authentification
    """
    auth_type = SQL_CONFIG.get('AUTH_TYPE', 'windows').lower()
    
    # Validation des paramètres obligatoires
    if not SQL_CONFIG.get('SERVER') or not SQL_CONFIG.get('DATABASE'):
        raise ValueError("Le serveur (DB_SERVER) et la base de données (DB_NAME) sont requis")
    
    # Chaîne de connexion de base
    conn_str = f"DRIVER={{SQL Server}};SERVER={SQL_CONFIG['SERVER']};DATABASE={SQL_CONFIG['DATABASE']}"
    
    # Authentification
    if auth_type == 'sql_server':
        if not SQL_CONFIG.get('USERNAME') or not SQL_CONFIG.get('PASSWORD'):
            raise ValueError("Les identifiants SQL Server (DB_USER, DB_PASSWORD) sont requis pour l'authentification SQL Server")
        conn_str += f";UID={SQL_CONFIG['USERNAME']};PWD={SQL_CONFIG['PASSWORD']}"
    else:
        conn_str += ";Trusted_Connection=yes"
    
    return conn_str

# System prompt par défaut
SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT', """Tu es un expert en SQL Server. Traduis cette question en requête SQL.

{schema_desc}

Question : {question}

INSTRUCTIONS IMPORTANTES:
1. Retourne UNIQUEMENT la requête SQL, sans explication ni commentaire
2. Utilise les noms exacts des tables et colonnes du schéma
3. Pour les ID spécifiques, respecte la casse exacte
""")
