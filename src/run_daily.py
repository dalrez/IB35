import os
import pandas as pd
import yfinance as yf
from datetime import datetime

# Lista inicial (simplificada). Luego la automatizamos con la lista real del IBEX.
# Estos tickers son ejemplos en Yahoo Finance para España (suelen acabar en .MC).
TICKERS = [
    "SAN.MC", "BBVA.MC", "ITX.MC", "IBE.MC", "TEF.MC"
]

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
    raw = download_prices(TICKERS)
    px = to_long_format(raw)
    under = compute_under_sma200(px)
    os.makedirs("data",exist_ok=True)

    # Guardamos CSV para que el dashboard lo lea
    under.to_csv("data/under_sma200.csv", index=False)

    # También guardamos un resumen para ver rápido en logs
    if under.empty:
        print("Hoy NO hay empresas bajo SMA200 (en la lista de ejemplo).")
    else:
        print("Empresas bajo SMA200:")
        print(under.to_string(index=False))

if __name__ == "__main__":
    main()
