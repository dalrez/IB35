import os
import time
import pandas as pd
import yfinance as yf

CACHE_PATH = "data/names_cache.csv"

def load_cache() -> pd.DataFrame:
    if os.path.exists(CACHE_PATH):
        df = pd.read_csv(CACHE_PATH)
        if "Ticker" not in df.columns:
            return pd.DataFrame(columns=["Ticker", "Name"])
        if "Name" not in df.columns:
            df["Name"] = ""
        df["Ticker"] = df["Ticker"].astype(str).str.strip().str.upper()
        df["Name"] = df["Name"].astype(str).fillna("").str.strip()
        return df[["Ticker", "Name"]].drop_duplicates(subset=["Ticker"], keep="first")
    return pd.DataFrame(columns=["Ticker", "Name"])

def read_all_tickers() -> list[str]:
    files = [
        "data/tickers.csv",              # IBEX empresas
        "data/tickers_nasdaq100.csv",    # Nasdaq100 empresas (si existe)
        "data/tickers_indices.csv",      # Índices (Name manual, pero también cacheamos si se puede)
    ]
    tickers = []
    for f in files:
        if os.path.exists(f):
            df = pd.read_csv(f)
            if "Ticker" in df.columns:
                tickers += df["Ticker"].astype(str).tolist()
    tickers = [t.strip().upper() for t in tickers if isinstance(t, str) and t.strip()]
    return sorted(set(tickers))

def fetch_name_yf(ticker: str) -> str:
    # yfinance a veces falla; intentamos get_info y varias claves
    t = yf.Ticker(ticker)
    info = {}
    try:
        info = t.get_info()
    except Exception:
        return ""

    for k in ("longName", "shortName", "name"):
        v = info.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def main():
    os.makedirs("data", exist_ok=True)

    tickers = read_all_tickers()
    cache = load_cache()
    cache_map = dict(zip(cache["Ticker"], cache["Name"]))

    # Solo buscamos los que no tengan nombre en cache
    missing = [t for t in tickers if not cache_map.get(t, "").strip()]
    print(f"Tickers totales: {len(tickers)} | sin nombre en cache: {len(missing)}")

    updates = 0
    for i, tkr in enumerate(missing, 1):
        name = ""
        try:
            name = fetch_name_yf(tkr)
        except Exception as e:
            print(f"Fallo {tkr}: {e}")

        if name:
            cache_map[tkr] = name
            updates += 1

        # Pausas suaves para evitar rate-limit
        if i % 15 == 0:
            time.sleep(2)

    out = pd.DataFrame({"Ticker": list(cache_map.keys()), "Name": list(cache_map.values())})
    out = out.sort_values("Ticker")
    out.to_csv(CACHE_PATH, index=False)

    print(f"Cache guardada: {CACHE_PATH} | updates nuevos: {updates} | total cache: {len(out)}")

if __name__ == "__main__":
    main()
