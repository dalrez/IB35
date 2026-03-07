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

# --- Selector de universo (por defecto INDICES) ---
options = ["Todos"] + sorted(df["Universe"].dropna().unique().tolist())

preferred_universe = "INDICES"
default_idx = options.index(preferred_universe) if preferred_universe in options else 0

universe = st.selectbox("Seleccione el mercado", options, index=default_idx)
if universe != "Todos":
    df = df[df["Universe"] == universe].copy()
    
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
    "RunDate", "Universe", "Ticker","Name",
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
# --- Tabla: mostrar returns/vol en % (pero sin tocar los datos originales) ---
table_view = table_df.copy()

cols_decimal_as_pct = [c for c in ["Return_5d", "Return_21d", "Return_63d", "Vol_20d"] if c in table_view.columns]
for c in cols_decimal_as_pct:
    table_view[c] = table_view[c] * 100  # 0.05 -> 5.0

# Redondeo para tabla
for c in table_view.select_dtypes(include="number").columns:
    table_view[c] = table_view[c].round(4)

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
    c4.metric("Media Rentabilidad 1 mes (21d)", f"{df['Return_21d'].mean() * 100:.2f}%")
if "Vol_20d" in df.columns:
    c5.metric("Volatilidad media (20d, anual)", f"{df['Vol_20d'].mean() * 100:.2f}%")

st.divider()

# --- Tabs: Tabla / Gráfico ---
tab1, tab2, tab3 = st.tabs(["Tabla", "Gráfico", "Detalle"])

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
        table_view,
        use_container_width=True,
        height=520,
        column_config=colcfg,
    )

with tab2:
    st.subheader("Ranking (% bajo SMA200)")

    topn = min(15, len(df))
    dplot = df.sort_values("PctBelow").head(topn).copy()
    dplot["Display"] = dplot.apply(
    lambda r: f"{r['Ticker']} — {r['Name']}" if "Name" in dplot.columns and str(r.get("Name", "")).strip() else str(r["Ticker"]),
    axis=1
)

    # Hover: elegimos columnas disponibles
    hover_cols = [c for c in ["AdjClose", "SMA200", "DeltaToSMA200", "Return_5d", "Return_21d", "Return_63d", "Vol_20d"]
                  if c in dplot.columns]

    fig = px.bar(
        dplot,
        x="PctBelow",
        y="Display",
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
    
with tab3:
    st.subheader("Detalle: precio vs SMA200")

    # Intentamos cargar el histórico del universo seleccionado
    # Si elegiste "Todos", te obligo a elegir uno concreto para el histórico
    if universe == "Todos":
        st.info("Selecciona un universo concreto arriba para ver el histórico.")
        st.stop()

    hist_path = f"data/prices_{universe}.csv"

    try:
        hist = pd.read_csv(hist_path, parse_dates=["Date"])
    except FileNotFoundError:
        st.warning(f"No existe {hist_path} todavía. Ejecuta el workflow para generarlo.")
        st.stop()

    if hist.empty:
        st.info("Histórico vacío.")
        st.stop()

    # --- Selector de ticker: SOLO NOMBRE (usando cache y CSV de índices) ---
    tickers_available = sorted(hist["Ticker"].dropna().astype(str).unique().tolist())
    if not tickers_available:
        st.info("No hay tickers en el histórico.")
        st.stop()
    
    # Construimos un mapa Ticker -> Name desde:
    # 1) names_cache.csv (yfinance)
    # 2) tickers_indices.csv (manual) con prioridad
    name_map = {}
    
    # 1) Cache yfinance
    try:
        nc = pd.read_csv("data/names_cache.csv")
        if "Ticker" in nc.columns and "Name" in nc.columns:
            nc["Ticker"] = nc["Ticker"].astype(str).str.strip().str.upper()
            nc["Name"] = nc["Name"].astype(str).fillna("").str.strip()
            name_map.update(dict(zip(nc["Ticker"], nc["Name"])))
    except FileNotFoundError:
        pass
    
    # 2) Nombres manuales de índices (prioridad)
    try:
        idx = pd.read_csv("data/tickers_indices.csv")
        if "Ticker" in idx.columns and "Name" in idx.columns:
            idx["Ticker"] = idx["Ticker"].astype(str).str.strip().str.upper()
            idx["Name"] = idx["Name"].astype(str).fillna("").str.strip()
            # pisa lo anterior si hay coincidencias
            name_map.update(dict(zip(idx["Ticker"], idx["Name"])))
    except FileNotFoundError:
        pass
    
    # Labels: solo nombre; si falta, caemos a ticker
    labels = []
    inv = {}
    for t in tickers_available:
        t_norm = str(t).strip().upper()
        label = name_map.get(t_norm, "").strip()
        if not label:
            label = t_norm  # fallback si no hay nombre
    
        # Evitar colisiones si dos nombres iguales
        if label in inv:
            label = f"{label} ({t_norm})"
    
        inv[label] = t_norm
        labels.append(label)
    
    # Preferido por defecto: ^GSPC (si existe)
    preferred_ticker = "^GSPC"
    preferred_label = None
    if preferred_ticker in tickers_available:
        nm = name_map.get(preferred_ticker, "").strip()
        preferred_label = nm if nm else preferred_ticker
    
    default_index = labels.index(preferred_label) if preferred_label in labels else 0
    
    chosen_label = st.selectbox("Nombre", labels, index=default_index)
    ticker = inv[chosen_label]


    # Filtramos serie
    s = hist[hist["Ticker"] == ticker].sort_values("Date").copy()
    if s.empty:
        st.info("No hay datos para ese ticker.")
        st.stop()

    # Calculamos SMA200 para el gráfico (sobre el histórico)
    s["AdjClose"] = pd.to_numeric(s["AdjClose"], errors="coerce")
    s = s.dropna(subset=["AdjClose"]).copy()
    s["SMA200"] = s["AdjClose"].rolling(200).mean()

    # Mostramos últimos N puntos (ajustable)
    last_n = st.slider("Días a mostrar", min_value=60, max_value=400, value=260, step=20)
    s_plot = s.tail(last_n).copy()

    # Nombre para mostrar en el título (si existe en df)
    display_name = ticker
    if "Name" in df.columns:
        m = df[df["Ticker"].astype(str) == str(ticker)]
        if not m.empty:
            n = str(m.iloc[0].get("Name", "")).strip()
            if n:
                display_name = n  # solo nombre
                
    # Gráfico
    fig = px.line(
        s_plot,
        x="Date",
        y=["AdjClose", "SMA200"],
        title=f"{display_name} — Precio vs SMA200 ({universe})",
    )
    fig.update_yaxes(title_text="Precio")
    fig.update_xaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True)

    # KPIs rápidos del ticker
    last = s.iloc[-1]
    sma = last.get("SMA200")
    if pd.notna(sma) and sma != 0:
        pct = (last["AdjClose"] / sma - 1) * 100
        st.caption(f"Último: {last['AdjClose']:.2f} | SMA200: {sma:.2f} | % vs SMA200: {pct:.2f}%")

st.caption("Realizado por David Álvarez Ruiz")
