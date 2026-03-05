import pandas as pd
import streamlit as st
import plotly.express as px
import os
from datetime import datetime

PATH = "data/under_sma200_all.csv"

# Info de última actualización (si existe el fichero)
import os
from datetime import datetime

if os.path.exists(PATH):
    ts = os.path.getmtime(PATH)
    st.caption("Última actualización: " + datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"))
else:
    st.caption("Última actualización del dataset: (aún no existe)")

# Botón de recarga
if st.button("Recargar datos"):
    st.rerun()

st.set_page_config(page_title="SMA200 - Universos", layout="wide")
st.title("Valores destacados por Media Semanal de los últimos 200 días")

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
    
# --- Slider para el % ---
threshold = st.sidebar.slider("Umbral (% bajo SMA200)", min_value=-30, max_value=5, value=-5, step=1)
df = df[df["PctBelow"] <= threshold].copy()

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
    colcfg = {}

    def num_col(label, fmt="%.2f"):
        return st.column_config.NumberColumn(label, format=fmt)
    
    def pct_col(label):
        # table_df tiene returns como decimal (0.05), esto lo muestra como 5.00%
        return st.column_config.NumberColumn(label, format="%.2f%%")
    
    # Formatos de precio
    if "AdjClose" in table_df.columns: colcfg["AdjClose"] = num_col("Precio", "%.2f")
    if "SMA200" in table_df.columns: colcfg["SMA200"] = num_col("SMA200", "%.2f")
    if "DeltaToSMA200" in table_df.columns: colcfg["DeltaToSMA200"] = num_col("Δ vs SMA200", "%.2f")
    if "WeeklyMean" in table_df.columns: colcfg["WeeklyMean"] = num_col("Media semanal", "%.2f")
    if "52wHigh" in table_df.columns: colcfg["52wHigh"] = num_col("52w High", "%.2f")
    if "52wLow" in table_df.columns: colcfg["52wLow"] = num_col("52w Low", "%.2f")
    
    # % (decimales -> % en pantalla)
    for c, label in [
        ("PctBelow", "% vs SMA200"),
        ("Return_5d", "Ret 5d"),
        ("Return_21d", "Ret 21d"),
        ("Return_63d", "Ret 63d"),
        ("Vol_20d", "Vol 20d (anual)"),
        ("PctFrom52wHigh", "% desde 52w High"),
        ("PctFrom52wLow", "% desde 52w Low"),
    ]:
        if c in table_df.columns:
            colcfg[c] = pct_col(label)
    
    # Ojo: SMA200_Slope_20d ya está en % (porque lo calculamos *100)
    # Así que lo formateamos como número normal con símbolo %
    if "SMA200_Slope_20d" in table_df.columns:
        colcfg["SMA200_Slope_20d"] = st.column_config.NumberColumn("Pendiente SMA200 (20d)", format="%.2f%%")
    
    st.dataframe(
        table_df,
        use_container_width=True,
        height=520,
        column_config=colcfg,
    )

with tab2:
    st.subheader("Ranking (% bajo SMA200)")

    topn = min(15, len(df))
    dplot = df.sort_values("PctBelow").head(topn).copy()

    # Hover: elegimos columnas disponibles
    hover_cols = [c for c in ["AdjClose", "SMA200", "DeltaToSMA200", "Return_5d", "Return_21d", "Return_63d", "Vol_20d"]
                  if c in dplot.columns]

    fig = px.bar(
        dplot,
        x="PctBelow",
        y="Ticker",
        orientation="h",
        text="PctBelow",
        hover_data=hover_cols,
        title=f"Top {topn} más por debajo",
    )

    # Etiquetas en barras como %
    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")

    # Eje X como %
    fig.update_xaxes(title_text="% vs SMA200", ticksuffix="%", zeroline=True)
    fig.update_yaxes(title_text="")

    # Hover template: usa customdata en el mismo orden que hover_cols
    lines = ["<b>%{y}</b>", "Pct vs SMA200: %{x:.2f}%"]
    nice = {
        "AdjClose": "Precio",
        "SMA200": "SMA200",
        "DeltaToSMA200": "Δ vs SMA200",
        "Return_5d": "Ret 5d",
        "Return_21d": "Ret 21d",
        "Return_63d": "Ret 63d",
        "Vol_20d": "Vol 20d (anual)",
    }
    
    for i, col in enumerate(hover_cols):
        label = nice.get(col, col)
        if col in ["AdjClose", "SMA200", "DeltaToSMA200"]:
            lines.append(f"{label}: %{{customdata[{i}]:.2f}}")
        elif col in ["Return_5d", "Return_21d", "Return_63d", "Vol_20d"]:
            # decimales: 0.05 -> 5.00%
            lines.append(f"{label}: %{{customdata[{i}]:.2%}}")
        else:
            lines.append(f"{label}: %{{customdata[{i}]}}")

    fig.update_traces(hovertemplate="<br>".join(lines) + "<extra></extra>")

    # Margen para que quepa el texto fuera
    fig.update_layout(margin=dict(l=10, r=10, t=60, b=10))

    st.plotly_chart(fig, use_container_width=True)
st.caption("Datos generados automáticamente por GitHub Actions. David Alvarez Ruiz")
