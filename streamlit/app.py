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
from config import SQL_CONFIG, get_connection_string, SYSTEM_PROMPT

# Load environment variables from parent directory's .env file
load_dotenv(Path(__file__).parent.parent / '.env')

#Configuration Proxy
https_proxy = os.getenv('HTTPS_PROXY')
if https_proxy :
    os.environ['HTTPS_PROXY'] = https_proxy if https_proxy else ''
    st.sidebar.info(f"Proxy Configuré")


# Configuration Google Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    st.error("Veuillez définir votre GOOGLE_API_KEY dans le fichier .env")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'schema' not in st.session_state:
    st.session_state.schema = None
if 'current_sql' not in st.session_state:
    st.session_state.current_sql = None

def query_model(payload):
    """
    Envoie une requête au modèle Google Gemini
    """
    try:
        response = model.generate_content(payload)
        return response
    except Exception as e:
        st.error(f"Erreur lors de l'appel au modèle : {str(e)}")
        return None

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
                'from_table': row.from_table,
                'from_column': row.from_column,
                'to_table': row.to_table,
                'to_column': row.to_column
            })
            
        cursor.close()
        return schema
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du schéma : {str(e)}")
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
        # Utiliser le prompt système depuis config.py
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
                
        # Ajouter une limitation à 1000 lignes si ce n'est pas déjà fait
        if 'top' not in sql_lower:
            # Trouver la position de la clause FROM
            from_pos = sql_lower.find('from')
            if from_pos != -1:
                # Insérer TOP 1000 juste après SELECT
                insert_pos = sql_lower.find('select') + 6
                sql_query = sql_query[:insert_pos] + ' TOP 1000 ' + sql_query[insert_pos:]
                
        return sql_query
        
    except Exception as e:
        st.error(f"Erreur lors de la génération de la requête : {str(e)}")
        return None

def execute_query(conn, query):
    """
    Exécute une requête SQL et retourne les résultats sous forme de DataFrame
    """
    try:
        # Nettoyer la requête pour éviter les problèmes de syntaxe
        query = query.strip()
        # Supprimer les points-virgules multiples
        query = re.sub(r';+', ';', query)
        # Supprimer les espaces multiples
        query = re.sub(r'\s+', ' ', query)
        
        # Exécuter la requête
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Récupérer les colonnes
        columns = [column[0] for column in cursor.description]
        
        # Nettoyer les noms de colonnes
        cleaned_columns = []
        for col in columns:
            # Si la colonne est vide, générer un nom basé sur sa position
            if not col or col.strip() == '':
                cleaned_columns.append(f'col_{len(cleaned_columns) + 1}')
            else:
                cleaned_columns.append(col.strip())
        
        # Récupérer les résultats
        results = cursor.fetchall()
        
        # Vérifier si nous avons des résultats
        if not results:
            return pd.DataFrame(columns=cleaned_columns)
            
        # Créer le DataFrame
        try:
            # Vérifier et corriger les noms de colonnes dupliqués
            unique_columns = []
            seen_columns = set()
            for col in cleaned_columns:
                if col in seen_columns:
                    # Ajouter un suffixe unique pour les colonnes dupliquées
                    suffix = 1
                    while f"{col}_{suffix}" in seen_columns:
                        suffix += 1
                    col = f"{col}_{suffix}"
                seen_columns.add(col)
                unique_columns.append(col)
            
            # Convertir les résultats en liste de listes
            result_list = [list(row) for row in results]
            
            df = pd.DataFrame(result_list, columns=unique_columns)
            return df
        except Exception as e:
            # Si la création du DataFrame échoue, essayer avec une liste de listes
            try:
                df = pd.DataFrame(list(results), columns=cleaned_columns)
                return df
            except Exception as e:
                st.error(f"Erreur lors de la création du DataFrame : {str(e)}")
                st.error(f"Structure des données : {str(results[:1])}")
                st.error(f"Colonnes : {str(cleaned_columns)}")
                return None
        
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        st.error(f"Voir la requête technique\n\n```sql\n{query}\n```")
        return None

def main():
    # Configuration du port Streamlit
    os.environ['STREAMLIT_SERVER_PORT'] = os.getenv('STREAMLIT_PORT', '8501')

    # Sidebar avec les informations
    show_about()
    
    # Titre principal
    st.title("Assistant Base de Données")
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
                        response["content"] = "Voici les résultats de votre recherche."
                    else:
                        st.info("Aucun résultat trouvé.")
                        response["content"] = "Je n'ai trouvé aucune information correspondant à votre demande."
                    
                    st.session_state.messages.append(response)
        
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()