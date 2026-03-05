import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="IBEX35 - Bajo SMA200", layout="wide")
st.title("IBEX35 – Empresas bajo SMA200")

PATH = "data/under_sma200_all.csv"

try:
    df = pd.read_csv(PATH)
except FileNotFoundError:
    st.warning("Aún no existe data/under_sma200_all.csv. Ejecuta el workflow una vez.")
    st.stop()

if df.empty:
    st.info("No hay empresas bajo SMA200 (según la lista actual).")
    st.stop()
universe = st.selectbox("Universo", sorted(df["Universe"].unique()))
df = df[df["Universe"] == universe].copy()
# Limpieza / tipos
df["AdjClose"] = pd.to_numeric(df["AdjClose"], errors="coerce")
df["SMA200"] = pd.to_numeric(df["SMA200"], errors="coerce")
df["PctBelow"] = pd.to_numeric(df["PctBelow"], errors="coerce")

df = df.dropna(subset=["PctBelow"]).copy()
df = df.sort_values("PctBelow")  # más negativo primero

# KPIs
c1, c2, c3 = st.columns(3)
c1.metric("Empresas bajo SMA200", f"{len(df)}")
c2.metric("Peor % vs SMA200", f"{df['PctBelow'].min():.2f}%")
c3.metric("Mejor % (menos bajo)", f"{df['PctBelow'].max():.2f}%")

st.divider()

# Tabla y gráfico
left, right = st.columns([2, 1])

with left:
    st.subheader("Listado (ordenado por % bajo SMA200)")
    show = df.copy()
    show["AdjClose"] = show["AdjClose"].round(2)
    show["SMA200"] = show["SMA200"].round(2)
    show["PctBelow"] = show["PctBelow"].round(2)
    st.dataframe(show, use_container_width=True, height=420)

with right:
    st.subheader("Ranking (% bajo SMA200)")
    fig = px.bar(
        df.head(15),
        x="PctBelow",
        y="Ticker",
        orientation="h",
        title="Top 15 más por debajo"
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Datos generados automáticamente por GitHub Actions.")
