# Assistant SQL avec Streamlit et Gemini

Application web permettant d'interroger une base de données SQL Server en langage naturel.

## Prérequis

- Python 3.8 ou supérieur (si installation standard)
- SQL Server avec les vues système accessibles (INFORMATION_SCHEMA, sys)
- Clé API Google pour Gemini
- Docker (optionnel, pour déploiement conteneurisé)

## Installation

### 1. Installation Standard (Sans Docker)

1. Cloner le repository :
```bash
git clone <votre-repo>
cd <votre-repo>
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

3. Configurer le fichier `.env` (voir section Configuration)

4. Lancer l'application :
```bash
streamlit run streamlit/app.py
```

### 2. Installation avec Docker (Recommandé pour la Production)

#### Prérequis Docker
- Docker installé sur le serveur
- Accès réseau au serveur SQL Server
- Port 80 disponible (ou autre port de votre choix)

#### Étapes de Déploiement

1. Configurer le fichier `.env` :
   - Copier `.env.example` vers `.env`
   - Remplir les informations (voir section Configuration)
   - **Important** : Mettre `DB_AUTH_TYPE=sql_server`

2. Construire l'image :
```bash
docker build -t sql-assistant .
```

3. Lancer le conteneur :
```bash
docker run -d \
  --name sql-assistant \
  -p 80:8501 \
  --env-file .env \
  --restart unless-stopped \
  sql-assistant
```

#### Gestion du Conteneur

- Voir les logs :
```bash
docker logs sql-assistant
```

- Redémarrer l'application :
```bash
docker restart sql-assistant
```

- Arrêter l'application :
```bash
docker stop sql-assistant
```

- Mettre à jour la configuration :
```bash
# 1. Modifier le fichier .env
# 2. Redémarrer le conteneur
docker restart sql-assistant
```

#### Avantages de Docker
- Installation simplifiée (pas de dépendances Python à gérer)
- Isolation de l'environnement
- Redémarrage automatique en cas de crash
- Facilité de mise à jour
- Gestion des logs centralisée

## Configuration

1. Créer un fichier `.env` à la racine du projet avec les informations suivantes :

```env
# Clé API Google (Obligatoire)
GOOGLE_API_KEY="votre-clé-api"

# Configuration Base de Données
DB_SERVER=nom-serveur
DB_NAME=nom-base
DB_USER=utilisateur-sql
DB_PASSWORD=mot-de-passe-sql
DB_PORT=1433
DB_AUTH_TYPE=sql_server  # Utiliser 'sql_server' en production

# Configuration IA (Optionnel)
SYSTEM_PROMPT="""Votre prompt personnalisé {schema_desc} {question}"""
```

2. Configurer les permissions SQL Server :
   - L'utilisateur doit avoir accès en lecture à :
     - INFORMATION_SCHEMA.TABLES
     - INFORMATION_SCHEMA.COLUMNS
     - sys.foreign_keys
     - sys.tables
     - sys.columns
     - Toutes les tables de la base de données

3. Configuration du serveur :
   - Ouvrir le port 1433 (ou votre port SQL Server)
   - Activer le chiffrement SSL pour SQL Server
   - S'assurer que le certificat SSL est valide

## Sécurité

- Ne jamais commiter le fichier `.env` dans le repository
- Utiliser des secrets sécurisés pour les mots de passe en production
- Activer le chiffrement SSL pour la connexion SQL Server
- Limiter les permissions de l'utilisateur SQL aux opérations nécessaires
- Configurer un pare-feu pour restreindre l'accès à la base de données

## Maintenance

- Surveiller les logs Streamlit pour les erreurs
- Vérifier régulièrement les mises à jour des dépendances
- Sauvegarder régulièrement la configuration
- Monitorer l'utilisation de l'API Gemini

## Support

Pour toute question ou problème :
- Ouvrir une issue sur le repository
- Contacter l'équipe de maintenance

## Licence

[Votre licence]
