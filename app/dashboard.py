import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="SMA200 - Universos", layout="wide")
st.title("Valores bajo SMA200")

PATH = "data/under_sma200_all.csv"

try:
    df = pd.read_csv(PATH)
except FileNotFoundError:
    st.warning("Aún no existe data/under_sma200_all.csv. Ejecuta el workflow una vez.")
    st.stop()

if df.empty:
    st.info("No hay valores bajo SMA200 (según la lista actual).")
    st.stop()

# --- Selector de universo ---
if "Universe" in df.columns:
    universe = st.selectbox("Universo", ["Todos"] + sorted(df["Universe"].dropna().unique().tolist()))
    if universe != "Todos":
        df = df[df["Universe"] == universe].copy()
else:
    universe = "Todos"

# --- Limpieza / tipos (solo si existen) ---
for col in ["AdjClose", "SMA200", "DeltaToSMA200", "PctBelow",
            "Return_5d", "Return_21d", "Return_63d", "Vol_20d",
            "WeeklyMean", "52wHigh", "52wLow", "PctFrom52wHigh", "PctFrom52wLow",
            "SMA200_Slope_20d"]:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "PctBelow" not in df.columns:
    st.error("Falta la columna PctBelow en el CSV.")
    st.stop()

df = df.dropna(subset=["PctBelow"]).copy()
df = df.sort_values("PctBelow")  # más negativo primero

# --- Controles (sidebar) ---
st.sidebar.header("Vista")
view = st.sidebar.radio("Modo", ["Básica", "Avanzada"], index=0)

top_n = st.sidebar.selectbox(
    "Top N (más por debajo)",
    options=[10, 25, 50, 100, "Todos"],
    index=1,  # 25 por defecto
)

search = st.sidebar.text_input("Buscar ticker (contiene)", value="").strip().upper()

if search and "Ticker" in df.columns:
    df = df[df["Ticker"].astype(str).str.upper().str.contains(search, na=False)].copy()

if top_n != "Todos" and len(df) > int(top_n):
    df = df.head(int(top_n)).copy()

# --- Columnas a mostrar ---
basic_cols = [
    "RunDate", "Universe", "Ticker",
    "AdjClose", "SMA200", "DeltaToSMA200", "PctBelow",
    "Return_21d", "Vol_20d",
]

advanced_cols = basic_cols + [
    "WeeklyMean",
    "Return_5d", "Return_63d",
    "52wHigh", "52wLow", "PctFrom52wHigh", "PctFrom52wLow",
    "SMA200_Slope_20d",
]

cols_show = basic_cols if view == "Básica" else advanced_cols
cols_show = [c for c in cols_show if c in df.columns]
table_df = df[cols_show].copy()

# Redondeo para tabla
for c in table_df.select_dtypes(include="number").columns:
    table_df[c] = table_df[c].round(4)

# --- KPIs ---
c1, c2, c3 = st.columns(3)
c1.metric("Bajo SMA200", f"{len(df)}")
c2.metric("Peor % vs SMA200", f"{df['PctBelow'].min():.2f}%")
c3.metric("Mejor % (menos bajo)", f"{df['PctBelow'].max():.2f}%")

c4, c5 = st.columns(2)
if "Return_21d" in df.columns:
    c4.metric("Media retorno 1 mes (21d)", f"{df['Return_21d'].mean() * 100:.2f}%")
if "Vol_20d" in df.columns:
    c5.metric("Volatilidad mediana (20d, anual)", f"{df['Vol_20d'].median() * 100:.2f}%")

st.divider()

# --- Tabs: Tabla / Gráfico ---
tab1, tab2 = st.tabs(["Tabla", "Gráfico"])

with tab1:
    st.subheader("Listado (ordenado por % bajo SMA200)")
    st.dataframe(table_df, use_container_width=True, height=520)

with tab2:
    st.subheader("Ranking (% bajo SMA200)")
    topn = min(15, len(df))
    fig = px.bar(
        df.head(topn),
        x="PctBelow",
        y="Ticker" if "Ticker" in df.columns else df.index.astype(str),
        orientation="h",
        title=f"Top {topn} más por debajo"
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Datos generados automáticamente por GitHub Actions. David Alvarez Ruiz")
