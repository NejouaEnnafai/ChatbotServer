import streamlit as st

# Configuration de la page Streamlit (doit être la première commande st)
st.set_page_config(page_title="Assistant SQL", layout="wide")

import pandas as pd
import pyodbc
import os
import re
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path
from config import SQL_CONFIG, get_connection_string

# Load environment variables from parent directory's .env file
load_dotenv(Path(__file__).parent.parent / '.env')

#Configuration Proxy
https_proxy = os.getenv('HTTPS_PROXY')
if https_proxy :
    os.environ['HTTPS_PROXY'] = https_proxy if https_proxy else ''
    st.sidebar.info(f"Proxy Configuré")


# Configuration Google Gemini
GOOGLE_API_KEY_SQL = "AIzaSyCeuJbKwmtSWBoEWbFtQaipS5K7A0nKzFA"  # Clé pour la génération SQL
GOOGLE_API_KEY_ANALYSIS = "AIzaSyDXB5ofl9Ss6pb5KHQDsJsHOy1nYXbqokU"  # Clé pour l'analyse des données

genai.configure(api_key=GOOGLE_API_KEY_SQL)
model_sql = genai.GenerativeModel('gemini-2.0-flash')

def get_analysis_model():
    """Obtient une instance du modèle pour l'analyse avec une clé API différente"""
    genai.configure(api_key=GOOGLE_API_KEY_ANALYSIS)
    return genai.GenerativeModel('gemini-2.0-flash')

def query_model(payload, for_analysis=False):
    """
    Envoie une requête au modèle Google Gemini avec la clé appropriée
    """
    try:
        # Utiliser le modèle approprié selon le type de requête
        if for_analysis:
            model = get_analysis_model()
            # Remettre la clé SQL pour les prochaines requêtes
            genai.configure(api_key=GOOGLE_API_KEY_SQL)
        else:
            model = model_sql
            
        response = model.generate_content(payload)
        return response
    except Exception as e:
        st.error(f"Erreur lors de l'appel au modèle : {str(e)}")
        return None

# Prompt système pour la génération SQL
SYSTEM_PROMPT = """Tu es un expert en SQL Server chargé de traduire des questions en langage naturel en requêtes SQL valides.

Schéma de la base de données :
{schema_desc}

Abréviations pour l'état du produit :
A: Concrétisé
L: Libre
R: Réservé
V: Vendu

Abréviations pour la nature du produit :
T: Terrain
A: Appartement
P: Parking
PL: Plateau de Bureau
LV: Lot de Villa
M: Maison
B: Bureau
V: Villa
EV: Equipement
MS: Maison Sociale

Règles importantes :
1. Utilise uniquement les tables commençant par 'Market'
2. Traduis les abréviations d'état et de nature de produit dans tes requêtes
3. Génère uniquement la requête SQL, sans explication
4. Utilise la syntaxe SQL Server

Question : {question}

Réponse (uniquement la requête SQL) :"""

# Prompt système pour l'analyse des données
ANALYSIS_PROMPT = """Tu es un expert en analyse de données immobilières. Analyse uniquement les données fournies et génère un résumé professionnel.

Contexte des données :
- État des biens : A (Concrétisé), L (Libre), R (Réservé), V (Vendu)
- Nature des biens : T (Terrain), A (Appartement), P (Parking), PL (Plateau Bureau), LV (Lot Villa), M (Maison), B (Bureau), V (Villa), EV (Équipement), MS (Maison Sociale)

Données à analyser :
{data_desc}

Question initiale : {question}

Donne une description textuelle pour les données extraites ne depasse pas 3 lignes.
Format souhaité : Un paragraphe professionnel et concis."""

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'schema' not in st.session_state:
    st.session_state.schema = None
if 'current_sql' not in st.session_state:
    st.session_state.current_sql = None

def show_about():
    """Affiche les informations À propos dans la sidebar"""
    with st.sidebar:
        st.title("À propos")
        st.markdown("""
        ### Assistant Base de Données
        
        Cet assistant vous aide à interroger la base de données en langage naturel.
        
        **Fonctionnalités :**
        - Posez vos questions simplement
        - Visualisation des résultats
        - Interface conversationnelle
        
        **Version :** 1.0.0
        """)

@st.cache_data(ttl=3600)
def get_database_schema(_conn):
    """
    Récupère le schéma de la base de données (uniquement les tables Market)
    """
    schema = {
        'tables': [],
        'relations': []
    }
    
    try:
        cursor = _conn.cursor()
        
        # Récupérer les tables et leurs colonnes (uniquement les tables Market)
        tables_query = """
        SELECT 
            t.name AS table_name,
            c.name AS column_name,
            ty.name AS data_type,
            c.max_length,
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
                'max_length': row.max_length,
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
        
        # Récupérer les relations (uniquement pour les tables Market)
        relations_query = """
        SELECT 
            pt.name AS from_table,
            pc.name AS from_column,
            rt.name AS to_table,
            rc.name AS to_column
        FROM sys.foreign_keys fk
        JOIN sys.tables pt ON fk.parent_object_id = pt.object_id
        JOIN sys.tables rt ON fk.referenced_object_id = rt.object_id
        JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
        JOIN sys.columns pc ON fkc.parent_object_id = pc.object_id AND fkc.parent_column_id = pc.column_id
        JOIN sys.columns rc ON fkc.referenced_object_id = rc.object_id AND fkc.referenced_column_id = rc.column_id
        WHERE pt.name LIKE 'Market%' OR rt.name LIKE 'Market%'
        ORDER BY pt.name, pc.name
        """
        
        cursor.execute(relations_query)
        for row in cursor.fetchall():
            schema['relations'].append({
                'table1': row.from_table,
                'column1': row.from_column,
                'table2': row.to_table,
                'column2': row.to_column
            })
            
        cursor.close()
        return schema
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du schéma : {str(e)}")
        return None

def analyze_results(results, question):
    """
    Analyse les résultats d'une requête SQL et génère un résumé
    """
    if results is None or results.empty:
        return None
        
    # Convertir le DataFrame en description textuelle
    data_desc = results.to_string()
    
    try:
        # Préparer le prompt pour l'analyse
        prompt = ANALYSIS_PROMPT.format(
            data_desc=data_desc,
            question=question
        )
        
        # Appeler le modèle pour l'analyse avec la clé dédiée
        response = query_model(prompt, for_analysis=True)
        if not response or not response.text:
            return None
            
        return response.text.strip()
        
    except Exception as e:
        st.error(f"Erreur lors de l'analyse des résultats : {str(e)}")
        return None

def generate_sql_query(question, schema):
    """
    Génère une requête SQL à partir d'une question en langage naturel
    """
    # Construire la description du schéma
    schema_desc = "Schéma de la base de données :\n"
    
    # Tables et colonnes
    for table in schema['tables']:
        schema_desc += f"\nTable {table['name']} :\n"
        for col in table['columns']:
            pk = "PK" if col['is_primary_key'] else "  "
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            schema_desc += f"  - {pk} {col['name']} ({col['type']}) {nullable}\n"
    
    # Relations
    if schema['relations']:
        schema_desc += "\nRelations :\n"
        for rel in schema['relations']:
            schema_desc += f"  - {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n"
    
    try:
        # Utiliser le prompt système défini dans ce fichier
        prompt = SYSTEM_PROMPT.format(
            schema_desc=schema_desc,
            question=question
        )
        
        # Appeler le modèle
        response = query_model(prompt)
        if not response or not response.text:
            st.error("Le modèle n'a pas généré de réponse valide.")
            return None
            
        # Extraire et nettoyer la requête SQL
        sql_query = response.text.strip()
        
        # Supprimer les blocs de code markdown s'ils existent
        sql_query = re.sub(r'```sql\s*|\s*```', '', sql_query)
        
        # Supprimer les points-virgules finaux
        sql_query = sql_query.rstrip(';')
        
        # Validation basique
        sql_query = sql_query.strip()
        if not sql_query:
            st.error("La requête générée est vide.")
            return None
            
        # Vérifier que la requête commence par un mot-clé SQL valide
        valid_starts = ('select', 'with')
        if not any(sql_query.lower().startswith(start) for start in valid_starts):
            st.error("La requête doit commencer par SELECT ou WITH.")
            return None
            
        # Vérifier la présence de mots-clés SQL de base
        if 'from' not in sql_query.lower():
            st.error("La requête doit contenir une clause FROM.")
            return None
            
        # Vérifier que les tables référencées existent dans le schéma
        tables = [table['name'].lower() for table in schema['tables']]
        sql_lower = sql_query.lower()
        
        # Extraire les noms de tables après FROM et JOIN
        table_refs = re.findall(r'\bfrom\s+(\w+)|join\s+(\w+)', sql_lower)
        referenced_tables = set()
        for from_table, join_table in table_refs:
            if from_table:
                referenced_tables.add(from_table)
            if join_table:
                referenced_tables.add(join_table)
        
        # Vérifier que chaque table référencée existe
        for table in referenced_tables:
            if table not in tables:
                st.error(f"La table '{table}' n'existe pas dans le schéma.")
                return None
            
        return sql_query
        
    except Exception as e:
        st.error(f"Erreur lors de la génération de la requête : {str(e)}")
        return None

def execute_query(conn, query):
    """
    Exécute une requête SQL et retourne les résultats sous forme de DataFrame
    """
    try:
        return pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        return None

def main():
    # Configuration du port Streamlit
    os.environ['STREAMLIT_SERVER_PORT'] = os.getenv('STREAMLIT_PORT', '8501')

    # Sidebar avec les informations
    show_about()
    
    # Titre principal
    st.title("Assistant Base de Données Test")
    st.write("Posez vos questions simplement, je m'occupe de rechercher les informations pour vous.")
    
    try:
        conn = pyodbc.connect(get_connection_string())
        
        # Get and cache database schema
        if st.session_state.schema is None:
            st.session_state.schema = get_database_schema(conn)
            if not st.session_state.schema:
                return
        
        # Chat interface
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                if "data" in message:
                    if "sql" in message:
                        with st.expander("Voir la requête technique", expanded=False):
                            st.code(message["sql"], language="sql")
                    st.dataframe(message["data"])
                else:
                    st.write(message["content"])
        
        # Zone de saisie utilisateur
        if question := st.chat_input("Quelle information recherchez-vous ?"):
            # Afficher la question de l'utilisateur
            with st.chat_message("user"):
                st.write(question)
            st.session_state.messages.append({"role": "user", "content": question})
            
            # Générer et afficher la réponse
            with st.chat_message("assistant"):
                sql_query = generate_sql_query(question, st.session_state.schema)
                
                if sql_query:
                    results = execute_query(conn, sql_query)
                    response = {
                        "role": "assistant",
                        "sql": sql_query
                    }
                    
                    with st.expander("Voir la requête technique", expanded=False):
                        st.code(sql_query, language="sql")
                        
                    if results is not None:
                        st.dataframe(results)
                        response["data"] = results
                        
                        # Ajouter l'analyse des résultats
                        analysis = analyze_results(results, question)
                        if analysis:
                            st.write("Description:")
                            st.write(analysis)
                            response["content"] = f"Voici les résultats de votre recherche.\n\n📊 **Analyse:**\n{analysis}"
                        else:
                            response["content"] = "Voici les résultats de votre recherche."
                    
                    st.session_state.messages.append(response)
        
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()