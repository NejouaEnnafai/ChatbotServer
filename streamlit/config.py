# Configuration SQL Server
SQL_CONFIG = {
    'SERVER': 'DESKTOP-U96K83L\\SQLEXPRESS',  # À configurer en production
    'DATABASE': 'immobilier',  # À configurer en production
    'DRIVER': 'SQL Server'
}

def get_connection_string():
    """Retourne la chaîne de connexion SQL Server"""
    return (
        f'DRIVER={{SQL Server}};'
        f'SERVER={SQL_CONFIG["SERVER"]};'
        f'DATABASE={SQL_CONFIG["DATABASE"]};'
        'Trusted_Connection=yes;'
    )
