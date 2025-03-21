import streamlit as st
import pandas as pd
import plotly.express as px
import pyodbc
from config import get_connection_string

# Configuration de la page
st.set_page_config(page_title="Test des fonctionnalités", layout="wide")

def generate_chart(df, chart_type, x_column, y_column):
    """Génère un graphique en fonction du type choisi"""
    try:
        if chart_type == "Ligne":
            fig = px.line(df, x=x_column, y=y_column, title=f"Graphique en ligne: {y_column} vs {x_column}")
        elif chart_type == "Barre":
            fig = px.bar(df, x=x_column, y=y_column, title=f"Graphique en barre: {y_column} vs {x_column}")
        elif chart_type == "Camembert":
            fig = px.pie(df, names=x_column, values=y_column, title=f"Graphique en camembert: {y_column} par {x_column}")
        return fig
    except Exception as e:
        st.error(f"Erreur lors de la génération du graphique : {str(e)}")
        return None

def execute_query(conn, query):
    """Exécute une requête SQL et retourne les résultats"""
    try:
        return pd.read_sql_query(query, conn)
    except Exception as e:
        st.error(f"Erreur lors de l'exécution de la requête : {str(e)}")
        return None

def main():
    st.title("Test des fonctionnalités avancées")
    
    # Connexion à la base de données
    try:
        conn = pyodbc.connect(get_connection_string())
        
        # Liste des requêtes de test
        test_queries = {
            "Ventes par catégorie": """
                SELECT c.CategoryName, COUNT(o.OrderID) as NombreVentes, SUM(od.Quantity * od.UnitPrice) as MontantTotal
                FROM Categories c
                JOIN Products p ON c.CategoryID = p.CategoryID
                JOIN [Order Details] od ON p.ProductID = od.ProductID
                JOIN Orders o ON od.OrderID = o.OrderID
                GROUP BY c.CategoryName
            """,
            "Evolution des ventes mensuelles": """
                SELECT FORMAT(o.OrderDate, 'yyyy-MM') as Mois, 
                       SUM(od.Quantity * od.UnitPrice) as VentesTotales
                FROM Orders o
                JOIN [Order Details] od ON o.OrderID = od.OrderID
                GROUP BY FORMAT(o.OrderDate, 'yyyy-MM')
                ORDER BY Mois
            """,
            "Top 5 produits": """
                SELECT TOP 5 p.ProductName, 
                       SUM(od.Quantity) as QuantiteVendue,
                       SUM(od.Quantity * od.UnitPrice) as MontantTotal
                FROM Products p
                JOIN [Order Details] od ON p.ProductID = od.ProductID
                GROUP BY p.ProductName
                ORDER BY QuantiteVendue DESC
            """
        }
        
        # Sélection de la requête
        selected_query = st.selectbox("Choisir une requête de test", list(test_queries.keys()))
        
        if st.button("Exécuter la requête"):
            # Exécution de la requête
            df = execute_query(conn, test_queries[selected_query])
            
            if df is not None and not df.empty:
                # Affichage des données
                st.subheader("Résultats de la requête")
                st.dataframe(df)
                
                # Section graphique
                st.subheader("Visualisation graphique")
                col1, col2, col3 = st.columns(3)
                
                # Sélection du type de graphique
                chart_type = col1.selectbox("Type de graphique", ["Ligne", "Barre", "Camembert"])
                
                # Sélection des colonnes
                numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
                all_cols = df.columns.tolist()
                
                x_col = col2.selectbox("Colonne X (axe horizontal)", all_cols)
                y_col = col3.selectbox(
                    "Colonne Y (axe vertical)", 
                    numeric_cols if chart_type != "Camembert" else all_cols
                )
                
                # Génération du graphique
                if st.button("Générer le graphique"):
                    fig = generate_chart(df, chart_type, x_col, y_col)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erreur de connexion à la base de données : {str(e)}")
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
