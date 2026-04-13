"""
scorer.py – Quality-Growth-Scoring nach Fisher/Buffett-Stil (0-100 Punkte).
"""


def calculate_score(metrics: dict) -> dict:
    """
    Berechnet den Gesamtscore und die Kaufempfehlung.
    Eingabe: Ausgabe von analyzer.calculate_metrics()
    """
    growth = metrics['growth']
    profitability = metrics['profitability']
    balance_sheet = metrics['balance_sheet']
    valuation = metrics['valuation']
    company = metrics['company']

    is_financial_sector = (company.get('sector', '') or '').lower() in (
        'financial services', 'banks', 'insurance', 'financial'
    )

    g_score, g_breakdown = _score_growth(growth)
    p_score, p_breakdown = _score_profitability(profitability, balance_sheet)
    b_score, b_breakdown = _score_balance_sheet(balance_sheet, is_financial_sector)
    v_score, v_breakdown = _score_valuation(valuation, growth)

    total = g_score + p_score + b_score + v_score
    recommendation, color = _get_recommendation(total)

    strengths = _get_strengths(metrics)
    concerns = _get_concerns(metrics)
    warnings = _get_data_warnings(metrics)

    return {
        'total_score': total,
        'recommendation': recommendation,
        'recommendation_color': color,
        'category_scores': {
            'growth': {'score': g_score, 'max': 30, 'breakdown': g_breakdown},
            'profitability': {'score': p_score, 'max': 30, 'breakdown': p_breakdown},
            'balance_sheet': {'score': b_score, 'max': 20, 'breakdown': b_breakdown},
            'valuation': {'score': v_score, 'max': 20, 'breakdown': v_breakdown},
        },
        'strengths': strengths,
        'concerns': concerns,
        'data_warnings': warnings,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Kategorie-Scoring
# ──────────────────────────────────────────────────────────────────────────────

def _score_growth(growth: dict) -> tuple[int, dict]:
    """Wachstum: max. 30 Punkte"""
    breakdown = {}

    # Revenue CAGR 3yr (15 Punkte)
    rev_cagr = growth.get('revenue_cagr_3yr')
    if rev_cagr is None:
        # Fallback auf YoY
        rev_cagr = growth.get('revenue_yoy')
        confidence = 0.7  # reduzierte Konfidenz
    else:
        confidence = 1.0

    rev_pts = 0
    rev_label = 'Keine Daten'
    if rev_cagr is not None:
        if rev_cagr >= 0.15:
            rev_pts = int(15 * confidence)
            rev_label = f"{rev_cagr*100:.1f}% — Ausgezeichnet (≥15%)"
        elif rev_cagr >= 0.10:
            rev_pts = int(10 * confidence)
            rev_label = f"{rev_cagr*100:.1f}% — Gut (10-15%)"
        elif rev_cagr >= 0.05:
            rev_pts = int(6 * confidence)
            rev_label = f"{rev_cagr*100:.1f}% — Solide (5-10%)"
        elif rev_cagr >= 0:
            rev_pts = int(2 * confidence)
            rev_label = f"{rev_cagr*100:.1f}% — Schwach (0-5%)"
        else:
            rev_pts = 0
            rev_label = f"{rev_cagr*100:.1f}% — Negativ"
    breakdown['revenue_cagr'] = {'pts': rev_pts, 'max': 15, 'label': rev_label}

    # EPS CAGR 3yr (10 Punkte)
    eps_cagr = growth.get('eps_cagr_3yr')
    if eps_cagr is None:
        eps_cagr = growth.get('earnings_yoy')
        eps_confidence = 0.7
    else:
        eps_confidence = 1.0

    eps_pts = 0
    eps_label = 'Keine Daten'
    if eps_cagr is not None:
        if eps_cagr >= 0.15:
            eps_pts = int(10 * eps_confidence)
            eps_label = f"{eps_cagr*100:.1f}% — Ausgezeichnet (≥15%)"
        elif eps_cagr >= 0.10:
            eps_pts = int(7 * eps_confidence)
            eps_label = f"{eps_cagr*100:.1f}% — Gut (10-15%)"
        elif eps_cagr >= 0.05:
            eps_pts = int(4 * eps_confidence)
            eps_label = f"{eps_cagr*100:.1f}% — Solide (5-10%)"
        elif eps_cagr >= 0:
            eps_pts = int(1 * eps_confidence)
            eps_label = f"{eps_cagr*100:.1f}% — Schwach (0-5%)"
        else:
            eps_pts = 0
            eps_label = f"{eps_cagr*100:.1f}% — Negativ"
    breakdown['eps_cagr'] = {'pts': eps_pts, 'max': 10, 'label': eps_label}

    # EPS Konsistenz (5 Punkte)
    consistency = growth.get('eps_consistency')
    cons_pts = 0
    cons_label = 'Keine Daten'
    if consistency is not None:
        if consistency >= 1.0:
            cons_pts = 5
            cons_label = "Immer positiv — Ausgezeichnet"
        elif consistency >= 0.67:
            cons_pts = 3
            cons_label = "Meist positiv — Gut"
        elif consistency >= 0.33:
            cons_pts = 1
            cons_label = "Unbeständig — Schwach"
        else:
            cons_pts = 0
            cons_label = "Überwiegend negativ"
    breakdown['eps_consistency'] = {'pts': cons_pts, 'max': 5, 'label': cons_label}

    total = rev_pts + eps_pts + cons_pts
    return total, breakdown


def _score_profitability(profitability: dict, balance_sheet: dict) -> tuple[int, dict]:
    """Profitabilität: max. 30 Punkte"""
    breakdown = {}

    # ROE (12 Punkte)
    roe = profitability.get('roe')
    de = balance_sheet.get('debt_to_equity', 0) or 0
    roe_pts = 0
    roe_label = 'Keine Daten'
    if roe is not None:
        if roe >= 0.25:
            roe_pts = 12
            roe_label = f"{roe*100:.1f}% — Ausgezeichnet (≥25%)"
        elif roe >= 0.15:
            roe_pts = 9
            roe_label = f"{roe*100:.1f}% — Gut (15-25%)"
        elif roe >= 0.10:
            roe_pts = 5
            roe_label = f"{roe*100:.1f}% — Solide (10-15%)"
        elif roe >= 0.05:
            roe_pts = 2
            roe_label = f"{roe*100:.1f}% — Schwach (5-10%)"
        else:
            roe_pts = 0
            roe_label = f"{roe*100:.1f}% — Sehr schwach (<5%)"

        # Sonderfall: ROE durch Leverage aufgeblasen
        if roe > 0.40 and de > 3.0:
            roe_pts = min(roe_pts, 9)
            roe_label += " ⚠ (ggf. durch Verschuldung erhöht)"
    breakdown['roe'] = {'pts': roe_pts, 'max': 12, 'label': roe_label}

    # Net Margin (10 Punkte)
    net_margin = profitability.get('net_margin')
    nm_pts = 0
    nm_label = 'Keine Daten'
    if net_margin is not None:
        if net_margin >= 0.20:
            nm_pts = 10
            nm_label = f"{net_margin*100:.1f}% — Ausgezeichnet (≥20%)"
        elif net_margin >= 0.10:
            nm_pts = 7
            nm_label = f"{net_margin*100:.1f}% — Gut (10-20%)"
        elif net_margin >= 0.05:
            nm_pts = 4
            nm_label = f"{net_margin*100:.1f}% — Solide (5-10%)"
        elif net_margin >= 0:
            nm_pts = 1
            nm_label = f"{net_margin*100:.1f}% — Schwach (0-5%)"
        else:
            nm_pts = 0
            nm_label = f"{net_margin*100:.1f}% — Verlust"
    breakdown['net_margin'] = {'pts': nm_pts, 'max': 10, 'label': nm_label}

    # FCF Margin (8 Punkte)
    fcf_margin = profitability.get('fcf_margin')
    fcf_pts = 0
    fcf_label = 'Keine Daten'
    if fcf_margin is not None:
        if fcf_margin >= 0.15:
            fcf_pts = 8
            fcf_label = f"{fcf_margin*100:.1f}% — Ausgezeichnet (≥15%)"
        elif fcf_margin >= 0.08:
            fcf_pts = 5
            fcf_label = f"{fcf_margin*100:.1f}% — Gut (8-15%)"
        elif fcf_margin >= 0:
            fcf_pts = 2
            fcf_label = f"{fcf_margin*100:.1f}% — Solide (0-8%)"
        else:
            fcf_pts = 0
            fcf_label = f"{fcf_margin*100:.1f}% — Negativer FCF"
    breakdown['fcf_margin'] = {'pts': fcf_pts, 'max': 8, 'label': fcf_label}

    total = roe_pts + nm_pts + fcf_pts
    return total, breakdown


def _score_balance_sheet(balance_sheet: dict, is_financial_sector: bool) -> tuple[int, dict]:
    """Bilanzqualität: max. 20 Punkte"""
    breakdown = {}

    # Debt/Equity (8 Punkte) – nicht für Finanzsektor
    de = balance_sheet.get('debt_to_equity')
    de_pts = 0
    de_label = 'Keine Daten'
    if is_financial_sector:
        de_pts = 4  # Neutrale Punkte für Finanzsektor
        de_label = "Nicht anwendbar (Finanzsektor)"
    elif de is not None:
        if de < 0.3:
            de_pts = 8
            de_label = f"{de:.2f}x — Ausgezeichnet (<0.3x)"
        elif de < 0.5:
            de_pts = 6
            de_label = f"{de:.2f}x — Gut (0.3-0.5x)"
        elif de < 1.0:
            de_pts = 4
            de_label = f"{de:.2f}x — Solide (0.5-1.0x)"
        elif de < 2.0:
            de_pts = 2
            de_label = f"{de:.2f}x — Erhöht (1.0-2.0x)"
        else:
            de_pts = 0
            de_label = f"{de:.2f}x — Hoch (>2.0x)"
    breakdown['debt_equity'] = {'pts': de_pts, 'max': 8, 'label': de_label}

    # Current Ratio (6 Punkte)
    cr = balance_sheet.get('current_ratio')
    cr_pts = 0
    cr_label = 'Keine Daten'
    if cr is not None:
        if cr >= 2.0:
            cr_pts = 6
            cr_label = f"{cr:.2f} — Ausgezeichnet (≥2.0)"
        elif cr >= 1.5:
            cr_pts = 4
            cr_label = f"{cr:.2f} — Gut (1.5-2.0)"
        elif cr >= 1.0:
            cr_pts = 2
            cr_label = f"{cr:.2f} — Solide (1.0-1.5)"
        else:
            cr_pts = 0
            cr_label = f"{cr:.2f} — Kritisch (<1.0)"
    breakdown['current_ratio'] = {'pts': cr_pts, 'max': 6, 'label': cr_label}

    # FCF Konsistenz (6 Punkte)
    fcf_hist = balance_sheet.get('fcf_history', [])
    fcf_pts = 0
    fcf_label = 'Keine Daten'
    if fcf_hist:
        positive = sum(1 for v in fcf_hist if v > 0)
        total_periods = len(fcf_hist)
        ratio = positive / total_periods
        if ratio >= 1.0:
            fcf_pts = 6
            fcf_label = f"{positive}/{total_periods} Jahre positiv — Ausgezeichnet"
        elif ratio >= 0.75:
            fcf_pts = 4
            fcf_label = f"{positive}/{total_periods} Jahre positiv — Gut"
        elif ratio >= 0.50:
            fcf_pts = 2
            fcf_label = f"{positive}/{total_periods} Jahre positiv — Solide"
        else:
            fcf_pts = 0
            fcf_label = f"{positive}/{total_periods} Jahre positiv — Schwach"
    breakdown['fcf_consistency'] = {'pts': fcf_pts, 'max': 6, 'label': fcf_label}

    total = de_pts + cr_pts + fcf_pts
    return total, breakdown


def _score_valuation(valuation: dict, growth: dict) -> tuple[int, dict]:
    """Bewertung: max. 20 Punkte (niedrigerer Score = teurer)"""
    breakdown = {}

    # PEG Ratio (10 Punkte)
    peg = valuation.get('peg')
    peg_pts = 0
    peg_label = 'Keine Daten'
    if peg is not None:
        if peg <= 0:
            peg_pts = 0
            peg_label = f"{peg:.2f} — Negativ (Wachstum negativ)"
        elif peg < 1.0:
            peg_pts = 10
            peg_label = f"{peg:.2f} — Attraktiv (<1.0)"
        elif peg < 1.5:
            peg_pts = 7
            peg_label = f"{peg:.2f} — Fair (1.0-1.5)"
        elif peg < 2.0:
            peg_pts = 4
            peg_label = f"{peg:.2f} — Leicht teuer (1.5-2.0)"
        elif peg < 3.0:
            peg_pts = 2
            peg_label = f"{peg:.2f} — Teuer (2.0-3.0)"
        else:
            peg_pts = 0
            peg_label = f"{peg:.2f} — Sehr teuer (>3.0)"
    breakdown['peg'] = {'pts': peg_pts, 'max': 10, 'label': peg_label}

    # P/FCF (6 Punkte)
    p_fcf = valuation.get('p_fcf')
    pfcf_pts = 0
    pfcf_label = 'Keine Daten'
    if p_fcf is not None:
        if p_fcf <= 0:
            pfcf_pts = 0
            pfcf_label = "N/A (negativer FCF)"
        elif p_fcf < 15:
            pfcf_pts = 6
            pfcf_label = f"{p_fcf:.1f}x — Günstig (<15x)"
        elif p_fcf < 25:
            pfcf_pts = 4
            pfcf_label = f"{p_fcf:.1f}x — Fair (15-25x)"
        elif p_fcf < 35:
            pfcf_pts = 2
            pfcf_label = f"{p_fcf:.1f}x — Teuer (25-35x)"
        else:
            pfcf_pts = 0
            pfcf_label = f"{p_fcf:.1f}x — Sehr teuer (>35x)"
    breakdown['p_fcf'] = {'pts': pfcf_pts, 'max': 6, 'label': pfcf_label}

    # Forward P/E (4 Punkte)
    fpe = valuation.get('forward_pe') or valuation.get('pe')
    fpe_pts = 0
    fpe_label = 'Keine Daten'
    if fpe is not None:
        if fpe <= 0:
            fpe_pts = 0
            fpe_label = "N/A (negatives KGV)"
        elif fpe < 15:
            fpe_pts = 4
            fpe_label = f"{fpe:.1f}x — Günstig (<15x)"
        elif fpe < 25:
            fpe_pts = 3
            fpe_label = f"{fpe:.1f}x — Fair (15-25x)"
        elif fpe < 35:
            fpe_pts = 2
            fpe_label = f"{fpe:.1f}x — Erhöht (25-35x)"
        elif fpe < 50:
            fpe_pts = 1
            fpe_label = f"{fpe:.1f}x — Teuer (35-50x)"
        else:
            fpe_pts = 0
            fpe_label = f"{fpe:.1f}x — Sehr teuer (>50x)"
    breakdown['forward_pe'] = {'pts': fpe_pts, 'max': 4, 'label': fpe_label}

    total = peg_pts + pfcf_pts + fpe_pts
    return total, breakdown


# ──────────────────────────────────────────────────────────────────────────────
# Empfehlung, Stärken & Risiken
# ──────────────────────────────────────────────────────────────────────────────

def _get_recommendation(score: int) -> tuple[str, str]:
    if score >= 75:
        return "KAUFEN", "#2e7d32"
    elif score >= 50:
        return "HALTEN", "#e65100"
    else:
        return "NICHT KAUFEN", "#c62828"


def _get_strengths(metrics: dict) -> list[str]:
    strengths = []
    g = metrics['growth']
    p = metrics['profitability']
    b = metrics['balance_sheet']
    v = metrics['valuation']

    if g.get('revenue_cagr_3yr') and g['revenue_cagr_3yr'] >= 0.15:
        strengths.append(f"Starkes Umsatzwachstum: {g['revenue_cagr_3yr']*100:.1f}% CAGR (3J) — übertrifft 15%-Benchmark")
    if g.get('eps_cagr_3yr') and g['eps_cagr_3yr'] >= 0.15:
        strengths.append(f"Starkes Gewinnwachstum: {g['eps_cagr_3yr']*100:.1f}% EPS-CAGR (3J)")
    if g.get('eps_consistency') and g['eps_consistency'] >= 1.0:
        strengths.append("Konsistentes Gewinnwachstum in allen betrachteten Jahren")
    if p.get('roe') and p['roe'] >= 0.20:
        strengths.append(f"Hohe Eigenkapitalrendite: {p['roe']*100:.1f}% ROE — starke Kapitaleffizienz")
    if p.get('net_margin') and p['net_margin'] >= 0.15:
        strengths.append(f"Starke Nettomarge: {p['net_margin']*100:.1f}% — robuste Ertragskraft")
    if p.get('fcf_margin') and p['fcf_margin'] >= 0.12:
        strengths.append(f"Ausgezeichnete FCF-Generierung: {p['fcf_margin']*100:.1f}% Free Cash Flow Marge")
    if b.get('debt_to_equity') is not None and b['debt_to_equity'] < 0.3:
        strengths.append(f"Sehr solide Bilanz: D/E-Ratio von {b['debt_to_equity']:.2f}x")
    if b.get('current_ratio') and b['current_ratio'] >= 2.0:
        strengths.append(f"Hohe Liquidität: Current Ratio {b['current_ratio']:.1f}x")
    if v.get('peg') and 0 < v['peg'] < 1.0:
        strengths.append(f"Attraktive Bewertung: PEG-Ratio {v['peg']:.2f} — günstig relativ zum Wachstum")
    if v.get('p_fcf') and 0 < v['p_fcf'] < 20:
        strengths.append(f"Günstig auf FCF-Basis: P/FCF von {v['p_fcf']:.1f}x")

    return strengths[:6]  # Max. 6 Stärken


def _get_concerns(metrics: dict) -> list[str]:
    concerns = []
    g = metrics['growth']
    p = metrics['profitability']
    b = metrics['balance_sheet']
    v = metrics['valuation']

    rev_cagr = g.get('revenue_cagr_3yr') or g.get('revenue_yoy')
    if rev_cagr is not None and rev_cagr < 0.05:
        concerns.append(f"Schwaches Umsatzwachstum: {rev_cagr*100:.1f}% — unterhalb der 5%-Mindestschwelle")
    if rev_cagr is not None and rev_cagr < 0:
        concerns.append(f"Rückläufiger Umsatz: {rev_cagr*100:.1f}% — strukturelles Problem")
    if g.get('eps_cagr_3yr') is not None and g['eps_cagr_3yr'] < 0:
        concerns.append(f"Negativer EPS-Trend: {g['eps_cagr_3yr']*100:.1f}% CAGR — Ertragskraft schwindet")
    if g.get('eps_consistency') is not None and g['eps_consistency'] < 0.5:
        concerns.append("Inkonsistentes Gewinnwachstum — fehlende Verlässlichkeit")
    if p.get('roe') is not None and p['roe'] < 0.10:
        concerns.append(f"Niedrige Eigenkapitalrendite: {p['roe']*100:.1f}% ROE — mangelnde Kapitaleffizienz")
    if p.get('net_margin') is not None and p['net_margin'] < 0:
        concerns.append(f"Unternehmen schreibt Verluste: Nettomarge {p['net_margin']*100:.1f}%")
    if p.get('fcf_margin') is not None and p['fcf_margin'] < 0:
        concerns.append("Negativer Free Cash Flow — Unternehmen verbrennt Kapital")
    if b.get('debt_to_equity') is not None and b['debt_to_equity'] > 2.0:
        concerns.append(f"Hohe Verschuldung: D/E-Ratio {b['debt_to_equity']:.2f}x — erhöhtes Finanzrisiko")
    if b.get('current_ratio') is not None and b['current_ratio'] < 1.0:
        concerns.append(f"Liquiditätsrisiko: Current Ratio {b['current_ratio']:.2f} — kurzfristige Verbindlichkeiten übersteigen Umlaufvermögen")
    if v.get('peg') is not None and v['peg'] > 3.0:
        concerns.append(f"Sehr hohe Bewertung: PEG-Ratio {v['peg']:.2f} — teuer relativ zum Wachstum")
    if v.get('forward_pe') is not None and v['forward_pe'] > 50:
        concerns.append(f"Extrem hohes KGV: {v['forward_pe']:.1f}x — sehr hohe Wachstumserwartungen eingepreist")

    return concerns[:6]  # Max. 6 Risiken


def _get_data_warnings(metrics: dict) -> list[str]:
    warnings = []
    g = metrics['growth']
    b = metrics['balance_sheet']

    if g.get('revenue_cagr_3yr') is None and g.get('revenue_yoy') is not None:
        warnings.append("Umsatz-CAGR basiert auf Schätzung (nur 1 Jahr verfügbar) — reduzierte Genauigkeit")
    if g.get('revenue_cagr_3yr') is None and g.get('revenue_yoy') is None:
        warnings.append("Keine Umsatzdaten verfügbar — Wachstumsbewertung eingeschränkt")
    if g.get('eps_cagr_3yr') is None:
        warnings.append("Historische EPS-Daten nicht verfügbar — EPS-Scoring basiert auf Schätzung")
    if not b.get('fcf_history'):
        warnings.append("Keine FCF-Historie verfügbar — FCF-Konsistenz konnte nicht bewertet werden")
    if metrics['valuation'].get('peg') is None:
        warnings.append("PEG-Ratio nicht berechenbar — Bewertungsanalyse eingeschränkt")

    return warnings
