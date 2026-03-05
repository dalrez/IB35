import pandas as pd
import requests
from io import StringIO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}

def fetch_tables(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return pd.read_html(StringIO(r.text))

def extract_tickers(tables, keywords=("ticker", "símbolo", "simbolo", "symbol"), suffix=""):
    for t in tables:
        cols = [str(c).strip() for c in t.columns]
        cols_l = [c.lower() for c in cols]

        ticker_col = None
        for i, c in enumerate(cols_l):
            if any(k in c for k in keywords):
                ticker_col = cols[i]
                break
        if ticker_col is None:
            continue

        tickers = (
            t[ticker_col]
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", "", regex=True)
            .str.upper()
        )
        tickers = [x for x in tickers.tolist() if x and x != "NAN"]

        # Aplicar sufijo si hace falta (IBEX -> .MC; Nasdaq -> "")
        if suffix:
            tickers = [x if x.endswith(suffix) else f"{x}{suffix}" for x in tickers]

        # quitar duplicados manteniendo orden
        seen = set()
        out = []
        for x in tickers:
            if x not in seen:
                seen.add(x)
                out.append(x)

        if len(out) >= 20:
            return out

    raise RuntimeError("No encontré una tabla válida con tickers.")

def update_ibex():
    urls = ["https://es.wikipedia.org/wiki/IBEX_35", "https://en.wikipedia.org/wiki/IBEX_35"]
    last_err = None
    for url in urls:
        try:
            tables = fetch_tables(url)
            tickers = extract_tickers(tables, suffix=".MC")
            pd.DataFrame({"Ticker": tickers}).to_csv("data/tickers.csv", index=False)
            print(f"OK IBEX: {len(tickers)} tickers desde {url}")
            return
        except Exception as e:
            last_err = e
    raise RuntimeError(f"IBEX: no pude actualizar tickers. Último error: {last_err}")

def update_nasdaq100():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = fetch_tables(url)
    tickers = extract_tickers(tables, suffix="")  # Nasdaq no lleva .MC
    pd.DataFrame({"Ticker": tickers}).to_csv("data/tickers_nasdaq100.csv", index=False)
    print(f"OK Nasdaq-100: {len(tickers)} tickers desde {url}")

def main():
    update_ibex()
    update_nasdaq100()

if __name__ == "__main__":
    main()
