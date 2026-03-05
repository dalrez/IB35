import os
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.notify_whatsapp import send_whatsapp

UNIVERSES = {
    "IBEX35": "data/tickers.csv",
    "NASDAQ100": "data/tickers_nasdaq100.csv",
    "INDICES": "data/tickers_indices.csv",
}
THRESHOLD_PCT = 5.0  # mostrar solo si está 5% o más por debajo de la SMA200

def load_tickers(path="data/tickers.csv"):
    df = pd.read_csv(path)
    tickers = df["Ticker"].dropna().astype(str).str.strip()
    # Quitar líneas vacías
    tickers = [t for t in tickers if t]
    return tickers

def download_prices(tickers):
    # Bajamos ~400 días para tener margen de 200 sesiones
    df = yf.download(
        tickers=tickers,
        period="400d",
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        threads=True,
        progress=False,
    )
    return df

def to_long_format(df):
    # Convierte el formato de yfinance a una tabla: Date, Ticker, Adj Close
    rows = []
    for ticker in df.columns.levels[0]:
        sub = df[ticker].copy()
        sub = sub.reset_index()
        sub["Ticker"] = ticker
        # Preferimos Adj Close si existe
        col = "Adj Close" if "Adj Close" in sub.columns else "Close"
        sub = sub[["Date", "Ticker", col]].rename(columns={col: "AdjClose"})
        rows.append(sub)
    out = pd.concat(rows, ignore_index=True)
    out = out.dropna()
    return out

def compute_under_sma200(px: pd.DataFrame) -> pd.DataFrame:
    # Espera columnas: Date, Ticker, AdjClose
    px = px.sort_values(["Ticker", "Date"]).copy()

    g = px.groupby("Ticker", group_keys=False)

    # Retorno diario
    px["Ret"] = g["AdjClose"].pct_change()

    # SMA200
    px["SMA200"] = g["AdjClose"].transform(lambda s: s.rolling(200).mean())

    # Retornos recientes
    px["Return_5d"] = g["AdjClose"].pct_change(5)
    px["Return_21d"] = g["AdjClose"].pct_change(21)
    px["Return_63d"] = g["AdjClose"].pct_change(63)

    # Volatilidad 20d (anualizada)
    px["Vol_20d"] = g["Ret"].transform(lambda s: s.rolling(20).std() * np.sqrt(252))

    # 52 semanas ~ 252 sesiones
    px["52wHigh"] = g["AdjClose"].transform(lambda s: s.rolling(252).max())
    px["52wLow"] = g["AdjClose"].transform(lambda s: s.rolling(252).min())

    px["PctFrom52wHigh"] = (px["AdjClose"] / px["52wHigh"] - 1.0) * 100
    px["PctFrom52wLow"] = (px["AdjClose"] / px["52wLow"] - 1.0) * 100

    # Pendiente SMA200: % cambio en 20 sesiones
    px["SMA200_Slope_20d"] = g["SMA200"].transform(lambda s: s.pct_change(20) * 100)

    # Último registro por ticker
    last = g.tail(1).copy()

    # Delta / % bajo SMA200
    last["DeltaToSMA200"] = last["AdjClose"] - last["SMA200"]
    last["PctBelow"] = (last["AdjClose"] / last["SMA200"] - 1.0) * 100
    last = last.dropna(subset=["SMA200", "PctBelow"]).copy()
    last["BelowThreshold"] = last["PctBelow"] < THRESHOLD_PCT


    # WeeklyMean: media semanal reciente (sobre últimas 200 sesiones)
    last200 = g.tail(200).copy()
    last200 = last200.set_index("Date")
    weekly = (
        last200.groupby("Ticker")["AdjClose"]
        .resample("W-FRI")
        .mean()
        .rename("WeeklyMean")
        .reset_index()
    )
    weekly_last = weekly.groupby("Ticker").tail(1)[["Ticker", "WeeklyMean"]]
    last = last.merge(weekly_last, on="Ticker", how="left")

    # Nos quedamos solo con los que están bajo SMA200
    under = last[last["BelowThreshold"]].copy()
    under = under.sort_values("PctBelow")  # más negativo primero

    # Columnas finales (ordenadas)
    cols = [
        "Ticker", "AdjClose", "SMA200", "DeltaToSMA200", "PctBelow",
        "WeeklyMean",
        "Return_5d", "Return_21d", "Return_63d",
        "Vol_20d",
        "52wHigh", "52wLow", "PctFrom52wHigh", "PctFrom52wLow",
        "SMA200_Slope_20d",
    ]
    # Algunas pueden no existir si algo cambia; por seguridad:
    cols = [c for c in cols if c in under.columns]
    return under[cols]

def main():
    os.makedirs("data", exist_ok=True)

    all_under = []

    for name, path in UNIVERSES.items():
        tickers = load_tickers(path)
        raw = download_prices(tickers)
        px = to_long_format(raw)
        under = compute_under_sma200(px)

        under["Universe"] = name
        under.to_csv(f"data/under_sma200_{name}.csv", index=False)
        all_under.append(under)

        print(f"{name}: {len(under)} empresas bajo SMA200")

    combined = pd.concat(all_under, ignore_index=True) if all_under else pd.DataFrame()
    combined.to_csv("data/under_sma200_all.csv", index=False)

    # WhatsApp: resumen combinado
        
    if combined.empty:
        msg = "Universos: hoy no hay tickers bajo SMA200."
    else:
        # Conteo por universo
        counts = combined.groupby("Universe")["Ticker"].count().sort_values(ascending=False)

        lines = ["📉 Señal SMA200 (≤ {THRESHOLD_PCT:.0f}%) — resumen por universo:"]
        lines.append("Resumen: https://ib35insights.streamlit.app/#ibex-35-empresas-bajo-sma-200")
        for uni, n in counts.items():
            lines.append(f"- {uni}: {n}")

        # Top global (más por debajo)
        top = combined.sort_values("PctBelow").head(10)
        lines.append("")
        lines.append("Top 10 global:")
        for _, r in top.iterrows():
            lines.append(f"- {r['Universe']} {r['Ticker']}: {r['PctBelow']:.2f}%")

        msg = "\n".join(lines)

    try:
        send_whatsapp(msg)
        print("WhatsApp enviado.")
    except Exception as e:
        print("⚠️ No se pudo enviar WhatsApp, pero el proceso continúa.")
        print(f"Detalle del error: {e}")
   

if __name__ == "__main__":
    main()
