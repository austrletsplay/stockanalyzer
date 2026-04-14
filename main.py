"""
main.py – FastAPI Backend für den Stock Analyzer.

Was ist FastAPI?
  FastAPI ist eine Library die deinen Python-Code als Web-API verfügbar macht.
  Das bedeutet: das React-Frontend kann über HTTP-Requests Daten von hier abrufen.
  Statt einer Streamlit-Seite gibt es hier nur Datenpunkte (JSON).

Was ist JSON?
  JSON ist ein Datenformat – ähnlich wie ein Python-Dictionary, nur als Text.
  Das Frontend liest JSON und baut daraus die Benutzeroberfläche.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from analyzer import fetch_stock_data, calculate_metrics, fetch_price_history, PERIOD_CONFIG
from scorer import calculate_score
from excel_export import generate_excel

# ── App erstellen ──────────────────────────────────────────────────────────────
# FastAPI() erstellt die Web-API. Der title und description erscheinen in der
# automatischen Dokumentation unter http://localhost:8000/docs
app = FastAPI(
    title="Stock Analyzer API",
    description="Quality-Growth Fundamentalanalyse API",
    version="1.0.0",
)

# ── CORS erlauben ──────────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# Das Frontend läuft auf Port 3000, das Backend auf Port 8000.
# Ohne CORS würde der Browser die Verbindung aus Sicherheitsgründen blockieren.
# allow_origins=["*"] bedeutet: alle URLs dürfen die API aufrufen.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Endpunkt 1: Aktienanalyse ──────────────────────────────────────────────────
# Was ist ein Endpunkt?
#   Eine URL die das Frontend aufrufen kann. Wenn das Frontend
#   GET /api/analyze/AAPL aufruft, führt Python diese Funktion aus
#   und gibt das Ergebnis als JSON zurück.
#
# {ticker} ist ein Platzhalter – der echte Ticker (z.B. "AAPL") wird
# beim Aufruf eingefügt und als Parameter übergeben.
@app.get("/api/analyze/{ticker}")
def analyze(ticker: str):
    """
    Gibt die vollständige Fundamentalanalyse für einen Ticker zurück.
    Beispiel-Aufruf: GET /api/analyze/AAPL
    """
    try:
        # Daten von Yahoo Finance holen (dein bestehender Code)
        raw = fetch_stock_data(ticker)

        # Kennzahlen berechnen (dein bestehender Code)
        metrics = calculate_metrics(raw)

        # Score berechnen (dein bestehender Code)
        score = calculate_score(metrics)

        # Alles zusammenpacken und zurückgeben
        # Das Frontend empfängt dieses Dictionary als JSON
        return {
            "company":          metrics["company"],
            "score":            score,
            "growth":           metrics["growth"],
            "profitability":    metrics["profitability"],
            "balance_sheet":    metrics["balance_sheet"],
            "valuation":        metrics["valuation"],
            "historical_table": metrics["historical_table"],
            "news":             metrics["news"],
            "events":           metrics["events"],
        }

    except ValueError as e:
        # ValueError = ungültiger Ticker oder keine Daten verfügbar
        # HTTPException mit status_code=404 bedeutet: "Nicht gefunden"
        # Das Frontend kann diesen Fehler abfangen und dem User zeigen
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        # Unerwarteter Fehler (z.B. Netzwerkproblem)
        # status_code=500 bedeutet: "Server-Fehler"
        raise HTTPException(status_code=500, detail=f"Interner Fehler: {str(e)}")


# ── Endpunkt 2: Kursdaten ──────────────────────────────────────────────────────
# Dieser Endpunkt liefert die Kursdaten für den Preischart.
# ?period=1M ist ein Query-Parameter – optional, Standard ist "1M"
# Beispiel-Aufruf: GET /api/price/AAPL?period=6M
@app.get("/api/price/{ticker}")
def price(ticker: str, period: str = "1M"):
    """
    Gibt historische Kursdaten für einen Ticker zurück.
    period: 1T, 1W, 1M, 6M, 1J, 5J
    """
    # Prüfen ob der angegebene Zeitraum gültig ist
    if period not in PERIOD_CONFIG:
        raise HTTPException(
            status_code=400,
            detail=f"Ungültiger Zeitraum '{period}'. Gültig: {list(PERIOD_CONFIG.keys())}"
        )

    df = fetch_price_history(ticker.upper(), period)

    if df is None or df.empty:
        raise HTTPException(
            status_code=404,
            detail=f"Keine Kursdaten für '{ticker}' verfügbar."
        )

    # DataFrame zu einer Liste von Dictionaries konvertieren
    # (DataFrames kann JSON nicht direkt lesen, aber Listen schon)
    records = []
    for _, row in df.iterrows():
        records.append({
            "date":   row["Datetime"].isoformat(),  # Datum als Text (ISO-Format)
            "open":   round(float(row["Open"]),  4),
            "high":   round(float(row["High"]),  4),
            "low":    round(float(row["Low"]),   4),
            "close":  round(float(row["Close"]), 4),
            "volume": int(row["Volume"]),
        })

    return {
        "ticker": ticker.upper(),
        "period": period,
        "data":   records,
    }


# ── Endpunkt 3: Excel Export ──────────────────────────────────────────────────
# Gibt eine fertige Excel-Datei zurück die der Browser direkt herunterlädt.
# Beispiel-Aufruf: GET /api/export/AAPL
@app.get("/api/export/{ticker}")
def export(ticker: str):
    """
    Erstellt eine formatierte Excel-Datei mit der vollständigen Fundamentalanalyse.
    """
    try:
        raw = fetch_stock_data(ticker)
        metrics = calculate_metrics(raw)
        scores = calculate_score(metrics)
        excel_bytes = generate_excel(metrics, scores, ticker.upper())

        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=Vestly_{ticker.upper()}_Analyse.xlsx"},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export fehlgeschlagen: {str(e)}")


# ── Endpunkt 4: Health Check ───────────────────────────────────────────────────
# Ein einfacher Endpunkt um zu prüfen ob das Backend läuft.
# Das Frontend kann diesen aufrufen beim Start.
@app.get("/api/health")
def health():
    return {"status": "ok"}
