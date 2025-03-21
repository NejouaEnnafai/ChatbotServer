from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path
import os
import logging
import re

# Configuration des logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ajouter le répertoire parent au PYTHONPATH pour importer les modules du projet
parent_dir = str(Path(__file__).parent.parent)
streamlit_dir = os.path.join(parent_dir, 'streamlit')
if streamlit_dir not in sys.path:
    sys.path.insert(0, streamlit_dir)  # Insérer au début du PYTHONPATH

try:
    from config import SQL_CONFIG, get_connection_string, SYSTEM_PROMPT  # Import direct depuis config.py
    logger.info("Configuration chargée avec succès")
except Exception as e:
    logger.error(f"Erreur lors du chargement de la configuration : {str(e)}")
    raise

import google.generativeai as genai
import pyodbc
import pandas as pd
from dotenv import load_dotenv
from typing import List, Dict, Optional

# Charger les variables d'environnement
load_dotenv(Path(__file__).parent.parent / '.env')

# Configuration de l'API
app = FastAPI(
    title="ChatbotSQL API",
    description="API pour interagir avec le chatbot SQL",
    version="1.0.0"
)

# Configuration de Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    logger.error("GOOGLE_API_KEY non définie dans .env")
    raise ValueError("GOOGLE_API_KEY non définie dans .env")

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-2.0-flash')
    logger.info("Modèle Gemini configuré avec succès")
except Exception as e:
    logger.error(f"Erreur lors de la configuration de Gemini : {str(e)}")
    raise

# Modèles de données
class Question(BaseModel):
    text: str
    conversation_history: Optional[List[Dict[str, str]]] = []

class Response(BaseModel):
    answer: str
    sql_query: str | None = None
    data: list | None = None

def get_database_schema(conn):
    """Récupères le schéma de la base de données"""
    schema = {
        'tables': [],
        'relations': []
    }
    
    try:
        cursor = conn.cursor()
        
        # Récupérer les tables et leurs colonnes
        tables_query = """
        SELECT 
            t.name AS table_name,
            c.name AS column_name,
            ty.name AS data_type,
            c.is_nullable,
            c.is_identity,
            CAST(CASE WHEN EXISTS (
                SELECT 1 FROM sys.indexes i
                JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                WHERE i.is_primary_key = 1
                AND ic.object_id = c.object_id
                AND ic.column_id = c.column_id
            ) THEN 1 ELSE 0 END AS bit) AS is_primary_key
        FROM sys.tables t
        JOIN sys.columns c ON t.object_id = c.object_id
        JOIN sys.types ty ON c.user_type_id = ty.user_type_id
        WHERE t.name LIKE 'Market%'
        ORDER BY t.name, c.column_id
        """
        
        cursor.execute(tables_query)
        current_table = None
        
        for row in cursor.fetchall():
            table_name = row.table_name
            column = {
                'name': row.column_name,
                'type': row.data_type,
                'nullable': row.is_nullable,
                'is_identity': row.is_identity,
                'is_primary_key': row.is_primary_key
            }
            
            if current_table is None or current_table['name'] != table_name:
                if current_table is not None:
                    schema['tables'].append(current_table)
                current_table = {
                    'name': table_name,
                    'columns': []
                }
            
            current_table['columns'].append(column)
        
        if current_table is not None:
            schema['tables'].append(current_table)
            
        # Récupérer les relations
        relations_query = """
        SELECT 
            t1.name AS from_table,
            c1.name AS from_column,
            t2.name AS to_table,
            c2.name AS to_column
        FROM sys.foreign_keys fk
        JOIN sys.tables t1 ON fk.parent_object_id = t1.object_id
        JOIN sys.tables t2 ON fk.referenced_object_id = t2.object_id
        JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        JOIN sys.columns c1 ON fkc.parent_object_id = c1.object_id AND fkc.parent_column_id = c1.column_id
        JOIN sys.columns c2 ON fkc.referenced_object_id = c2.object_id AND fkc.referenced_column_id = c2.column_id
        WHERE t1.name LIKE 'Market%' OR t2.name LIKE 'Market%'
        ORDER BY t1.name, c1.name
        """
        
        cursor.execute(relations_query)
        for row in cursor.fetchall():
            relation = {
                'from_table': row.from_table,
                'from_column': row.from_column,
                'to_table': row.to_table,
                'to_column': row.to_column
            }
            schema['relations'].append(relation)
        
        cursor.close()
        logger.info("Schéma de la base de données récupéré")
        return schema
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du schéma : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du schéma : {str(e)}")

def execute_query(conn, query):
    """Exécute une requête SQL et retourne les résultats"""
    try:
        df = pd.read_sql(query, conn)
        logger.info("Requête SQL exécutée avec succès")
        return df
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'exécution de la requête : {str(e)}")

def clean_sql_query(query: str) -> str:
    """Nettoie la requête SQL des artefacts de formatage markdown"""
    # Supprimer les blocs de code markdown
    query = re.sub(r'```sql\s*|\s*```', '', query)
    # Supprimer les backticks simples
    query = re.sub(r'`', '', query)
    # Supprimer les points-virgules finaux
    query = query.strip().rstrip(';')
    return query

@app.post("/chat", response_model=Response)
async def chat(question: Question):
    """
    Point d'entrée principal pour le chat.
    Accepte une question et retourne une réponse avec SQL si pertinent.
    """
    try:
        # Connexion à la base de données
        conn = pyodbc.connect(get_connection_string())
        
        # Récupération du schéma
        schema = get_database_schema(conn)
        if not schema:
            raise HTTPException(status_code=500, message="Impossible de récupérer le schéma de la base de données")
        
        # Construire le contexte avec l'historique des conversations
        conversation_context = "\n".join([
            f"Question: {msg['question']}\nRéponse SQL: {msg['sql']}"
            for msg in question.conversation_history[-3:]  # Garder les 3 dernières interactions
        ])
        
        # Construire la description du schéma
        schema_desc = "Schéma de la base de données :\n"
        for table in schema['tables']:
            schema_desc += f"\nTable {table['name']} :\n"
            for col in table['columns']:
                pk = "PK" if col['is_primary_key'] else "  "
                nullable = "NULL" if col['nullable'] else "NOT NULL"
                schema_desc += f"  - {pk} {col['name']} ({col['type']}) {nullable}\n"
        
        if schema['relations']:
            schema_desc += "\nRelations :\n"
            for rel in schema['relations']:
                schema_desc += f"  - {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n"
        
        # Construire le prompt avec le contexte
        prompt = f"{SYSTEM_PROMPT}\n\n{schema_desc}\n\n"
        if conversation_context:
            prompt += f"Historique des conversations récentes:\n{conversation_context}\n\n"
        prompt += f"Question actuelle: {question.text}\n\nGénérez uniquement la requête SQL correspondante."
        
        # Générer la requête SQL
        response = model.generate_content(prompt)
        if not response or not response.text:
            raise HTTPException(status_code=500, detail="Le modèle n'a pas généré de réponse valide")
        
        # Nettoyer la requête SQL
        sql_query = clean_sql_query(response.text)
        
        # Exécuter la requête
        try:
            results = execute_query(conn, sql_query)
            
            # Préparer la réponse
            return Response(
                answer="Requête exécutée avec succès",
                sql_query=sql_query,
                data=results.to_dict('records') if results is not None else None
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
            raise HTTPException(status_code=500, detail=f"Erreur lors de l'exécution de la requête : {str(e)}")
            
    except Exception as e:
        logger.error(f"Erreur dans le chat : {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('FASTAPI_PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
