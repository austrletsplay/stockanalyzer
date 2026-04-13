"""
analyzer.py – Datenabruf via yfinance und Berechnung aller Fundamentalkennzahlen.
"""

import yfinance as yf
import pandas as pd
import math


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
    """
    ticker_symbol = ticker_symbol.strip().upper()

    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
    except Exception as e:
        raise ValueError(f"Netzwerkfehler beim Abruf von '{ticker_symbol}': {e}")

    # Validierung: yfinance gibt bei unbekannten Tickern ein leeres/minimales Dict zurück
    price_keys = ('regularMarketPrice', 'currentPrice', 'previousClose', 'open')
    if not info or not any(info.get(k) for k in price_keys):
        raise ValueError(
            f"Ticker '{ticker_symbol}' nicht gefunden oder keine Daten verfügbar. "
            "Tipp: US-Aktien ohne Suffix (AAPL), Deutsche Aktien mit .DE (SAP.DE), "
            "Japanische Aktien mit .T (7203.T)"
        )

    # Finanzdaten einzeln abrufen – ETFs/Indizes haben keine Jahresabschlüsse
    financials = _safe_fetch(ticker, 'financials')
    balance_sheet = _safe_fetch(ticker, 'balance_sheet')
    cashflow = _safe_fetch(ticker, 'cashflow')

    if financials is None and info.get('totalRevenue') is None:
        raise ValueError(
            f"Keine Fundamentaldaten für '{ticker_symbol}' verfügbar. "
            "Bitte nur Aktien eingeben (keine ETFs, Indizes oder Rohstoffe)."
        )

    return {
        'ticker_symbol': ticker_symbol,
        'info': info,
        'financials': financials,
        'balance_sheet': balance_sheet,
        'cashflow': cashflow,
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

    return {
        'company': company,
        'valuation': valuation,
        'growth': growth,
        'profitability': profitability,
        'balance_sheet': balance_sheet,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Interne Berechnungsfunktionen
# ──────────────────────────────────────────────────────────────────────────────

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
