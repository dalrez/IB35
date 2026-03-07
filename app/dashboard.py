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
    st.subheader("Listado (tabla pro)")

    from st_aggrid import AgGrid, GridOptionsBuilder
    from st_aggrid.shared import GridUpdateMode

    # Partimos de table_view (recomendado)
    pretty = table_view.copy()

    # Renombrar columnas a nombres humanos
    rename = {
        "RunDate": "Fecha",
        "Universe": "Universo",
        "Ticker": "Ticker",
        "Name": "Nombre",
        "AdjClose": "Precio",
        "SMA200": "SMA200",
        "DeltaToSMA200": "Δ vs SMA200",
        "PctBelow": "% vs SMA200",
        "WeeklyMean": "Media semanal",
        "Return_5d": "Ret 5d",
        "Return_21d": "Ret 21d",
        "Return_63d": "Ret 63d",
        "Vol_20d": "Vol 20d (anual)",
        "52wHigh": "52w High",
        "52wLow": "52w Low",
        "PctFrom52wHigh": "% desde 52w High",
        "PctFrom52wLow": "% desde 52w Low",
        "SMA200_Slope_20d": "Pendiente SMA200 (20d)",
    }
    pretty = pretty.rename(columns={k: v for k, v in rename.items() if k in pretty.columns})

    # Orden recomendado
    order = [
        "Fecha", "Universo", "Ticker", "Nombre",
        "Precio", "SMA200", "Δ vs SMA200", "% vs SMA200",
        "Ret 21d", "Ret 63d", "Vol 20d (anual)",
        "% desde 52w Low", "% desde 52w High",
        "Pendiente SMA200 (20d)",
        "Ret 5d", "Media semanal", "52w High", "52w Low",
    ]
    cols = [c for c in order if c in pretty.columns] + [c for c in pretty.columns if c not in order]
    pretty = pretty[cols]

    # Redondeo
    for c in pretty.select_dtypes(include="number").columns:
        pretty[c] = pretty[c].round(4)

    # --- AgGrid options ---
    gb = GridOptionsBuilder.from_dataframe(pretty)
    gb.configure_default_column(
        resizable=True,
        sortable=True,
        filter=True,
        floatingFilter=True,
        wrapText=True,
        autoHeight=True,
    )

    # Selección de fila
    gb.configure_selection(selection_mode="single", use_checkbox=False)

    # Fijar columnas clave
    if "Ticker" in pretty.columns:
        gb.configure_column("Ticker", pinned="left", width=110)
    if "Nombre" in pretty.columns:
        gb.configure_column("Nombre", pinned="left", width=280)
    if "Universo" in pretty.columns:
        gb.configure_column("Universo", width=130)

    # Formatos numéricos
    for c in ["Precio", "SMA200", "Δ vs SMA200", "Media semanal", "52w High", "52w Low"]:
        if c in pretty.columns:
            gb.configure_column(
                c,
                type=["numericColumn"],
                valueFormatter="(params.value==null)?'':params.value.toFixed(2)"
            )

    # % columnas (ya están en % en table_view/pretty)
    pct_cols = ["% vs SMA200", "Ret 5d", "Ret 21d", "Ret 63d", "Vol 20d (anual)",
                "% desde 52w High", "% desde 52w Low", "Pendiente SMA200 (20d)"]
    for c in pct_cols:
        if c in pretty.columns:
            gb.configure_column(
                c,
                type=["numericColumn"],
                valueFormatter="(params.value==null)?'':params.value.toFixed(2) + '%'"
            )

    # Paginación
    n = len(pretty)
    if n <= 25:
        gb.configure_pagination(enabled=False)
    else:
        gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=25)

    gridOptions = gb.build()

    # Altura dinámica
    header_px = 85
    row_px = 32
    min_h = 220
    max_h = 720
    grid_height = min(max_h, max(min_h, header_px + n * row_px))

    grid = AgGrid(
        pretty,
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        height=grid_height,
        theme="streamlit",
    )

    selected = grid.get("selected_rows", None)
        
    row = None
    # Puede venir como DataFrame (común) o como lista de dicts (según versión)
    if selected is None:
        row = None
    elif hasattr(selected, "empty"):  # pandas DataFrame
        if not selected.empty:
            row = selected.iloc[0].to_dict()
    elif isinstance(selected, list):
        if len(selected) > 0:
            row = selected[0]
        
    if row and "Ticker" in row and row["Ticker"]:
        st.session_state["selected_ticker"] = str(row["Ticker"]).strip()
        st.session_state["selected_row"] = row  # <-- guardamos la fila completa
        st.caption(f"Seleccionado: **{st.session_state['selected_ticker']}** → ve a la pestaña **Detalle**")
            
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

    # Si elegiste "Todos", obligamos a elegir uno concreto para el histórico
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

    # Preferido por defecto: el seleccionado en tabla, si no ^GSPC
    preferred_ticker = st.session_state.get("selected_ticker", "^GSPC")

    tickers_available = sorted(hist["Ticker"].dropna().astype(str).unique().tolist())
    if not tickers_available:
        st.info("No hay tickers en el histórico.")
        st.stop()

    # Construimos mapa Ticker -> Name desde:
    # 1) names_cache.csv (yfinance)
    # 2) tickers_indices.csv (manual) con prioridad
    name_map = {}

    try:
        nc = pd.read_csv("data/names_cache.csv")
        if "Ticker" in nc.columns and "Name" in nc.columns:
            nc["Ticker"] = nc["Ticker"].astype(str).str.strip().str.upper()
            nc["Name"] = nc["Name"].astype(str).fillna("").str.strip()
            name_map.update(dict(zip(nc["Ticker"], nc["Name"])))
    except FileNotFoundError:
        pass

    try:
        idx = pd.read_csv("data/tickers_indices.csv")
        if "Ticker" in idx.columns and "Name" in idx.columns:
            idx["Ticker"] = idx["Ticker"].astype(str).str.strip().str.upper()
            idx["Name"] = idx["Name"].astype(str).fillna("").str.strip()
            name_map.update(dict(zip(idx["Ticker"], idx["Name"])))  # prioridad
    except FileNotFoundError:
        pass

    # Labels: solo nombre; si falta, caemos a ticker; evitamos colisiones
    labels = []
    inv = {}
    for t in tickers_available:
        t_norm = str(t).strip().upper()
        label = name_map.get(t_norm, "").strip()
        if not label:
            label = t_norm
        if label in inv:
            label = f"{label} ({t_norm})"
        inv[label] = t_norm
        labels.append(label)

    # índice por defecto según ticker preferido
    preferred_label = name_map.get(preferred_ticker, "").strip() or preferred_ticker
    if preferred_label in inv:
        default_index = labels.index(preferred_label)
    else:
        # fallback: si el preferido no está en este universo, el primero
        default_index = 0

    chosen_label = st.selectbox("Nombre", labels, index=default_index)
    ticker = inv[chosen_label]

    # --- KPIs (siempre se actualizan con el selector de Detalle) ---
    
    import math
    
    def _fmt_num(x, decimals=2):
        try:
            return f"{float(x):.{decimals}f}"
        except Exception:
            return "—"
    
    def _fmt_pct(x):
        try:
            v = float(x)
            # si viene en decimal (0.05) lo pasamos a %
            v = v * 100 if abs(v) < 2 else v
            return f"{v:.2f}%"
        except Exception:
            return "—"
    
    # 1) Intentamos sacar métricas del df del universo (df ya está filtrado por universe arriba)
    row_today = None
    if "Ticker" in df.columns and len(df) > 0:
        m = df[df["Ticker"].astype(str).str.strip().str.upper() == str(ticker).strip().upper()]
        if not m.empty:
            row_today = m.iloc[0]
    
    # KPIs base (preferimos df si existe)
    precio = row_today.get("AdjClose") if row_today is not None and "AdjClose" in row_today else None
    sma200 = row_today.get("SMA200") if row_today is not None and "SMA200" in row_today else None
    pct_vs = row_today.get("PctBelow") if row_today is not None and "PctBelow" in row_today else None
    ret21 = row_today.get("Return_21d") if row_today is not None and "Return_21d" in row_today else None
    vol20 = row_today.get("Vol_20d") if row_today is not None and "Vol_20d" in row_today else None
    
    # 2) Fallback: calcular desde histórico si faltan
    h = hist[hist["Ticker"].astype(str).str.strip().str.upper() == str(ticker).strip().upper()].sort_values("Date").copy()
    if not h.empty:
        h["AdjClose"] = pd.to_numeric(h["AdjClose"], errors="coerce")
        h = h.dropna(subset=["AdjClose"]).copy()
    
        if len(h) >= 1:
            last_price = float(h.iloc[-1]["AdjClose"])
            if precio is None:
                precio = last_price
    
        # SMA200 y % vs SMA200 desde histórico
        if len(h) >= 200:
            sma_series = h["AdjClose"].rolling(200).mean()
            last_sma = float(sma_series.iloc[-1])
            if sma200 is None:
                sma200 = last_sma
            if pct_vs is None and last_sma != 0:
                pct_vs = (last_price / last_sma - 1) * 100
    
        # Return 21d desde histórico (21 sesiones)
        if ret21 is None and len(h) >= 22:
            p_now = float(h.iloc[-1]["AdjClose"])
            p_21 = float(h.iloc[-22]["AdjClose"])  # 21 sesiones atrás (porque incluye hoy)
            if p_21 != 0:
                ret21 = (p_now / p_21) - 1.0  # decimal
    
        # Vol 20d anualizada desde histórico
        if vol20 is None and len(h) >= 21:
            # retornos diarios últimos 20 días
            rets = h["AdjClose"].pct_change().dropna().tail(20)
            if len(rets) >= 10:  # mínimo razonable para evitar ruido
                vol20 = float(rets.std(ddof=0) * math.sqrt(252))  # decimal
    
    # Pintamos KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Precio", _fmt_num(precio, 2))
    c2.metric("SMA200", _fmt_num(sma200, 2))
    c3.metric("% vs SMA200", _fmt_pct(pct_vs))
    c4.metric("Ret 21d", _fmt_pct(ret21))
    c5.metric("Vol 20d (anual)", _fmt_pct(vol20))
    
    st.divider()

    # Serie del ticker
    s = hist[hist["Ticker"].astype(str).str.upper() == ticker].sort_values("Date").copy()
    if s.empty:
        st.info("No hay datos para ese ticker.")
        st.stop()

    # SMA200
    s["AdjClose"] = pd.to_numeric(s["AdjClose"], errors="coerce")
    s = s.dropna(subset=["AdjClose"]).copy()
    s["SMA200"] = s["AdjClose"].rolling(200).mean()

    last_n = st.slider("Días a mostrar", min_value=60, max_value=400, value=260, step=20)
    s_plot = s.tail(last_n).copy()

    # Nombre para mostrar en el título (solo nombre)
    display_name = name_map.get(ticker, "").strip() or ticker

    fig = px.line(
        s_plot,
        x="Date",
        y=["AdjClose", "SMA200"],
        title=f"{display_name} — Precio vs SMA200 ({universe})",
    )
    # Tooltip limpio y diferente por serie
    fig.for_each_trace(lambda tr: tr.update(
        hovertemplate=(
            f"<b>{display_name}</b><br>"
            "Fecha: %{x|%Y-%m-%d}<br>"
            + ("Precio: %{y:.2f}<br>" if tr.name == "AdjClose" else "SMA200: %{y:.2f}<br>")
        )
    ))
    fig.update_yaxes(title_text="Precio")
    fig.update_xaxes(title_text="")
    st.plotly_chart(fig, use_container_width=True)

    # KPI del ticker
    last = s.iloc[-1]
    sma = last.get("SMA200")
    if pd.notna(sma) and sma != 0:
        pct = (last["AdjClose"] / sma - 1) * 100
        st.caption(f"Último: {last['AdjClose']:.2f} | SMA200: {sma:.2f} | % vs SMA200: {pct:.2f}%")
        
st.caption("Realizado por David Álvarez Ruiz")
