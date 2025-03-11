import streamlit as st
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

# Configuration
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    st.error("Veuillez définir votre GOOGLE_API_KEY dans le fichier .env")
    st.stop()

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Page configuration
st.set_page_config(
    page_title="Assistant SQL",
    page_icon="💬",
    layout="wide"
)

@st.cache_data(ttl=3600)
def get_database_schema(_conn):
    """Récupère dynamiquement le schéma de la base de données"""
    try:
        cursor = _conn.cursor()
        
        # Récupérer toutes les tables
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        schema = {}
        for table in tables:
            # Récupérer les colonnes pour chaque table
            cursor.execute(f"""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
            """, table)
            
            columns = []
            for col in cursor.fetchall():
                col_name = col[0]
                data_type = col[1]
                max_length = col[2]
                precision = col[3]
                scale = col[4]
                nullable = col[5]
                
                type_desc = data_type
                if data_type in ('varchar', 'nvarchar', 'char', 'nchar'):
                    type_desc += f"({max_length if max_length != -1 else 'max'})"
                elif data_type in ('decimal', 'numeric'):
                    type_desc += f"({precision},{scale})"
                    
                columns.append(f"{col_name} ({type_desc})")
            
            schema[table] = columns
            
        # Récupérer les relations entre les tables
        cursor.execute("""
            SELECT 
                fk.name AS FK_name,
                tp.name AS parent_table,
                cp.name AS parent_column,
                tr.name AS referenced_table,
                cr.name AS referenced_column
            FROM 
                sys.foreign_keys fk
                INNER JOIN sys.tables tp ON fk.parent_object_id = tp.object_id
                INNER JOIN sys.tables tr ON fk.referenced_object_id = tr.object_id
                INNER JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
                INNER JOIN sys.columns cp ON fkc.parent_column_id = cp.column_id AND fkc.parent_object_id = cp.object_id
                INNER JOIN sys.columns cr ON fkc.referenced_column_id = cr.column_id AND fkc.referenced_object_id = cr.object_id
        """)
        
        relations = cursor.fetchall()
        schema['relations'] = []
        for rel in relations:
            schema['relations'].append({
                'name': rel[0],
                'from_table': rel[1],
                'from_column': rel[2],
                'to_table': rel[3],
                'to_column': rel[4]
            })
        
        cursor.close()
        return schema
        
    except Exception as e:
        st.error(f"Erreur lors de la récupération du schéma: {str(e)}")
        return None

def generate_sql_query(question, schema):
    """Traduit le langage naturel en SQL avec Gemini"""
    if not schema:
        return None
        
    # Construire la description du schéma
    schema_desc = "Schéma de la base de données:\n"
    for table, columns in schema.items():
        if table != 'relations':
            schema_desc += f"\nTable '{table}':\n"
            for col in columns:
                schema_desc += f"  - {col}\n"
    
    if schema.get('relations'):
        schema_desc += "\nRelations entre les tables:\n"
        for rel in schema['relations']:
            schema_desc += f"  - {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}\n"
    
    prompt = f"""Tu es un expert en SQL Server. Traduis cette question en requête SQL.

{schema_desc}

Question : {question}

INSTRUCTIONS IMPORTANTES:
1. Retourne UNIQUEMENT la requête SQL, sans explication ni commentaire
2. Utilise les noms exacts des tables et colonnes du schéma
3. Pour les ID spécifiques, respecte la casse exacte
"""
    
    try:
        # Generate SQL query
        response = model.generate_content(prompt)
        
        if not response or not response.text:
            return None
            
        # Get the raw response and clean it up
        sql_query = response.text.strip()
        sql_query = sql_query.rstrip(';')
        sql_query = re.sub(r'```sql\s*|\s*```', '', sql_query)
        sql_query = sql_query.strip()
        
        # Validate the query
        if not sql_query or not sql_query.upper().startswith('SELECT'):
            return None
        
        return sql_query
        
    except Exception as e:
        st.error(f"Erreur lors de la génération de la requête: {str(e)}")
        return None

def execute_query(conn, query):
    """Exécute une requête SQL et retourne les résultats sous forme de DataFrame"""
    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        
        # Récupérer les colonnes et résultats
        columns = [column[0] for column in cursor.description]
        results = cursor.fetchall()
        
        # Créer le DataFrame
        df = pd.DataFrame.from_records(results, columns=columns)
        return df
        
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        return None
        
    finally:
        if cursor:
            cursor.close()

def main():
    st.title("💬 Assistant SQL")
    
    # Initialize database connection
    conn = None
    try:
        conn_str = get_connection_string()
        conn = pyodbc.connect(conn_str, timeout=10)
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données: {str(e)}")
        st.stop()
    
    # Get database schema
    schema = get_database_schema(conn)
    if not schema:
        st.error("Impossible de récupérer le schéma de la base de données")
        st.stop()
    
    # Show database info
    with st.expander("ℹ️ Structure de la base de données"):
        for table, columns in schema.items():
            if table != 'relations':
                st.write(f"**Table: {table}**")
                st.write("Colonnes:")
                for col in columns:
                    st.write(f"- {col}")
        if schema.get('relations'):
            st.write("\n**Relations:**")
            for rel in schema['relations']:
                st.write(f"- {rel['from_table']}.{rel['from_column']} → {rel['to_table']}.{rel['to_column']}")
    
    # User input
    st.write("### 💬 Posez votre question en français")
    st.write("Je la traduirai en SQL et vous montrerai les résultats.")
    
    # Question input
    question = st.text_input("Votre question:", placeholder="Exemple: Liste de toutes les tables")
    
    if question:
        # Generate SQL query
        sql_query = generate_sql_query(question, schema)
        
        if sql_query:
            # Show the generated SQL
            with st.expander("🔍 Voir la requête SQL générée"):
                st.code(sql_query, language='sql')
            
            try:
                # Execute query and show results
                results = execute_query(conn, sql_query)
                if results is not None:
                    if len(results) > 0:
                        st.write("### 📊 Résultats")
                        st.dataframe(results)
                        st.write(f"*{len(results)} résultats trouvés*")
                    else:
                        st.info("Aucun résultat trouvé pour cette requête.")
                else:
                    st.error("Erreur lors de l'exécution de la requête. Vérifiez la syntaxe SQL.")
            except Exception as e:
                st.error(f"Erreur lors de l'exécution de la requête: {str(e)}")
        else:
            st.error("Je n'ai pas pu générer une requête SQL valide pour votre question. Essayez de reformuler.")
    
    # Footer
    st.markdown("---")
    st.markdown("*💡 Cet assistant utilise Gemini Pro pour traduire vos questions en SQL*")

if __name__ == "__main__":
    main()