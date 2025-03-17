# ChatbotSQL avec FastAPI et Streamlit

Un assistant conversationnel intelligent qui permet d'interroger une base de données SQL en langage naturel. Le projet utilise FastAPI pour l'API REST, Streamlit pour l'interface utilisateur, et le modèle Gemini de Google pour la compréhension du langage naturel.

## Fonctionnalités Principales

- 💬 **Conversation Naturelle** : Posez vos questions en langage naturel
- 🔍 **Conversion en SQL** : Transformation automatique des questions en requêtes SQL
- 📊 **Visualisation** : Interface utilisateur intuitive avec Streamlit
- 🚀 **API REST** : Endpoints FastAPI pour l'intégration avec d'autres applications
- 🔒 **Sécurité** : Support de l'authentification Windows et SQL Server
- 📝 **Logs** : Système de logging détaillé pour le debugging

## Structure du Projet
```
ChatbotClean/
├── api/
│   └── main.py          # API FastAPI et logique du chatbot
├── streamlit/
│   ├── app.py          # Interface utilisateur Streamlit
│   ├── config.py       # Configuration partagée
│   └── static/         # Ressources statiques
├── .env                # Variables d'environnement
└── requirements.txt    # Dépendances Python
```

## Prérequis Détaillés

1. **Python**
   - Version 3.11 ou supérieure
   - Vérifiez avec : `python --version`

2. **SQL Server**
   - SQL Server 2019 ou supérieur
   - Configuration réseau activée
   - Port par défaut : 1433
   - Authentification Windows ou SQL Server configurée

3. **Clé API Google**
   - Compte Google Cloud Platform
   - API Gemini activée
   - Clé API avec droits suffisants

4. **Système**
   - Windows 10/11 (recommandé)
   - 4GB RAM minimum
   - Connexion Internet stable

## Guide d'Installation Détaillé

1. **Préparation de l'Environnement**
   ```bash
   # déplacez-vous dans le dossier du projet
   cd ChatbotClean
   
   # Créer l'environnement virtuel
   python -m venv venv
   
   # Activer l'environnement (Windows)
   venv\Scripts\activate
   
   # Vérifier l'activation
   where python  # Doit montrer le python de l'environnement virtuel
   ```

2. **Installation des Dépendances**
   ```bash
   # Mettre à jour pip
   python -m pip install --upgrade pip
   
   # Installer les dépendances
   pip install -r requirements.txt
   
   # Vérifier l'installation
   pip list  # Doit afficher toutes les dépendances
   ```

3. **Configuration de l'Environnement**
   Créez un fichier `.env` à la racine avec ces variables :
   ```env
   # API Key Google
   GOOGLE_API_KEY="votre_clé_api_gemini"
   
   # Configuration SQL Server
   DB_SERVER="nom_serveur_sql"  # Exemple: DESKTOP-ABC\SQLEXPRESS
   DB_NAME="nom_base_données"
   DB_AUTH_TYPE="windows"       # ou "sql_server"
   DB_TIMEOUT=30
   
   # Ports des serveurs (optionnel)
   FASTAPI_PORT=8000      # Port par défaut pour FastAPI
   STREAMLIT_PORT=8501    # Port par défaut pour Streamlit
   
   # Optionnel pour auth SQL Server
   DB_USER="votre_utilisateur"
   DB_PASSWORD="votre_mot_de_passe"
   ```

4. **Vérification de l'Installation**
   ```bash
   # 1. Démarrer l'API FastAPI
   python -m uvicorn api.main:app --reload
   # Vérifier : http://127.0.0.1:8000/docs
   
   # 2. Dans un nouveau terminal, démarrer Streamlit
   streamlit run streamlit/app.py
   # Vérifier : http://localhost:8501
   ```

## Utilisation de l'API REST

### Endpoint Principal : POST /chat

Cet endpoint traite les questions des utilisateurs et retourne les réponses.

**Format de Requête :**
```json
{
  "text": "votre question ici"
}
```

**Format de Réponse :**
```json
{
  "answer": "Réponse en langage naturel",
  "sql_query": "SELECT * FROM table",  # Si applicable
  "data": [                           # Résultats SQL si applicable
    {
      "colonne1": "valeur1",
      "colonne2": "valeur2"
    }
  ]
}
```

### Exemples d'Utilisation

1. **Via cURL :**
   ```bash
   curl -X POST "http://127.0.0.1:8000/chat" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"Montre-moi tous les biens immobiliers\"}"
   ```

2. **Via Python :**
   ```python
   import requests
   
   def ask_chatbot(question):
       url = "http://127.0.0.1:8000/chat"
       response = requests.post(url, json={"text": question})
       return response.json()
   
   # Exemple
   result = ask_chatbot("Quelle est la surface moyenne des appartements?")
   print(result)
   ```

3. **Via JavaScript :**
   ```javascript
   async function askChatbot(question) {
     const response = await fetch('http://127.0.0.1:8000/chat', {
       method: 'POST',
       headers: {
         'Content-Type': 'application/json'
       },
       body: JSON.stringify({
         text: question
       })
     });
     return await response.json();
   }
   
   // Exemple
   askChatbot('Liste tous les biens avec leur prix')
     .then(data => console.log(data))
     .catch(error => console.error(error));
   ```

## Interface Streamlit

L'interface Streamlit offre une expérience utilisateur intuitive :

1. **Démarrage :**
   ```bash
   streamlit run streamlit/app.py
   ```

2. **Fonctionnalités :**
   - Chat en temps réel
   - Historique des conversations
   - Visualisation des résultats SQL
   - Mode sombre/clair
   - Responsive design

## Dépannage

### Problèmes Courants

1. **Erreur de Connexion SQL**
   - Vérifier le format du nom du serveur
   - Tester la connexion avec SQL Server Management Studio
   - Vérifier les logs dans la console

2. **Erreur API Gemini**
   - Vérifier la validité de la clé API
   - Vérifier la connexion Internet
   - Consulter les quotas d'utilisation

3. **Erreur Streamlit**
   - Vérifier que le port 8501 est libre
   - Redémarrer l'application
   - Effacer le cache : `.streamlit/`

## Notes Techniques

- **Performance** : L'API utilise un pool de connexions SQL
- **Sécurité** : Les requêtes SQL sont nettoyées et validées
- **Logs** : Niveau INFO par défaut, configurable en DEBUG
- **Cache** : Streamlit met en cache les requêtes fréquentes
- **Async** : FastAPI gère les requêtes de manière asynchrone

## Support

Pour obtenir de l'aide :
1. Consulter les logs détaillés
2. Vérifier la documentation Swagger UI
3. Contacter l'équipe de maintenance
