import requests
import psycopg2
from datetime import datetime
import pandas as pd
import logging
from dotenv import load_dotenv
import os

# Charger les variables d'environnement
load_dotenv()

# Étape 1 : Configuration de l'API OpenWeatherMap
API_KEY = os.getenv("API_KEY")
VILLE = os.getenv("VILLE")
URL = f'https://api.openweathermap.org/data/2.5/forecast?q={VILLE}&appid={API_KEY}&units=metric&lang=fr'

# Étape 2 : Connexion PostgreSQL
conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)
cursor = conn.cursor()

# Étape 3 : Création des tables si elles n'existent pas
cursor.execute("""
    CREATE SCHEMA IF NOT EXISTS meteo;

    CREATE TABLE IF NOT EXISTS meteo.donnees_brutes (
        id SERIAL PRIMARY KEY,
        date_heure TIMESTAMP,
        temperature FLOAT,
        humidite INT,
        description VARCHAR(255)
    );

    CREATE TABLE IF NOT EXISTS meteo.donnees_enrichies (
        id SERIAL PRIMARY KEY,
        date_heure TIMESTAMP,
        temperature FLOAT,
        humidite INT,
        description VARCHAR(255),
        categorie_temp VARCHAR(50)
    );

    CREATE TABLE IF NOT EXISTS meteo.moyennes_journalieres (
        id SERIAL PRIMARY KEY,
        date DATE,
        temperature_moyenne FLOAT,
        humidite_moyenne FLOAT
    );
""")
conn.commit()

# Étape 4 : Récupérer les données depuis l'API
response = requests.get(URL)
data = response.json()

# Transformer les données en DataFrame
donnees_meteo = []
for item in data['list']:
    donnees_meteo.append({
        'date_heure': datetime.fromtimestamp(item['dt']),
        'temperature': item['main']['temp'],
        'humidite': item['main']['humidity'],
        'description': item['weather'][0]['description']  # Maintenant en français via l'API
    })

df = pd.DataFrame(donnees_meteo)

# Ajouter une colonne "categorie_temp" en fonction de la température
def categoriser_temperature(temp):
    if temp < 5:
        return "Froid"
    elif 5 <= temp <= 20:
        return "Tempéré"
    else:
        return "Chaud"

df['categorie_temp'] = df['temperature'].apply(categoriser_temperature)

# Calculer les moyennes par jour
df['date'] = df['date_heure'].dt.date  # Extraire la date
moyennes_journalieres = df.groupby('date')[['temperature', 'humidite']].mean().reset_index()
moyennes_journalieres.columns = ['date', 'temperature_moyenne', 'humidite_moyenne']

# Étape 5 : Insérer les données dans PostgreSQL
for _, row in df[['date_heure', 'temperature', 'humidite', 'description']].iterrows():
    cursor.execute("""
        INSERT INTO meteo.donnees_brutes (date_heure, temperature, humidite, description)
        VALUES (%s, %s, %s, %s)
    """, (row['date_heure'], row['temperature'], row['humidite'], row['description']))

for _, row in df.iterrows():
    cursor.execute("""
        INSERT INTO meteo.donnees_enrichies (date_heure, temperature, humidite, description, categorie_temp)
        VALUES (%s, %s, %s, %s, %s)
    """, (row['date_heure'], row['temperature'], row['humidite'], row['description'], row['categorie_temp']))

for _, row in moyennes_journalieres.iterrows():
    cursor.execute("""
        INSERT INTO meteo.moyennes_journalieres (date, temperature_moyenne, humidite_moyenne)
        VALUES (%s, %s, %s)
    """, (row['date'], row['temperature_moyenne'], row['humidite_moyenne']))

conn.commit()

# Étape 6 : Fermer la connexion
cursor.close()
conn.close()

print("Toutes les données ont été insérées avec succès dans PostgreSQL avec des champs en français.")

# Configurer le logger
logging.basicConfig(filename='journal_meteo.txt', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logging.info("Les données météo ont été insérées dans PostgreSQL avec des champs en français.")
