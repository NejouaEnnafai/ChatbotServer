# Assistant SQL avec Streamlit et Gemini

Application web permettant d'interroger une base de données SQL Server en langage naturel.

## Prérequis

- Python 3.8 ou supérieur
- SQL Server avec les vues système accessibles (INFORMATION_SCHEMA, sys)
- Clé API Google pour Gemini

## Installation

1. Cloner le repository :
```bash
git clone https://github.com/NejouaEnnafai/chatbotsqldone.git
cd chatbotsqldone
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

## Commandes d'Exécution

### Démarrage Rapide
```bash
# Cloner le projet
git clone https://github.com/NejouaEnnafai/chatbotsqldone.git
cd chatbotsqldone

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'application
streamlit run streamlit/app.py
```

### Mise à Jour du Projet
```bash
# Mettre à jour depuis le dépôt distant
git pull origin main

# Mettre à jour les dépendances si nécessaire
pip install -r requirements.txt --upgrade
```

### Développement
```bash
# Créer une nouvelle branche
git checkout -b ma-nouvelle-fonctionnalite

# Sauvegarder les modifications
git add .
git commit -m "Description des modifications"

# Pousser les modifications
git push origin ma-nouvelle-fonctionnalite
```

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
