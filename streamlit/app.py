import streamlit as st
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

# Configuration Google Gemini
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    st.error("Veuillez définir votre GOOGLE_API_KEY dans le fichier .env")
    st.stop()

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')


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
        ### Assistant SQL
        
        Cet assistant vous aide à interroger votre base de données SQL Server en langage naturel.
        
        **Fonctionnalités :**
        - Traduction en langage SQL
        - Visualisation des résultats
        - Support de SQL Server
        
        **Technologies :**
        - Streamlit
        - Google Gemini
        - SQL Server
        
        **Version :** 1.0.0
        """)
        
       
@st.cache_data(ttl=3600)
def get_database_schema(_conn):
    """
    Récupère le schéma de la base de données
    """
    schema = {
        'tables': [],
        'relations': []
    }
    
    try:
        cursor = _conn.cursor()
        
        # Récupérer les tables et leurs colonnes
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
    st.set_page_config(
        page_title="Assistant SQL",
        page_icon="",
        layout="wide"
    )
    
    # Afficher la sidebar À propos
    show_about()
    
    # Titre principal
    st.title("Assistant SQL")
    
    # Initialize database connection
    conn = None
    try:
        conn = pyodbc.connect(get_connection_string())
        
        # Get database schema
        schema = get_database_schema(conn)
        
        if schema:
            # User input
            question = st.text_area(
                "Posez votre question en langage naturel",
                placeholder="Exemple : Quels sont les 10 derniers biens ajoutés ?",
                help="Décrivez ce que vous souhaitez savoir à propos de vos données."
            )
            
            # Generate and execute query
            if st.button("Générer la requête"):
                sql_query = generate_sql_query(question, schema)
                
                if sql_query:
                    # Show the generated SQL
                    with st.expander("Voir la requête SQL générée"):
                        st.code(sql_query, language='sql')
                    
                    try:
                        # Execute query and show results
                        results = execute_query(conn, sql_query)
                        if results is not None and not results.empty:
                            st.dataframe(
                                results,
                                use_container_width=True,
                                hide_index=True
                            )
                        else:
                            st.info("Aucun résultat trouvé.")
                    except Exception as e:
                        st.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {str(e)}")
    
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()