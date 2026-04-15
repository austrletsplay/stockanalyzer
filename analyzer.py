"""
analyzer.py – Datenabruf via yfinance und Berechnung aller Fundamentalkennzahlen.
"""

import yfinance as yf
import pandas as pd
import math
import time
import random
import requests
import feedparser
from datetime import datetime, timezone, timedelta


def fetch_news_and_events(company_name: str, ticker: str, calendar: dict) -> dict:
    """
    Holt Nachrichten der letzten 7 Tage + wichtige Events der nächsten 6 Monate.
    Nutzt Google News RSS via feedparser — kein API-Key nötig.
    Gibt {'news': [...], 'events': [...]} zurück.
    """
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    six_months = now + timedelta(days=180)

    # ── Nachrichten (letzte 7 Tage) ──────────────────────────────────────────
    query = f"{company_name} {ticker}".replace(" ", "+")
    rss_url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"

    news_items = []
    try:
        # feedparser sendet keinen User-Agent → Google blockiert es
        # Zuerst mit requests laden, dann mit feedparser parsen
        import io
        rss_response = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        feed = feedparser.parse(io.BytesIO(rss_response.content))
        for entry in feed.entries[:15]:
            # Datum parsen
            pub_dt = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                pub_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                pub_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

            # Nur letzte 7 Tage
            if pub_dt and pub_dt < week_ago:
                continue

            title   = getattr(entry, 'title', '').strip()
            link    = getattr(entry, 'link', '')
            source  = getattr(entry, 'source', {})
            src_name = source.get('title', '') if isinstance(source, dict) else ''
            summary = getattr(entry, 'summary', '') or ''
            # Kurze Zusammenfassung: erste 120 Zeichen des summary, HTML entfernen
            import re
            clean = re.sub(r'<[^>]+>', '', summary).strip()
            short_summary = clean[:150] + '…' if len(clean) > 150 else clean

            pub_str = pub_dt.strftime('%d.%m.%Y') if pub_dt else ''

            if title:
                news_items.append({
                    'title':   title,
                    'summary': short_summary,
                    'link':    link,
                    'source':  src_name,
                    'date':    pub_str,
                })
        # Max 8 Artikel
        news_items = news_items[:8]
    except Exception:
        pass

    # ── Events (nächste 6 Monate) ────────────────────────────────────────────
    events = []

    # 1. Earnings aus yfinance Calendar
    for key in ('Earnings Date', 'earningsDate', 'Earnings Dates'):
        val = calendar.get(key)
        if val:
            dates = val if isinstance(val, list) else [val]
            for d in dates:
                try:
                    dt = pd.to_datetime(d)
                    if pd.Timestamp.now() <= dt <= pd.Timestamp.now() + pd.Timedelta(days=180):
                        days = (dt - pd.Timestamp.now()).days
                        events.append({
                            'type':  '📅 Quartalszahlen',
                            'date':  dt.strftime('%d. %B %Y'),
                            'days':  days,
                            'note':  f'In {days} Tagen — Umsatz & Gewinn werden veröffentlicht',
                        })
                except Exception:
                    pass
            break

    # 2. Dividende
    for key in ('Dividend Date', 'dividendDate'):
        val = calendar.get(key)
        if val:
            try:
                dt = pd.to_datetime(val)
                if pd.Timestamp.now() <= dt <= pd.Timestamp.now() + pd.Timedelta(days=180):
                    days = (dt - pd.Timestamp.now()).days
                    amount = calendar.get('Dividend Amount') or calendar.get('dividendRate', '')
                    events.append({
                        'type': '💰 Dividendenzahlung',
                        'date': dt.strftime('%d. %B %Y'),
                        'days': days,
                        'note': f'In {days} Tagen' + (f' · {amount}' if amount else ''),
                    })
            except Exception:
                pass
            break

    # 3. Ex-Dividenden-Datum
    for key in ('Ex-Dividend Date', 'exDividendDate'):
        val = calendar.get(key)
        if val:
            try:
                dt = pd.to_datetime(val)
                if pd.Timestamp.now() <= dt <= pd.Timestamp.now() + pd.Timedelta(days=180):
                    days = (dt - pd.Timestamp.now()).days
                    events.append({
                        'type': '✂️ Ex-Dividenden-Datum',
                        'date': dt.strftime('%d. %B %Y'),
                        'days': days,
                        'note': f'In {days} Tagen — Aktie muss vor diesem Datum gehalten werden',
                    })
            except Exception:
                pass
            break

    # 4. Zukunfts-Events aus News erkennen (Produktlaunches, Konferenzen etc.)
    event_keywords = [
        ('launch', '🚀 Produktlaunch'),
        ('release', '🎮 Release'),
        ('conference', '🎤 Konferenz'),
        ('investor day', '📊 Investor Day'),
        ('annual meeting', '🏛️ Hauptversammlung'),
        ('fda', '🏥 FDA-Entscheidung'),
        ('acquisition', '🤝 Übernahme'),
        ('merger', '🤝 Fusion'),
        ('partnership', '🤝 Partnerschaft'),
        ('earnings', '📅 Earnings'),
    ]
    try:
        event_query = f"{company_name} {ticker} 2025 2026".replace(" ", "+")
        event_url = f"https://news.google.com/rss/search?q={event_query}&hl=en&gl=US&ceid=US:en"
        import io as _io
        event_rss = requests.get(event_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
        event_feed = feedparser.parse(_io.BytesIO(event_rss.content))
        seen_titles = set()
        for entry in event_feed.entries[:20]:
            title_lower = getattr(entry, 'title', '').lower()
            for keyword, label in event_keywords:
                if keyword in title_lower:
                    title = getattr(entry, 'title', '').strip()
                    link  = getattr(entry, 'link', '')
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        events.append({
                            'type': label,
                            'date': '',
                            'days': 999,
                            'note': title,
                            'link': link,
                        })
                    break
    except Exception:
        pass

    # Events nach Datum sortieren
    events.sort(key=lambda x: x.get('days', 999))

    return {'news': news_items, 'events': events[:8]}



PERIOD_CONFIG = {
    "1T":  {"period": "1d",  "interval": "5m"},
    "1W":  {"period": "5d",  "interval": "1h"},
    "1M":  {"period": "1mo", "interval": "1d"},
    "6M":  {"period": "6mo", "interval": "1d"},
    "1J":  {"period": "1y",  "interval": "1d"},
    "5J":  {"period": "5y",  "interval": "1wk"},
}


def fetch_price_history(ticker_symbol: str, label: str = "1M") -> pd.DataFrame | None:
    """
    Gibt historische Kursdaten als DataFrame zurück (Spalten: Datetime, Close, Open, High, Low, Volume).
    label: eines von '1T', '1W', '1M', '6M', '1J', '5J'
    """
    cfg = PERIOD_CONFIG.get(label, PERIOD_CONFIG["1M"])
    try:
        ticker = yf.Ticker(ticker_symbol.upper())
        df = ticker.history(period=cfg["period"], interval=cfg["interval"])
        if df.empty:
            return None
        df = df.reset_index()
        # Spaltenname für Datum ist je nach Interval 'Datetime' oder 'Date'
        date_col = "Datetime" if "Datetime" in df.columns else "Date"
        df = df.rename(columns={date_col: "Datetime"})
        df["Datetime"] = pd.to_datetime(df["Datetime"])
        return df[["Datetime", "Open", "High", "Low", "Close", "Volume"]]
    except Exception:
        return None


def fetch_stock_data(ticker_symbol: str) -> dict:
    """
    Ruft alle rohen yfinance-Daten für einen Ticker ab.
    Wirft ValueError bei ungültigem Ticker oder fehlenden Daten.
    Versucht bei Rate-Limiting bis zu 3 Mal mit Wartezeit.
    """
    ticker_symbol = ticker_symbol.strip().upper()

    last_error = None
    for attempt in range(4):
        try:
            ticker = yf.Ticker(ticker_symbol)
            info = ticker.info
            last_error = None
            break
        except Exception as e:
            last_error = e
            if "rate" in str(e).lower() or "429" in str(e) or "too many" in str(e).lower():
                # Exponentielles Backoff: 20s, 40s, 80s, 160s + zufällige Pause
                wait = (2 ** attempt) * 20 + random.uniform(1, 5)
                time.sleep(wait)
            else:
                break

    if last_error:
        raise ValueError(f"Netzwerkfehler beim Abruf von '{ticker_symbol}': {last_error}")

    # Validierung: yfinance gibt bei unbekannten Tickern ein leeres/minimales Dict zurück
    price_keys = ('regularMarketPrice', 'currentPrice', 'previousClose', 'open')
    if not info or not any(info.get(k) for k in price_keys):
        raise ValueError(
            f"Ticker '{ticker_symbol}' nicht gefunden oder keine Daten verfügbar. "
            "Tipp: US-Aktien ohne Suffix (AAPL), Deutsche Aktien mit .DE (SAP.DE), "
            "Japanische Aktien mit .T (7203.T)"
        )

    # Finanzdaten einzeln abrufen – ETFs/Indizes haben keine Jahresabschlüsse
    # Kleine Pausen zwischen Requests um Yahoo Finance Rate-Limiting zu vermeiden
    financials = _safe_fetch(ticker, 'financials')
    time.sleep(random.uniform(1.0, 2.0))
    balance_sheet = _safe_fetch(ticker, 'balance_sheet')
    time.sleep(random.uniform(1.0, 2.0))
    cashflow = _safe_fetch(ticker, 'cashflow')
    time.sleep(random.uniform(1.0, 2.0))

    if financials is None and info.get('totalRevenue') is None:
        raise ValueError(
            f"Keine Fundamentaldaten für '{ticker_symbol}' verfügbar. "
            "Bitte nur Aktien eingeben (keine ETFs, Indizes oder Rohstoffe)."
        )

    # Kalender (kein Fehler wenn nicht verfügbar)
    calendar = {}
    try:
        cal = ticker.calendar
        if isinstance(cal, dict):
            calendar = cal
        elif hasattr(cal, 'to_dict'):
            calendar = cal.to_dict()
    except Exception:
        pass

    # News & Events via Google News RSS + yfinance Calendar
    company_name = info.get('longName') or info.get('shortName') or ticker_symbol
    news_and_events = fetch_news_and_events(company_name, ticker_symbol, calendar)

    return {
        'ticker_symbol': ticker_symbol,
        'info': info,
        'financials': financials,
        'balance_sheet': balance_sheet,
        'cashflow': cashflow,
        'news': news_and_events.get('news', []),
        'events': news_and_events.get('events', []),
        'calendar': calendar,
    }


def calculate_metrics(raw_data: dict) -> dict:
    """
    Berechnet alle Fundamentalkennzahlen aus den rohen yfinance-Daten.
    Fehlende Werte werden als None zurückgegeben (nie crashen).
    """
    info = raw_data['info']
    fin = raw_data['financials']
    bs = raw_data['balance_sheet']
    cf = raw_data['cashflow']

    company = _calc_company(info, raw_data['ticker_symbol'])
    valuation = _calc_valuation(info)
    growth = _calc_growth(info, fin)
    profitability = _calc_profitability(info, fin, cf)
    balance_sheet = _calc_balance_sheet(info, bs, cf)

    # P/FCF nachberechnen (braucht market_cap + FCF)
    market_cap = _safe_get(info, 'marketCap')
    fcf = balance_sheet.get('free_cash_flow')
    if market_cap and fcf and fcf > 0:
        valuation['p_fcf'] = round(market_cap / fcf, 2)
    else:
        valuation['p_fcf'] = None

    # PEG manuell berechnen falls nicht vorhanden
    if valuation['peg'] is None:
        pe = valuation.get('forward_pe') or valuation.get('pe')
        eps_cagr = growth.get('eps_cagr_3yr')
        if pe and eps_cagr and eps_cagr > 0:
            valuation['peg'] = round(pe / (eps_cagr * 100), 2)

    historical_table = _build_historical_table(fin, bs, cf, info)

    return {
        'company': company,
        'valuation': valuation,
        'growth': growth,
        'profitability': profitability,
        'balance_sheet': balance_sheet,
        'historical_table': historical_table,
        'news': raw_data.get('news', []),
        'events': raw_data.get('events', []),
        'calendar': raw_data.get('calendar', {}),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Interne Berechnungsfunktionen
# ──────────────────────────────────────────────────────────────────────────────

def _build_historical_table(fin, bs, cf, info) -> dict:
    """
    Erstellt eine Jahrestabelle mit allen wichtigen Kennzahlen (bis 5 Jahre).
    Gibt dict zurück: { 'years': [...], 'rows': [{'label': ..., 'values': [...], 'format': ...}] }
    """
    if fin is None or fin.empty:
        return {'years': [], 'rows': []}

    # Jahresspalten: ältestes zuerst, max. 5 Jahre
    cols = sorted(fin.columns)[-5:]
    years = [str(c.year) for c in cols]
    shares = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding') or 1

    def row_vals(df, keys):
        """Holt Zeilenwerte aus DataFrame, gibt Liste mit None für fehlende Jahre."""
        series = None
        if df is not None and not df.empty:
            for k in keys:
                if k in df.index:
                    series = df.loc[k]
                    break
        if series is None:
            return [None] * len(cols)
        return [series.get(c) if _is_valid(series.get(c, None)) else None for c in cols]

    def margin_vals(numerator_vals, revenue_vals):
        result = []
        for n, r in zip(numerator_vals, revenue_vals):
            if n is not None and r and r != 0:
                result.append(n / r)
            else:
                result.append(None)
        return result

    revenue   = row_vals(fin, ['Total Revenue', 'TotalRevenue'])
    gross     = row_vals(fin, ['Gross Profit', 'GrossProfit'])
    ebit      = row_vals(fin, ['Operating Income', 'Ebit', 'EBIT'])
    net_inc   = row_vals(fin, ['Net Income', 'NetIncome'])
    ocf       = row_vals(cf,  ['Operating Cash Flow', 'Total Cash From Operating Activities']) if cf is not None else [None]*len(cols)
    capex_raw = row_vals(cf,  ['Capital Expenditures', 'Purchase Of Property Plant And Equipment']) if cf is not None else [None]*len(cols)
    fcf       = [
        (o + c) if o is not None and c is not None else (o if o is not None else None)
        for o, c in zip(ocf, capex_raw)
    ]
    total_debt = row_vals(bs, ['Total Debt', 'Long Term Debt']) if bs is not None else [None]*len(cols)
    cash       = row_vals(bs, ['Cash And Cash Equivalents', 'Cash Cash Equivalents And Short Term Investments']) if bs is not None else [None]*len(cols)
    equity     = row_vals(bs, ['Total Stockholder Equity', 'Stockholders Equity']) if bs is not None else [None]*len(cols)

    eps = [ni / shares if ni is not None else None for ni in net_inc]

    rows = [
        {'label': 'Umsatz',           'values': revenue,                          'format': 'big'},
        {'label': 'Bruttogewinn',      'values': gross,                            'format': 'big'},
        {'label': 'EBIT',              'values': ebit,                             'format': 'big'},
        {'label': 'Nettogewinn',       'values': net_inc,                          'format': 'big'},
        {'label': 'EPS (Gew. je Akt.)','values': eps,                             'format': 'eps'},
        {'label': 'Free Cash Flow',    'values': fcf,                              'format': 'big'},
        {'label': 'Bruttomarge',       'values': margin_vals(gross, revenue),      'format': 'pct'},
        {'label': 'EBIT-Marge',        'values': margin_vals(ebit, revenue),       'format': 'pct'},
        {'label': 'Nettomarge',        'values': margin_vals(net_inc, revenue),    'format': 'pct'},
        {'label': 'Gesamtschulden',    'values': total_debt,                       'format': 'big'},
        {'label': 'Kassenbestand',     'values': cash,                             'format': 'big'},
        {'label': 'Eigenkapital',      'values': equity,                           'format': 'big'},
    ]

    return {'years': years, 'rows': rows}

def _calc_company(info: dict, ticker: str) -> dict:
    market_cap = _safe_get(info, 'marketCap')
    return {
        'ticker': ticker,
        'name': _safe_get(info, 'longName') or _safe_get(info, 'shortName') or ticker,
        'sector': _safe_get(info, 'sector', 'N/A'),
        'industry': _safe_get(info, 'industry', 'N/A'),
        'country': _safe_get(info, 'country', 'N/A'),
        'currency': _safe_get(info, 'currency', 'USD'),
        'market_cap': market_cap,
        'market_cap_fmt': _fmt_large_number(market_cap),
        'description': _safe_get(info, 'longBusinessSummary', ''),
        'website': _safe_get(info, 'website', ''),
        'employees': _safe_get(info, 'fullTimeEmployees'),
        'current_price': _safe_get(info, 'currentPrice') or _safe_get(info, 'regularMarketPrice'),
        'analyst_recommendation': _safe_get(info, 'recommendationKey', ''),
    }


def _calc_valuation(info: dict) -> dict:
    return {
        'pe': _safe_get(info, 'trailingPE'),
        'forward_pe': _safe_get(info, 'forwardPE'),
        'pb': _safe_get(info, 'priceToBook'),
        'ps': _safe_get(info, 'priceToSalesTrailingTwelveMonths'),
        'peg': _safe_get(info, 'pegRatio'),
        'ev_ebitda': _safe_get(info, 'enterpriseToEbitda'),
        'p_fcf': None,  # wird nachberechnet
    }


def _calc_growth(info: dict, fin: pd.DataFrame | None) -> dict:
    result = {
        'revenue_cagr_3yr': None,
        'eps_cagr_3yr': None,
        'eps_consistency': None,
        'revenue_yoy': _safe_get(info, 'revenueGrowth'),
        'earnings_yoy': _safe_get(info, 'earningsGrowth'),
        'revenue_history': [],
        'eps_history': [],
        'revenue_years': [],
    }

    if fin is not None and not fin.empty:
        # Umsatz-Historie (ältestes Jahr zuerst)
        rev_series = _get_fin_row(fin, ['Total Revenue', 'TotalRevenue'])
        if rev_series is not None:
            rev_sorted = rev_series.sort_index()  # ältestes Datum zuerst
            result['revenue_history'] = [v for v in rev_sorted.values if _is_valid(v)]
            result['revenue_years'] = [str(d.year) for d in rev_sorted.index]
            if len(result['revenue_history']) >= 2:
                result['revenue_cagr_3yr'] = _compute_cagr(result['revenue_history'])

        # EPS / Net Income für CAGR
        ni_series = _get_fin_row(fin, ['Net Income', 'NetIncome'])
        shares = _safe_get(info, 'sharesOutstanding') or _safe_get(info, 'impliedSharesOutstanding')
        if ni_series is not None and shares and shares > 0:
            ni_sorted = ni_series.sort_index()
            eps_vals = [v / shares for v in ni_sorted.values if _is_valid(v)]
            result['eps_history'] = [round(e, 4) for e in eps_vals]
            if len(eps_vals) >= 2:
                result['eps_cagr_3yr'] = _compute_cagr(eps_vals)
                result['eps_consistency'] = _compute_consistency(eps_vals)

    # Fallback für EPS-Konsistenz aus info (wenn nur 1 Jahr Daten)
    if result['eps_consistency'] is None and result['earnings_yoy'] is not None:
        result['eps_consistency'] = 1 if result['earnings_yoy'] > 0 else 0

    return result


def _calc_profitability(info: dict, fin: pd.DataFrame | None, cf: pd.DataFrame | None) -> dict:
    roe = _safe_get(info, 'returnOnEquity')
    net_margin = _safe_get(info, 'profitMargins')
    total_revenue = _safe_get(info, 'totalRevenue')

    # FCF Margin
    fcf_margin = None
    fcf_ttm = _safe_get(info, 'freeCashflow')
    if fcf_ttm and total_revenue and total_revenue > 0:
        fcf_margin = fcf_ttm / total_revenue

    return {
        'roe': roe,
        'roa': _safe_get(info, 'returnOnAssets'),
        'gross_margin': _safe_get(info, 'grossMargins'),
        'operating_margin': _safe_get(info, 'operatingMargins'),
        'net_margin': net_margin,
        'ebitda_margin': _safe_get(info, 'ebitdaMargins'),
        'fcf_margin': fcf_margin,
    }


def _calc_balance_sheet(info: dict, bs: pd.DataFrame | None, cf: pd.DataFrame | None) -> dict:
    de_raw = _safe_get(info, 'debtToEquity')
    # yfinance liefert D/E manchmal als Prozent (150 = 1.5x)
    debt_to_equity = de_raw / 100 if de_raw and de_raw > 10 else de_raw

    result = {
        'debt_to_equity': debt_to_equity,
        'current_ratio': _safe_get(info, 'currentRatio'),
        'quick_ratio': _safe_get(info, 'quickRatio'),
        'total_cash': _safe_get(info, 'totalCash'),
        'total_debt': _safe_get(info, 'totalDebt'),
        'free_cash_flow': _safe_get(info, 'freeCashflow'),
        'fcf_history': [],
        'fcf_years': [],
    }

    # FCF-Historie aus Cashflow-DataFrame
    if cf is not None and not cf.empty:
        fcf_series = _get_fin_row(cf, ['Free Cash Flow', 'FreeCashFlow'])
        if fcf_series is None:
            # Manuell berechnen: OCF - Capex
            ocf = _get_fin_row(cf, ['Operating Cash Flow', 'Cash Flow From Operations', 'Total Cash From Operating Activities'])
            capex = _get_fin_row(cf, ['Capital Expenditures', 'Purchase Of Property Plant And Equipment'])
            if ocf is not None and capex is not None:
                fcf_series = ocf + capex  # Capex ist meist negativ in yfinance

        if fcf_series is not None:
            fcf_sorted = fcf_series.sort_index()
            result['fcf_history'] = [v for v in fcf_sorted.values if _is_valid(v)]
            result['fcf_years'] = [str(d.year) for d in fcf_sorted.index]

        # Net Debt
        if result['total_debt'] and result['total_cash']:
            result['net_debt'] = result['total_debt'] - result['total_cash']
        else:
            result['net_debt'] = None

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Hilfsfunktionen
# ──────────────────────────────────────────────────────────────────────────────

def _safe_fetch(ticker, attribute: str):
    """Ruft ein yfinance-Attribut ab, gibt None zurück bei Fehler oder leerem DataFrame."""
    try:
        data = getattr(ticker, attribute)
        if isinstance(data, pd.DataFrame) and data.empty:
            return None
        return data
    except Exception:
        return None


def _safe_get(d: dict, key: str, default=None):
    """Gibt d[key] zurück wenn vorhanden und nicht NaN/None, sonst default."""
    val = d.get(key, default)
    if val is None:
        return default
    try:
        if math.isnan(float(val)):
            return default
    except (TypeError, ValueError):
        pass
    return val


def _get_fin_row(df: pd.DataFrame, possible_keys: list) -> pd.Series | None:
    """Sucht eine Zeile im DataFrame nach mehreren möglichen Zeilennamen."""
    for key in possible_keys:
        if key in df.index:
            row = df.loc[key]
            # Nur gültige numerische Werte behalten
            valid = row.dropna()
            if len(valid) > 0:
                return valid
    return None


def _is_valid(val) -> bool:
    """Prüft ob ein Wert gültig (nicht None, nicht NaN, numerisch) ist."""
    if val is None:
        return False
    try:
        return not math.isnan(float(val))
    except (TypeError, ValueError):
        return False


def _compute_cagr(values: list) -> float | None:
    """
    Berechnet den CAGR über eine Liste von Jahreswerten (ältestes zuerst).
    Gibt None zurück wenn die Berechnung nicht möglich ist.
    """
    if len(values) < 2:
        return None
    start = values[0]
    end = values[-1]
    years = len(values) - 1
    if start <= 0 or end <= 0:
        # Bei negativen Werten: einfaches durchschnittliches Wachstum
        if start < 0 and end > 0:
            return None  # Turnaround, schwer zu berechnen
        return None
    try:
        return round((end / start) ** (1 / years) - 1, 4)
    except (ZeroDivisionError, ValueError):
        return None


def _compute_consistency(values: list) -> float:
    """
    Gibt den Anteil der Perioden mit positivem YoY-Wachstum zurück (0.0 bis 1.0).
    """
    if len(values) < 2:
        return 0.0
    positive = sum(1 for i in range(1, len(values)) if values[i] > values[i - 1])
    return round(positive / (len(values) - 1), 2)


def _fmt_large_number(value) -> str:
    """Formatiert große Zahlen als lesbare Strings (z.B. 2.8T, 450B, 12M)."""
    if value is None:
        return 'N/A'
    try:
        v = float(value)
        if v >= 1e12:
            return f"{v/1e12:.1f}T"
        elif v >= 1e9:
            return f"{v/1e9:.1f}B"
        elif v >= 1e6:
            return f"{v/1e6:.1f}M"
        else:
            return f"{v:,.0f}"
    except (TypeError, ValueError):
        return 'N/A'
