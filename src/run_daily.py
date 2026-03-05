import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.notify_whatsapp import send_whatsapp

UNIVERSES = {
    "IBEX35": "data/tickers.csv",
    "NASDAQ100": "data/tickers_nasdaq100.csv",
    "INDICES": "data/tickers_indices.csv",
}

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

def compute_under_sma200(px):
    px = px.sort_values(["Ticker", "Date"])
    px["SMA200"] = px.groupby("Ticker")["AdjClose"].transform(lambda s: s.rolling(200).mean())

    last = px.groupby("Ticker").tail(1).copy()
    last["BelowSMA200"] = last["AdjClose"] < last["SMA200"]
    last["PctBelow"] = (last["AdjClose"] / last["SMA200"] - 1.0) * 100

    under = last[last["BelowSMA200"]].copy()
    under = under.sort_values("PctBelow")  # más negativo = más por debajo

    # Output amigable
    under["RunDate"] = datetime.utcnow().strftime("%Y-%m-%d")
    return under[["RunDate", "Ticker", "AdjClose", "SMA200", "PctBelow"]]

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

        lines = ["📉 Señal SMA200 (todos los universos)"]
        lines.append("Resumen por universo:")
        for uni, n in counts.items():
            lines.append(f"- {uni}: {n}")

        # Top global (más por debajo)
        top = combined.sort_values("PctBelow").head(10)
        lines.append("")
        lines.append("Top 10 global (% bajo SMA200):")
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
