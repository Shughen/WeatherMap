# Importation des bibliothèques nécessaires
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
        df_daily_avg = pd.read_sql("SELECT * FROM meteo.vue_moyennes_journalieres;", conn)
        # Données brutes horaires
        df_weather = pd.read_sql("SELECT * FROM meteo.donnees_brutes;", conn)
    return df_daily_avg, translate_weather_descriptions(df_weather)

# Chargement des données
df_daily_avg, df_weather = load_data()

# Interface Streamlit
st.title("Tableau de bord Météo Interactif")
st.subheader("Analyse des températures et humidités à La Roche sur Yon")

# 1. Moyennes quotidiennes
# Création du graphique avec deux axes Y
fig1 = make_subplots(specs=[[{"secondary_y": True}]])

# Tracer la température moyenne
fig1.add_trace(
    go.Scatter(
        x=df_daily_avg['date'],
        y=df_daily_avg['temperature_moyenne'],
        mode="lines+markers",
        name="Température Moyenne",
        line=dict(color="red", width=2)
    ),
    secondary_y=False  # Axe Y principal (gauche)
)

# Tracer l'humidité moyenne
fig1.add_trace(
    go.Scatter(
        x=df_daily_avg['date'],
        y=df_daily_avg['humidite_moyenne'],
        mode="lines+markers",
        name="Humidité Moyenne",
        line=dict(color="blue", width=2)
    ),
    secondary_y=True  # Axe Y secondaire (droite)
)

# Mise en forme
fig1.update_layout(
    title="Température et humidité moyennes par jour",
    xaxis_title="Date",
    yaxis=dict(title="Température Moyenne (°C)", color="red"),
    yaxis2=dict(title="Humidité Moyenne (%)", overlaying="y", side="right", color="blue"),
    legend=dict(x=0.5, y=1.15, orientation="h")
)

st.plotly_chart(fig1)

# 2. Températures avec tendance linéaire
st.header("Évolution quotidienne des températures avec tendance linéaire")

# Agréger les données par jour
df_weather['date'] = df_weather['date_heure'].dt.date  # Extraire seulement la date
df_daily_temp = df_weather.groupby('date')['temperature'].mean().reset_index()

# Calcul de la droite de tendance
x = pd.to_datetime(df_daily_temp['date']).astype('int64') // 10**9  # Convertir datetime en timestamps
y = df_daily_temp["temperature"]
coefficients = np.polyfit(x, y, 1)
y_trend = coefficients[0] * x + coefficients[1]

# Création du graphique
fig2 = go.Figure()
fig2.add_trace(go.Scatter(
    x=df_daily_temp["date"],
    y=df_daily_temp["temperature"],
    mode="lines+markers",
    name="Température Moyenne (°C)",
    line=dict(color="blue", width=2)
))
fig2.add_trace(go.Scatter(
    x=df_daily_temp["date"],
    y=y_trend,
    mode="lines",
    name="Tendance linéaire",
    line=dict(color="orange", width=3, dash="dash")
))
fig2.update_layout(
    title="Évolution quotidienne des températures avec tendance linéaire",
    xaxis_title="Date",
    yaxis_title="Température Moyenne (°C)",
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
    st.write("Données filtrées :", filtered_data.drop(columns=["id"]))

    # Bouton pour exporter en CSV
    csv_buffer = BytesIO()
    filtered_data.to_csv(csv_buffer, index=False, encoding='utf-8-sig', sep=';', decimal=',')
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
