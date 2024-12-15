# Importation des bibliothèques nécessaires
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from sqlalchemy import create_engine
import numpy as np
from io import BytesIO

# Connexion PostgreSQL
POSTGRES_CONN = "postgresql+psycopg2://postgres:postgres@localhost/openweathermap"

# Fonction pour traduire les descriptions météo
def translate_weather_descriptions(df):
    translation_map = {
        "overcast clouds": "Couvert",
        "clear sky": "Ciel dégagé",
        "scattered clouds": "Nuageux",
        "few clouds": "Peu nuageux",
        "broken clouds": "Partiellement nuageux",
        "light rain": "Légère pluie",
        "moderate rain": "Pluie modérée",
        "heavy rain": "Forte pluie"
    }
    df["description"] = df["description"].replace(translation_map)
    return df

# Fonction pour charger les données
@st.cache_data
def load_data():
    engine = create_engine(POSTGRES_CONN)
    with engine.connect() as conn:
        # Moyennes journalières
        df_daily_avg = pd.read_sql("SELECT * FROM meteo.moyennes_journalieres;", conn)
        # Données brutes horaires
        df_weather = pd.read_sql("SELECT * FROM meteo.donnees_brutes;", conn)
    return df_daily_avg, translate_weather_descriptions(df_weather)

# Chargement des données
df_daily_avg, df_weather = load_data()

# Suppression des doublons éventuels
df_weather = df_weather.drop_duplicates(subset="date_heure")

# Interface Streamlit
st.title("Tableau de bord Météo - La Roche sur Yon")
st.subheader("Analyse des températures et humidités")

# 1. Moyennes quotidiennes
st.header("Moyennes quotidiennes de température et humidité")
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=df_daily_avg['date'], y=df_daily_avg['temperature_moyenne'],
    mode="lines+markers", name="Température Moyenne",
    line=dict(color="red", width=2)
))
fig1.add_trace(go.Scatter(
    x=df_daily_avg['date'], y=df_daily_avg['humidite_moyenne'],
    mode="lines+markers", name="Humidité Moyenne",
    line=dict(color="blue", width=2)
))
fig1.update_layout(
    title="Température et humidité moyennes par jour",
    xaxis_title="Date", yaxis_title="Valeurs", showlegend=True
)
st.plotly_chart(fig1)

# 2. Températures horaires avec tendance linéaire
st.header("Évolution des températures heure par heure avec tendance linéaire")

# Assurer que les dates sont correctement triées
df_weather = df_weather.sort_values(by="date_heure")

# Calcul de la droite de tendance
x = pd.to_datetime(df_weather["date_heure"]).astype(np.int64) // 10**9  # Timestamps
y = df_weather["temperature"]
coefficients = np.polyfit(x, y, 1)
y_trend = coefficients[0] * x + coefficients[1]

# Création du graphique
fig2 = go.Figure()

# Courbe des températures
fig2.add_trace(go.Scatter(
    x=df_weather["date_heure"],
    y=df_weather["temperature"],
    mode="lines+markers",
    name="Température (°C)",
    line=dict(color="blue", width=2),
    marker=dict(size=6)
))

# Droite de tendance linéaire
fig2.add_trace(go.Scatter(
    x=df_weather["date_heure"],
    y=y_trend,
    mode="lines",
    name="Tendance linéaire",
    line=dict(color="orange", width=3, dash="dash")
))
fig2.update_layout(
    title="Évolution des températures heure par heure avec tendance linéaire",
    xaxis_title="Heure",
    yaxis_title="Température (°C)",
    showlegend=True
)
st.plotly_chart(fig2)

# 3. Histogramme des descriptions météo
st.header("Fréquence des conditions météorologiques")
fig3 = go.Figure()
fig3.add_trace(go.Histogram(
    x=df_weather["description"],
    marker=dict(color="lightskyblue"),
    name="Conditions météo"
))
fig3.update_layout(
    title="Répartition des descriptions météo",
    xaxis_title="Conditions météorologiques",
    yaxis_title="Nombre d'occurrences",
    bargap=0.2
)
st.plotly_chart(fig3)

# 4. Filtrage des données et export CSV
st.header("Filtrer les données horaires")
date_range = st.date_input(
    "Sélectionner la période :",
    [df_weather['date_heure'].min().date(), df_weather['date_heure'].max().date()]
)

if len(date_range) == 2:
    filtered_data = df_weather[
        (df_weather['date_heure'] >= pd.Timestamp(date_range[0])) &
        (df_weather['date_heure'] <= pd.Timestamp(date_range[1]))
    ]
    st.write("Données filtrées :", filtered_data)

    # Bouton pour exporter en CSV
    csv_buffer = BytesIO()
    filtered_data.to_csv(csv_buffer, index=False)
    st.download_button(
        label="Exporter les données filtrées en CSV",
        data=csv_buffer.getvalue(),
        file_name="donnees_filtrees.csv",
        mime="text/csv"
    )

# Section "À propos"
st.markdown("---")
st.header("À propos")
st.write("""
Ce tableau de bord météo utilise les données de l'API OpenWeatherMap pour afficher :  
- Les moyennes journalières de température et d'humidité.  
- L'évolution des températures relevées heure par heure avec une tendance linéaire.  
- Une répartition des conditions météorologiques.  

**Fonctionnalités** :  
- Filtrer les données sur une plage de dates.  
- Exporter les données filtrées en fichier CSV.  

**Technologies utilisées** : Python, PostgreSQL, Streamlit, Plotly.
""")
