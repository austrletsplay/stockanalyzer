"""
app.py – Streamlit Web-App für Quality-Growth Fundamentalanalyse.
"""

import streamlit as st
import plotly.graph_objects as go
from datetime import date

from analyzer import fetch_stock_data, calculate_metrics, fetch_price_history, PERIOD_CONFIG
from scorer import calculate_score
from excel_export import generate_excel

# ── Glossar aller Fachbegriffe ─────────────────────────────────────────────────
GLOSSARY = {
    # Score-Kategorien
    "Wachstum": (
        "**Wachstum** misst, wie stark das Unternehmen seinen Umsatz und Gewinn über mehrere "
        "Jahre steigern konnte.\n\n"
        "Ein Quality-Growth-Unternehmen wächst idealerweise **≥15% pro Jahr** – "
        "das verdoppelt den Umsatz alle ~5 Jahre. Je höher und konsistenter das Wachstum, "
        "desto besser.\n\n"
        "📌 *Enthält: Umsatz-CAGR, EPS-CAGR, EPS-Konsistenz*"
    ),
    "Profitabilität": (
        "**Profitabilität** zeigt, wie viel vom Umsatz am Ende als Gewinn und Cash übrig bleibt.\n\n"
        "Ein Unternehmen kann stark wachsen und trotzdem kein Geld verdienen – "
        "hohe Profitabilität ist das Zeichen eines echten Burggrabens (Wettbewerbsvorteil).\n\n"
        "📌 *Enthält: ROE, Nettomarge, FCF-Marge*"
    ),
    "Bilanzqualität": (
        "**Bilanzqualität** bewertet, wie solide die finanzielle Basis des Unternehmens ist.\n\n"
        "Wenig Schulden, ausreichend Liquidität und konstanter Free Cash Flow bedeuten, "
        "dass das Unternehmen Krisen übersteht und nicht auf Fremdkapital angewiesen ist.\n\n"
        "📌 *Enthält: Debt/Equity, Current Ratio, FCF-Konsistenz*"
    ),
    "Bewertung": (
        "**Bewertung** misst, wie viel du als Investor für die Unternehmensqualität bezahlst.\n\n"
        "Selbst ein exzellentes Unternehmen kann ein schlechtes Investment sein, "
        "wenn der Preis zu hoch ist. Niedrigere Kennzahlen bedeuten in der Regel "
        "eine günstigere Bewertung.\n\n"
        "📌 *Enthält: PEG-Ratio, P/FCF, Forward-KGV*"
    ),
    # Wachstum
    "Umsatz-CAGR (3J)": (
        "**Umsatz-CAGR** = *Compound Annual Growth Rate* des Umsatzes über 3 Jahre.\n\n"
        "Gibt an, wie viel Prozent der Umsatz **pro Jahr durchschnittlich gewachsen** ist – "
        "berücksichtigt den Zinseszinseffekt.\n\n"
        "**Beispiel:** CAGR von 20% bedeutet, der Umsatz hat sich in 3 Jahren auf "
        "~1,73× vergrößert (1,2³).\n\n"
        "🎯 *Quality-Growth-Ziel: ≥15% p.a.*"
    ),
    "EPS-CAGR (3J)": (
        "**EPS-CAGR** = Wachstumsrate des *Earnings Per Share* (Gewinn je Aktie) über 3 Jahre.\n\n"
        "Der EPS zeigt, wie viel Gewinn **auf jede einzelne Aktie** entfällt. "
        "Steigt der EPS schneller als der Umsatz, verbessern sich die Margen.\n\n"
        "**Wichtig:** EPS kann durch Aktienrückkäufe steigen, auch wenn der Gesamtgewinn gleich bleibt. "
        "Daher immer zusammen mit der Umsatzentwicklung betrachten.\n\n"
        "🎯 *Quality-Growth-Ziel: ≥15% p.a.*"
    ),
    "EPS Konsistenz": (
        "**EPS-Konsistenz** gibt an, in wie vielen der letzten Jahre der Gewinn je Aktie "
        "gegenüber dem Vorjahr **gestiegen** ist.\n\n"
        "100% = jedes Jahr Gewinnsteigerung → sehr verlässliches Unternehmen\n"
        "50% = jedes zweite Jahr rückläufig → unbeständig, höheres Risiko\n\n"
        "Ein Quality-Growth-Unternehmen wächst **konsistent**, nicht nur in guten Jahren.\n\n"
        "🎯 *Quality-Growth-Ziel: ≥ 2 von 3 Jahren positiv*"
    ),
    "Umsatz YoY": (
        "**Umsatz YoY** = *Year-over-Year* – das Umsatzwachstum im Vergleich zum **Vorjahr**.\n\n"
        "Anders als der CAGR zeigt YoY nur den letzten 12-Monats-Vergleich und kann "
        "durch Sondereffekte (Übernahmen, Währungen) verzerrt sein.\n\n"
        "📌 *Ergänzende Kennzahl – aussagekräftiger ist der 3-Jahres-CAGR*"
    ),
    "Gewinn YoY": (
        "**Gewinn YoY** = Nettowachstum des Gewinns im Vergleich zum **Vorjahr**.\n\n"
        "Zeigt, ob das Unternehmen aktuell auf Wachstumskurs ist. "
        "Temporäre Rückgänge können durch Investitionen oder Sonderabschreibungen entstehen.\n\n"
        "📌 *Ergänzende Kennzahl – den Trend über mehrere Jahre beachten*"
    ),
    # Profitabilität
    "ROE (Eigenkapitalrendite)": (
        "**ROE** = *Return on Equity* = Eigenkapitalrendite.\n\n"
        "Zeigt, wie viel Gewinn das Unternehmen **mit dem Geld der Aktionäre** erwirtschaftet.\n\n"
        "**Formel:** Nettogewinn ÷ Eigenkapital\n\n"
        "**Beispiel:** ROE 25% = aus 100€ Eigenkapital werden 25€ Gewinn pro Jahr.\n\n"
        "⚠️ *Vorsicht: Ein sehr hoher ROE (>40%) kann durch hohe Verschuldung entstehen, "
        "nicht durch echte Stärke.*\n\n"
        "🎯 *Quality-Growth-Ziel: ≥15%, besser ≥20%*"
    ),
    "Nettomarge": (
        "**Nettomarge** = Nettogewinnmarge.\n\n"
        "Gibt an, wie viel Prozent des Umsatzes am Ende als **Reingewinn** übrig bleibt – "
        "nach allen Kosten, Steuern und Zinsen.\n\n"
        "**Formel:** Nettogewinn ÷ Umsatz\n\n"
        "**Beispiel:** Nettomarge 20% = von 100€ Umsatz bleiben 20€ Gewinn.\n\n"
        "Hohe Nettomarge = starker Wettbewerbsvorteil (Burggraben).\n\n"
        "🎯 *Quality-Growth-Ziel: ≥10%, besser ≥15%*"
    ),
    "FCF-Marge": (
        "**FCF-Marge** = Free Cash Flow Marge.\n\n"
        "Zeigt, wie viel Prozent des Umsatzes als **echter Barmittelüberschuss** anfällt – "
        "nach Investitionen in Maschinen, Gebäude etc.\n\n"
        "**Warum wichtig?** Gewinne können buchhalterisch manipuliert werden, "
        "Cash nicht. FCF ist das 'echte Geld' des Unternehmens.\n\n"
        "**Formel:** Free Cash Flow ÷ Umsatz\n\n"
        "🎯 *Quality-Growth-Ziel: ≥8%, besser ≥15%*"
    ),
    "Bruttomarge": (
        "**Bruttomarge** = Anteil des Umsatzes nach Abzug der direkten Produktionskosten.\n\n"
        "**Formel:** (Umsatz − Herstellungskosten) ÷ Umsatz\n\n"
        "Eine hohe Bruttomarge zeigt, dass das Unternehmen seine Produkte/Dienstleistungen "
        "mit großem Aufschlag verkaufen kann → Preissetzungsmacht.\n\n"
        "Software-Unternehmen: oft 70–90% | Händler: oft 20–40%\n\n"
        "🎯 *Je höher, desto besser – Vergleich innerhalb der Branche*"
    ),
    "EBIT-Marge": (
        "**EBIT-Marge** = *Earnings Before Interest and Taxes* – Betriebsmarge.\n\n"
        "Zeigt die Profitabilität des **operativen Kerngeschäfts** – ohne Zinskosten "
        "und Steuern (die vom Finanzierungsmodell abhängen).\n\n"
        "**Formel:** EBIT ÷ Umsatz\n\n"
        "Gut zum Vergleich zwischen Unternehmen, unabhängig von ihrer Kapitalstruktur.\n\n"
        "🎯 *Quality-Growth-Ziel: ≥15%*"
    ),
    "EBITDA-Marge": (
        "**EBITDA-Marge** = *Earnings Before Interest, Taxes, Depreciation and Amortization*.\n\n"
        "Ähnlich wie EBIT-Marge, aber zusätzlich werden **Abschreibungen** herausgerechnet. "
        "Gibt den 'Cash-Betriebsgewinn' an, bevor Investitionen berücksichtigt werden.\n\n"
        "Besonders beliebt in kapitalintensiven Branchen (Industrie, Telekom).\n\n"
        "⚠️ *Hohe Abschreibungen können EBITDA schönrechnen – immer auch FCF prüfen.*\n\n"
        "🎯 *Quality-Growth-Ziel: ≥20%*"
    ),
    "ROA": (
        "**ROA** = *Return on Assets* = Gesamtkapitalrendite.\n\n"
        "Zeigt, wie effizient das Unternehmen **mit seinem gesamten Vermögen** (Eigenkapital + "
        "Schulden) wirtschaftet.\n\n"
        "**Formel:** Nettogewinn ÷ Bilanzsumme\n\n"
        "Im Gegensatz zum ROE ist ROA nicht durch hohe Verschuldung aufblähbar – "
        "daher oft aussagekräftiger für den Vergleich.\n\n"
        "🎯 *Quality-Growth-Ziel: ≥5%, besser ≥10%*"
    ),
    # Bilanz
    "Debt/Equity": (
        "**Debt/Equity Ratio** = Verschuldungsgrad.\n\n"
        "Zeigt das Verhältnis von **Fremdkapital (Schulden) zu Eigenkapital**.\n\n"
        "**Beispiel:** D/E = 0,5x → für 1€ Eigenkapital gibt es 0,50€ Schulden.\n\n"
        "Hohe Schulden erhöhen das Risiko, besonders in Rezessionen oder bei "
        "steigenden Zinsen. Ein Quality-Growth-Unternehmen braucht idealerweise "
        "kaum Fremdkapital.\n\n"
        "⚠️ *Für Banken/Versicherungen gilt eine andere Logik – D/E dort nicht vergleichbar.*\n\n"
        "🎯 *Quality-Growth-Ziel: <0,5x, besser <0,3x*"
    ),
    "Current Ratio": (
        "**Current Ratio** = Liquiditätsgrad 2. Ordnung.\n\n"
        "Zeigt, ob das Unternehmen seine **kurzfristigen Schulden** (fällig in <1 Jahr) "
        "mit seinen kurzfristigen Vermögenswerten bezahlen kann.\n\n"
        "**Formel:** Umlaufvermögen ÷ kurzfristige Verbindlichkeiten\n\n"
        "- **> 2,0** = sehr komfortable Liquidität\n"
        "- **1,0–2,0** = ausreichend\n"
        "- **< 1,0** = potenzielle Liquiditätsprobleme – Warnsignal!\n\n"
        "🎯 *Quality-Growth-Ziel: ≥1,5*"
    ),
    "Quick Ratio": (
        "**Quick Ratio** = Liquiditätsgrad (ohne Lagerbestände).\n\n"
        "Ähnlich wie Current Ratio, aber **Lagerbestände werden herausgerechnet**, "
        "da sie nicht sofort zu Geld gemacht werden können.\n\n"
        "**Formel:** (Umlaufvermögen − Vorräte) ÷ kurzfristige Verbindlichkeiten\n\n"
        "Besonders relevant für Handels- oder Fertigungsunternehmen mit hohen Lagerbeständen.\n\n"
        "🎯 *Ziel: ≥1,0*"
    ),
    "FCF Konsistenz": (
        "**FCF-Konsistenz** = Anteil der Jahre mit positivem Free Cash Flow.\n\n"
        "**Free Cash Flow** ist der Geldbetrag, der nach allen Betriebsausgaben und "
        "Investitionen übrig bleibt – das Geld, das das Unternehmen frei einsetzen kann "
        "(Dividenden, Rückkäufe, Schuldenabbau, Übernahmen).\n\n"
        "4/4 Jahre positiv = sehr zuverlässige Geldmaschine.\n\n"
        "🎯 *Quality-Growth-Ziel: ≥3 von 4 Jahren positiver FCF*"
    ),
    "Gesamtschulden": (
        "**Gesamtschulden** = Summe aller kurz- und langfristigen Verbindlichkeiten "
        "gegenüber Gläubigern (Banken, Anleihen etc.).\n\n"
        "Absolute Zahl – sinnvoll im Verhältnis zum Eigenkapital (D/E-Ratio) "
        "oder zum EBITDA betrachten.\n\n"
        "📌 *Nur als Kontextzahl – D/E und Current Ratio sind aussagekräftiger*"
    ),
    "Kassenbestand": (
        "**Kassenbestand** = Summe aus Bargeld und kurzfristigen Geldanlagen des Unternehmens.\n\n"
        "Viel Cash bedeutet finanzielle Flexibilität: Übernahmen, Investitionen, "
        "Aktienrückkäufe oder Krisenpolster – ohne neue Schulden aufnehmen zu müssen.\n\n"
        "📌 *Netto-Cash = Kassenbestand − Gesamtschulden (positiv = schuldenfrei)*"
    ),
    # Bewertung
    "PEG Ratio": (
        "**PEG Ratio** = *Price/Earnings to Growth* Ratio.\n\n"
        "Setzt das KGV ins Verhältnis zum **Gewinnwachstum** – damit wird die Bewertung "
        "um das Wachstum bereinigt.\n\n"
        "**Formel:** KGV ÷ EPS-Wachstumsrate (in %)\n\n"
        "- **PEG < 1,0** = günstig relativ zum Wachstum\n"
        "- **PEG = 1,0** = fair bewertet\n"
        "- **PEG > 2,0** = teuer, hohes Wachstum muss sich erst bewahrheiten\n\n"
        "**Beispiel:** KGV 30, Gewinnwachstum 20% → PEG = 1,5\n\n"
        "🎯 *Quality-Growth-Ziel: <1,5*"
    ),
    "P/FCF": (
        "**P/FCF** = Kurs-Free-Cash-Flow-Verhältnis.\n\n"
        "Wie viele Jahre Free Cash Flow brauchst du, um den aktuellen Aktienkurs zu 'verdienen'?\n\n"
        "**Formel:** Marktkapitalisierung ÷ Free Cash Flow\n\n"
        "Gilt als zuverlässiger als das KGV, weil FCF schwerer zu manipulieren ist.\n\n"
        "- **P/FCF < 15** = günstig\n"
        "- **P/FCF 15–25** = fair\n"
        "- **P/FCF > 35** = teuer\n\n"
        "🎯 *Quality-Growth-Ziel: <25x*"
    ),
    "Forward KGV": (
        "**Forward KGV** = Kurs-Gewinn-Verhältnis basierend auf dem **erwarteten** Gewinn "
        "der nächsten 12 Monate.\n\n"
        "**Formel:** Aktienkurs ÷ geschätzter EPS (nächste 12 Monate)\n\n"
        "Zeigt, was Investoren bereit sind, für den **zukünftigen** Gewinn zu bezahlen. "
        "Niedriger als das Trailing-KGV = Analysten erwarten Gewinnwachstum.\n\n"
        "- **< 15** = günstig\n- **15–25** = faire Bewertung\n"
        "- **> 35** = hohe Wachstumserwartungen eingepreist\n\n"
        "🎯 *Quality-Growth-Ziel: <25x*"
    ),
    "Trailing KGV": (
        "**Trailing KGV** (KGV) = Kurs-Gewinn-Verhältnis auf Basis des **letzten** "
        "Jahresgewinns.\n\n"
        "**Formel:** Aktienkurs ÷ EPS der letzten 12 Monate\n\n"
        "Zeigt, wie viele Jahre Gewinn du zum aktuellen Kurs 'zahlst'. "
        "Ein KGV von 20 bedeutet: du zahlst das 20-fache des Jahresgewinns.\n\n"
        "Historisch liegt der Marktdurchschnitt bei ~15–18. "
        "Wachstumsunternehmen haben oft höhere KGVs.\n\n"
        "🎯 *Quality-Growth-Ziel: <30x (je nach Wachstum)*"
    ),
    "KBV (P/Book)": (
        "**KBV** = Kurs-Buchwert-Verhältnis (*Price-to-Book*).\n\n"
        "Vergleicht den Börsenwert mit dem **Buchwert des Eigenkapitals** laut Bilanz.\n\n"
        "**Formel:** Aktienkurs ÷ Buchwert je Aktie\n\n"
        "- **KBV < 1** = Aktie kostet weniger als der Buchwert → klassischer Value-Indicator\n"
        "- **KBV > 3** = Markt zahlt erheblich mehr als den Buchwert → erwartet hohe Renditen\n\n"
        "Bei Software-Unternehmen mit wenig Sachvermögen ist KBV oft wenig aussagekräftig.\n\n"
        "🎯 *Ziel: <3x, in Kombination mit anderen Kennzahlen betrachten*"
    ),
    "KUV (P/Sales)": (
        "**KUV** = Kurs-Umsatz-Verhältnis (*Price-to-Sales*).\n\n"
        "Setzt den Börsenwert ins Verhältnis zum **Umsatz** – unabhängig von Profitabilität.\n\n"
        "**Formel:** Marktkapitalisierung ÷ Jahresumsatz\n\n"
        "Besonders nützlich bei noch unprofitablen Wachstumsunternehmen, "
        "wo KGV nicht sinnvoll berechenbar ist.\n\n"
        "- **KUV < 2** = günstig\n"
        "- **KUV > 10** = sehr teuer, nur bei sehr hohem Wachstum gerechtfertigt\n\n"
        "🎯 *Ziel: <5x*"
    ),
    "EV/EBITDA": (
        "**EV/EBITDA** = Enterprise Value zu EBITDA.\n\n"
        "**Enterprise Value** = Marktkapitalisierung + Schulden − Cash\n"
        "= 'Gesamtpreis' des Unternehmens, wenn man es komplett kaufen würde.\n\n"
        "EV/EBITDA zeigt, wie viele Jahre EBITDA nötig wären, um den Gesamtpreis zu bezahlen.\n\n"
        "Vorteil: Nicht durch Kapitalstruktur (Schulden) oder Steuern verzerrt – "
        "ideal für Unternehmensvergleiche.\n\n"
        "- **< 10** = günstig\n- **10–15** = fair\n- **> 20** = teuer\n\n"
        "🎯 *Quality-Growth-Ziel: <15x*"
    ),
}


def _info_popup(term_key: str, label: str | None = None):
    """
    Rendert einen kleinen ℹ-Button mit Popover für den Fachbegriff.
    term_key muss im GLOSSARY vorhanden sein.
    """
    explanation = GLOSSARY.get(term_key)
    if not explanation:
        return
    display = label or term_key
    with st.popover(f"ℹ️", help=f"Was bedeutet '{display}'?"):
        st.markdown(f"### {display}")
        st.markdown(explanation)

st.set_page_config(
    page_title="Stock Analyzer — Quality Growth",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS für mobile Optimierung ─────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .rec-banner {
        padding: 18px 24px;
        border-radius: 12px;
        text-align: center;
        font-size: 22px;
        font-weight: 700;
        color: white;
        margin: 16px 0;
        letter-spacing: 0.5px;
    }
    .metric-card {
        background: #1a1f2e;
        border-radius: 10px;
        padding: 12px 16px;
        text-align: center;
        margin: 4px 0;
    }
    .metric-label { font-size: 12px; color: #aaa; margin-bottom: 4px; }
    .metric-value { font-size: 20px; font-weight: 700; color: #fff; }
    .strength-item { color: #4caf50; margin: 4px 0; }
    .concern-item  { color: #ff7043; margin: 4px 0; }
    div[data-testid="stTabs"] button { font-size: 14px; }
    @media (max-width: 600px) {
        .rec-banner { font-size: 18px; padding: 14px 12px; }
    }
</style>
""", unsafe_allow_html=True)


# ── Hauptfunktion ──────────────────────────────────────────────────────────────

def main():
    st.title("📊 Stock Analyzer")
    st.caption("Fundamentalanalyse nach Quality-Growth-Stil (Fisher/Buffett · 5–10 Jahre Haltedauer)")

    st.markdown("---")

    # Eingabe-Bereich
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        ticker_input = st.text_input(
            "Ticker eingeben",
            placeholder="z.B. AAPL · MSFT · SAP.DE · NESN.SW · 7203.T",
            label_visibility="collapsed",
        )
    with col_btn:
        analyze_btn = st.button("Analysieren", type="primary", use_container_width=True)

    st.caption(
        "Weltweite Ticker: USA ohne Suffix (AAPL), Deutschland (.DE), Schweiz (.SW), "
        "Japan (.T), UK (.L)"
    )

    # Analyse ausführen
    if analyze_btn and ticker_input.strip():
        _run_analysis(ticker_input.strip())
    elif 'last_metrics' in st.session_state and 'last_scores' in st.session_state:
        _show_results(
            st.session_state['last_metrics'],
            st.session_state['last_scores'],
            st.session_state.get('last_ticker', ''),
        )
    else:
        _show_welcome()


def _run_analysis(ticker: str):
    ticker = ticker.upper()

    with st.spinner(f"Analysiere {ticker} …"):
        try:
            raw_data = fetch_stock_data(ticker)
            metrics = calculate_metrics(raw_data)
        except ValueError as e:
            st.error(f"**Fehler:** {e}")
            return
        except Exception as e:
            st.error(f"**Unerwarteter Fehler:** {e}")
            return

    scores = calculate_score(metrics)

    # In Session State cachen (Tab-Wechsel löst keinen Re-Fetch aus)
    st.session_state['last_ticker'] = ticker
    st.session_state['last_metrics'] = metrics
    st.session_state['last_scores'] = scores

    _show_results(metrics, scores, ticker)


def _show_results(metrics: dict, scores: dict, ticker: str):
    company = metrics['company']

    # Unternehmen-Header
    st.subheader(f"{company['name']}  ({ticker})")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.caption(f"**Sektor:** {company.get('sector', 'N/A')}")
    with col2:
        st.caption(f"**Land:** {company.get('country', 'N/A')}")
    with col3:
        st.caption(f"**Market Cap:** {company.get('market_cap_fmt', 'N/A')}")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Übersicht", "Kennzahlen", "Bericht", "Export"])

    with tab1:
        _tab_overview(metrics, scores)
    with tab2:
        _tab_details(metrics, scores)
    with tab3:
        _tab_report(metrics, scores)
    with tab4:
        _tab_export(metrics, scores, ticker)


def _show_welcome():
    st.markdown("---")
    st.markdown("""
    ### Wie es funktioniert

    1. **Ticker eingeben** — z.B. `AAPL` für Apple, `SAP.DE` für SAP
    2. **Analysieren** — die App lädt aktuelle Fundamentaldaten von Yahoo Finance
    3. **Score prüfen** — Quality-Growth-Bewertung von 0–100 Punkten:
       - 🟢 **75–100**: KAUFEN — starkes Quality-Growth-Unternehmen
       - 🟡 **50–74**: HALTEN — gut, aber Einschränkungen
       - 🔴 **0–49**: NICHT KAUFEN — erfüllt Kriterien nicht
    4. **Excel exportieren** — alle Kennzahlen als formatierte Datei

    **Bewertungslogik:** Wachstum (30 Pkt) · Profitabilität (30 Pkt) · Bilanz (20 Pkt) · Bewertung (20 Pkt)
    """)


# ── Tab 1: Übersicht ───────────────────────────────────────────────────────────

def _tab_overview(metrics: dict, scores: dict):
    rec = scores['recommendation']
    total = scores['total_score']
    color_map = {"KAUFEN": "#1b5e20", "HALTEN": "#e65100", "NICHT KAUFEN": "#c62828"}
    color = color_map.get(rec, "#333")
    ticker = metrics['company']['ticker']

    # Empfehlungs-Banner
    st.markdown(
        f'<div class="rec-banner" style="background:{color}">'
        f'{rec} — {total} / 100 Punkte</div>',
        unsafe_allow_html=True,
    )

    # ── Kurschart ─────────────────────────────────────────────────────────────
    st.markdown("#### Kursentwicklung")
    periods = list(PERIOD_CONFIG.keys())  # ['1T','1W','1M','6M','1J','5J']

    # Zeitraum-Auswahl per Button-Leiste
    if 'price_period' not in st.session_state:
        st.session_state['price_period'] = '1M'

    btn_cols = st.columns(len(periods))
    for col, label in zip(btn_cols, periods):
        with col:
            active = st.session_state['price_period'] == label
            if st.button(
                label,
                key=f"period_{label}",
                type="primary" if active else "secondary",
                use_container_width=True,
            ):
                st.session_state['price_period'] = label
                st.rerun()

    selected_period = st.session_state['price_period']
    cache_key = f"price_{ticker}_{selected_period}"

    if cache_key not in st.session_state:
        with st.spinner("Lade Kursdaten…"):
            df = fetch_price_history(ticker, selected_period)
        st.session_state[cache_key] = df
    else:
        df = st.session_state[cache_key]

    if df is not None and not df.empty:
        st.plotly_chart(
            _create_price_chart(df, ticker, selected_period, metrics['company'].get('currency', 'USD')),
            use_container_width=True,
        )
    else:
        st.info("Kursdaten für diesen Zeitraum nicht verfügbar.")

    st.markdown("---")

    # ── Score-Kacheln ──────────────────────────────────────────────────────────
    cat = scores['category_scores']
    col1, col2 = st.columns(2)
    with col1:
        g = cat['growth']
        _score_card_with_popup("Wachstum", g['score'], g['max'])
        b = cat['balance_sheet']
        _score_card_with_popup("Bilanzqualität", b['score'], b['max'])
    with col2:
        p = cat['profitability']
        _score_card_with_popup("Profitabilität", p['score'], p['max'])
        v = cat['valuation']
        _score_card_with_popup("Bewertung", v['score'], v['max'])

    # Radar-Chart
    fig = _create_radar_chart(scores)
    st.plotly_chart(fig, use_container_width=True)

    # Stärken
    if scores['strengths']:
        st.markdown("#### Stärken")
        for s in scores['strengths']:
            st.success(f"✓  {s}")

    # Risiken
    if scores['concerns']:
        st.markdown("#### Risiken / Schwächen")
        for c in scores['concerns']:
            st.warning(f"⚠  {c}")

    # Datenwarnungen
    if scores['data_warnings']:
        with st.expander("ℹ Datenverfügbarkeit"):
            for w in scores['data_warnings']:
                st.info(w)


# ── Tab 2: Kennzahlen-Details ──────────────────────────────────────────────────

def _tab_details(metrics: dict, scores: dict):
    g = metrics['growth']
    p = metrics['profitability']
    b = metrics['balance_sheet']
    v = metrics['valuation']

    def pct(val): return f"{val*100:.1f}%" if val is not None else "N/A"
    def x(val):   return f"{val:.2f}x" if val is not None else "N/A"
    def n(val):   return f"{val:.2f}" if val is not None else "N/A"

    # ── Wachstum ──
    with st.expander("📈  Wachstum (Growth)", expanded=True):
        _render_breakdown_table([
            ("Umsatz-CAGR (3J)", pct(g.get('revenue_cagr_3yr')), "≥15%",
             scores['category_scores']['growth']['breakdown'].get('revenue_cagr', {})),
            ("EPS-CAGR (3J)", pct(g.get('eps_cagr_3yr')), "≥15%",
             scores['category_scores']['growth']['breakdown'].get('eps_cagr', {})),
            ("EPS Konsistenz", _fmt_consistency_pct(g.get('eps_consistency')), "100%",
             scores['category_scores']['growth']['breakdown'].get('eps_consistency', {})),
            ("Umsatz YoY", pct(g.get('revenue_yoy')), "≥10%", {}),
            ("Gewinn YoY", pct(g.get('earnings_yoy')), "≥10%", {}),
        ])

        if g.get('revenue_history') and g.get('revenue_years'):
            st.plotly_chart(
                _bar_chart(g['revenue_years'], g['revenue_history'],
                           "Umsatzentwicklung", metrics['company'].get('currency', 'USD')),
                use_container_width=True,
            )
        if g.get('eps_history') and g.get('revenue_years'):
            st.plotly_chart(
                _bar_chart(g['revenue_years'][:len(g['eps_history'])], g['eps_history'],
                           "EPS-Entwicklung", metrics['company'].get('currency', 'USD'), colors=True),
                use_container_width=True,
            )

    # ── Profitabilität ──
    with st.expander("💰  Profitabilität", expanded=True):
        _render_breakdown_table([
            ("ROE (Eigenkapitalrendite)", pct(p.get('roe')), "≥15%",
             scores['category_scores']['profitability']['breakdown'].get('roe', {})),
            ("Nettomarge", pct(p.get('net_margin')), "≥10%",
             scores['category_scores']['profitability']['breakdown'].get('net_margin', {})),
            ("FCF-Marge", pct(p.get('fcf_margin')), "≥8%",
             scores['category_scores']['profitability']['breakdown'].get('fcf_margin', {})),
            ("Bruttomarge", pct(p.get('gross_margin')), "≥30%", {}),
            ("EBIT-Marge", pct(p.get('operating_margin')), "≥15%", {}),
            ("EBITDA-Marge", pct(p.get('ebitda_margin')), "≥20%", {}),
            ("ROA", pct(p.get('roa')), "≥5%", {}),
        ])

    # ── Bilanzqualität ──
    with st.expander("🏦  Bilanzqualität", expanded=True):
        _render_breakdown_table([
            ("Debt/Equity", x(b.get('debt_to_equity')), "<0.5x",
             scores['category_scores']['balance_sheet']['breakdown'].get('debt_equity', {})),
            ("Current Ratio", n(b.get('current_ratio')), "≥1.5",
             scores['category_scores']['balance_sheet']['breakdown'].get('current_ratio', {})),
            ("Quick Ratio", n(b.get('quick_ratio')), "≥1.0", {}),
            ("FCF Konsistenz", _fmt_fcf_cons(b.get('fcf_history', [])), "4/4 pos.",
             scores['category_scores']['balance_sheet']['breakdown'].get('fcf_consistency', {})),
            ("Gesamtschulden", _fmt_big(b.get('total_debt')), "—", {}),
            ("Kassenbestand", _fmt_big(b.get('total_cash')), "—", {}),
        ])

        if b.get('fcf_history') and b.get('fcf_years'):
            st.plotly_chart(
                _bar_chart(b['fcf_years'], b['fcf_history'],
                           "Free Cash Flow Entwicklung",
                           metrics['company'].get('currency', 'USD'), colors=True),
                use_container_width=True,
            )

    # ── Bewertung ──
    with st.expander("🏷  Bewertung (Valuation)", expanded=True):
        _render_breakdown_table([
            ("PEG Ratio", n(v.get('peg')), "<1.5",
             scores['category_scores']['valuation']['breakdown'].get('peg', {})),
            ("P/FCF", x(v.get('p_fcf')), "<25x",
             scores['category_scores']['valuation']['breakdown'].get('p_fcf', {})),
            ("Forward KGV", x(v.get('forward_pe')), "<25x",
             scores['category_scores']['valuation']['breakdown'].get('forward_pe', {})),
            ("Trailing KGV", x(v.get('pe')), "<30x", {}),
            ("KBV (P/Book)", x(v.get('pb')), "<3x", {}),
            ("KUV (P/Sales)", x(v.get('ps')), "<5x", {}),
            ("EV/EBITDA", x(v.get('ev_ebitda')), "<15x", {}),
        ])


def _render_breakdown_table(rows: list):
    """
    Rendert eine Kennzahlentabelle mit Farb-Coding und ℹ-Popover je Zeile.
    rows: list of (label, value, benchmark, breakdown_dict)
    """
    # Tabellenkopf
    h0, h1, h2, h3, h4 = st.columns([0.35, 2.8, 1.1, 1.1, 1.2])
    h0.markdown("<span style='color:#888;font-size:12px'>&nbsp;</span>", unsafe_allow_html=True)
    h1.markdown("<span style='color:#888;font-size:12px'>**Kennzahl**</span>", unsafe_allow_html=True)
    h2.markdown("<span style='color:#888;font-size:12px'>**Wert**</span>", unsafe_allow_html=True)
    h3.markdown("<span style='color:#888;font-size:12px'>**Benchmark**</span>", unsafe_allow_html=True)
    h4.markdown("<span style='color:#888;font-size:12px'>**Score**</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:2px 0 6px 0;opacity:0.2'>", unsafe_allow_html=True)

    for label, value, benchmark, breakdown in rows:
        pts = breakdown.get('pts')
        max_pts = breakdown.get('max')
        detail = breakdown.get('label', '')

        pts_str = f"{pts}/{max_pts}" if pts is not None and max_pts else "—"
        if pts is not None and max_pts:
            ratio = pts / max_pts
            dot = "🟢" if ratio >= 0.7 else ("🟡" if ratio >= 0.4 else "🔴")
        else:
            dot = "⚪"

        col0, col1, col2, col3, col4 = st.columns([0.35, 2.8, 1.1, 1.1, 1.2])

        # Info-Button (Popover)
        with col0:
            explanation = GLOSSARY.get(label)
            if explanation:
                with st.popover("ℹ️"):
                    st.markdown(f"### {label}")
                    st.markdown(explanation)
            else:
                st.write("")

        # Kennzahl-Name
        col1.markdown(f"<span style='font-size:14px'>{label}</span>", unsafe_allow_html=True)

        # Wert (farbig wenn Score vorhanden)
        if pts is not None and max_pts:
            ratio = pts / max_pts
            val_color = "#4caf50" if ratio >= 0.7 else ("#ffd54f" if ratio >= 0.4 else "#ef5350")
            col2.markdown(
                f"<span style='font-size:14px;font-weight:600;color:{val_color}'>{value}</span>",
                unsafe_allow_html=True,
            )
        else:
            col2.markdown(f"<span style='font-size:14px;color:#aaa'>{value}</span>", unsafe_allow_html=True)

        col3.markdown(f"<span style='font-size:13px;color:#aaa'>{benchmark}</span>", unsafe_allow_html=True)

        # Score-Anzeige mit Tooltip aus dem Breakdown-Label
        if detail:
            col4.markdown(
                f"<span title='{detail}' style='font-size:13px'>{dot} {pts_str}</span>",
                unsafe_allow_html=True,
            )
        else:
            col4.markdown(f"<span style='font-size:13px'>{dot} {pts_str}</span>", unsafe_allow_html=True)

        st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)


# ── Tab 3: Bericht ─────────────────────────────────────────────────────────────

def _tab_report(metrics: dict, scores: dict):
    company = metrics['company']
    g = metrics['growth']
    p = metrics['profitability']
    b = metrics['balance_sheet']
    v = metrics['valuation']
    rec = scores['recommendation']
    total = scores['total_score']

    def pct(val, label=""): return f"{val*100:.1f}%{label}" if val is not None else "N/A"
    def x(val): return f"{val:.2f}x" if val is not None else "N/A"

    st.markdown(f"## Fundamentalanalyse: {company['name']} ({company['ticker']})")
    st.markdown(f"*Erstellt am {date.today().strftime('%d. %B %Y')} · Quality-Growth-Stil*")
    st.markdown("---")

    # 1. Gesamtbewertung
    color_map = {"KAUFEN": "🟢", "HALTEN": "🟡", "NICHT KAUFEN": "🔴"}
    emoji = color_map.get(rec, "⚪")
    st.markdown(f"### {emoji} Gesamtbewertung: {rec} ({total}/100 Punkte)")
    cat = scores['category_scores']
    st.markdown(
        f"- Wachstum: **{cat['growth']['score']}/30** Pkt  \n"
        f"- Profitabilität: **{cat['profitability']['score']}/30** Pkt  \n"
        f"- Bilanzqualität: **{cat['balance_sheet']['score']}/20** Pkt  \n"
        f"- Bewertung: **{cat['valuation']['score']}/20** Pkt"
    )

    # 2. Unternehmensübersicht
    st.markdown("---")
    st.markdown("### Unternehmensübersicht")
    desc = company.get('description', '')
    if desc:
        st.markdown(desc[:800] + ("…" if len(desc) > 800 else ""))
    st.markdown(
        f"**Sektor:** {company.get('sector', 'N/A')} · "
        f"**Branche:** {company.get('industry', 'N/A')} · "
        f"**Land:** {company.get('country', 'N/A')}"
    )
    if company.get('employees'):
        st.markdown(f"**Mitarbeiter:** {company['employees']:,}")

    # 3. Wachstumsanalyse
    st.markdown("---")
    st.markdown("### Wachstumsanalyse")
    rev_cagr = g.get('revenue_cagr_3yr')
    eps_cagr = g.get('eps_cagr_3yr')
    if rev_cagr is not None:
        if rev_cagr >= 0.15:
            st.markdown(
                f"{company['name']} zeigt mit einem **Umsatz-CAGR von {pct(rev_cagr)}** "
                f"(3 Jahre) ein ausgezeichnetes Wachstumsprofil, das die Quality-Growth-"
                f"Benchmark von 15% übertrifft."
            )
        elif rev_cagr >= 0.08:
            st.markdown(
                f"Das Umsatzwachstum von **{pct(rev_cagr)}** CAGR (3J) ist solide, "
                f"erreicht aber noch nicht das Zielniveau von ≥15% für Premium-Quality-Growth-Werte."
            )
        else:
            st.markdown(
                f"Das Umsatzwachstum von **{pct(rev_cagr)}** CAGR (3J) ist unterhalb "
                f"der Quality-Growth-Mindestanforderung. Dies deutet auf eingeschränkte "
                f"Wachstumsdynamik hin."
            )
    if eps_cagr is not None:
        st.markdown(
            f"Der **EPS-CAGR von {pct(eps_cagr)}** (3J) "
            + ("zeigt, dass das Wachstum auch auf Gewinne durchschlägt — ein positives Zeichen."
               if eps_cagr >= 0.10 else
               "liegt hinter dem Umsatzwachstum — die Margenentwicklung verdient Aufmerksamkeit.")
        )
    if g.get('eps_consistency') is not None:
        cons = g['eps_consistency']
        st.markdown(
            f"**EPS-Konsistenz:** {pct(cons)} der betrachteten Perioden mit positivem "
            f"Gewinnwachstum — "
            + ("sehr zuverlässig." if cons >= 0.9 else
               "akzeptabel." if cons >= 0.6 else
               "unbeständig, was Risiko signalisiert.")
        )

    # 4. Profitabilitätsanalyse
    st.markdown("---")
    st.markdown("### Profitabilitätsanalyse")
    roe = p.get('roe')
    if roe is not None:
        st.markdown(
            f"Die **Eigenkapitalrendite (ROE) von {pct(roe)}** ist "
            + ("hervorragend und zeigt hohe Kapitaleffizienz."
               if roe >= 0.20 else
               "solide."
               if roe >= 0.12 else
               "unter dem Quality-Growth-Benchmark von 15%.")
        )
    nm = p.get('net_margin')
    if nm is not None:
        st.markdown(
            f"Die **Nettomarge von {pct(nm)}** "
            + ("zeigt eine ausgeprägte Preissetzungsmacht und operativen Hebel."
               if nm >= 0.15 else
               "ist im soliden Bereich."
               if nm >= 0.07 else
               "ist gering — das Unternehmen operiert in einem wettbewerbsintensiven Umfeld.")
        )
    fcf_m = p.get('fcf_margin')
    if fcf_m is not None:
        st.markdown(
            f"**Free Cash Flow Marge: {pct(fcf_m)}** — "
            + ("exzellente Geldgenerierung, Puffer für Wachstumsinvestitionen und Aktionärsrenditen."
               if fcf_m >= 0.12 else
               "positiver FCF, Basis für organisches Wachstum."
               if fcf_m >= 0 else
               "negativer FCF — das Unternehmen verbrennt Kapital, Vorsicht geboten.")
        )

    # 5. Bilanzanalyse
    st.markdown("---")
    st.markdown("### Bilanzanalyse")
    de = b.get('debt_to_equity')
    if de is not None:
        st.markdown(
            f"**Verschuldungsgrad (D/E): {x(de)}** — "
            + ("sehr konservative Finanzstruktur, hohe Krisenresistenz."
               if de < 0.3 else
               "moderate Verschuldung, finanziell stabil."
               if de < 1.0 else
               "erhöhte Verschuldung, die bei wirtschaftlichem Abschwung Risiken birgt.")
        )
    cr = b.get('current_ratio')
    if cr is not None:
        st.markdown(
            f"**Current Ratio: {cr:.2f}** — "
            + ("hohe kurzfristige Liquidität." if cr >= 2.0 else
               "ausreichende Liquidität." if cr >= 1.2 else
               "eingeschränkte Liquidität, kurzfristige Verbindlichkeiten dominant.")
        )
    fcf_hist = b.get('fcf_history', [])
    if fcf_hist:
        pos = sum(1 for f in fcf_hist if f > 0)
        st.markdown(
            f"**FCF-Konsistenz:** {pos}/{len(fcf_hist)} Jahre positiver Free Cash Flow — "
            + ("außerordentlich zuverlässig." if pos == len(fcf_hist) else
               "solide." if pos >= len(fcf_hist) * 0.75 else
               "instabil.")
        )

    # 6. Bewertungsanalyse
    st.markdown("---")
    st.markdown("### Bewertungsanalyse")
    peg = v.get('peg')
    if peg is not None and peg > 0:
        st.markdown(
            f"**PEG-Ratio: {peg:.2f}** — "
            + ("die Aktie ist attraktiv bewertet relativ zu ihrem Wachstum."
               if peg < 1.0 else
               "faire Bewertung, Wachstum ist angemessen eingepreist."
               if peg < 1.8 else
               "die Bewertung spiegelt hohe Wachstumserwartungen wider — erhöhtes Enttäuschungsrisiko.")
        )
    fpe = v.get('forward_pe')
    if fpe is not None and fpe > 0:
        st.markdown(f"**Forward-KGV: {fpe:.1f}x** — der Markt preist {fpe:.0f}-fachen Jahresgewinn ein.")
    pfcf = v.get('p_fcf')
    if pfcf is not None and pfcf > 0:
        st.markdown(
            f"**P/FCF: {pfcf:.1f}x** — "
            + ("günstig auf Free-Cash-Flow-Basis." if pfcf < 20 else
               "moderat bewertet." if pfcf < 30 else
               "teuer auf FCF-Basis.")
        )

    # 7. Fazit
    st.markdown("---")
    st.markdown("### Fazit & Investment-These")
    _write_conclusion(company, scores, g, p, b, v)

    st.markdown("---")
    st.caption(
        "⚠ **Hinweis:** Diese Analyse dient nur zu Informationszwecken und stellt keine "
        "Anlageberatung dar. Investitionsentscheidungen sollten auf eigener Recherche basieren."
    )


def _write_conclusion(company, scores, g, p, b, v):
    rec = scores['recommendation']
    total = scores['total_score']
    name = company['name']
    pct = lambda val: f"{val*100:.1f}%" if val is not None else "N/A"

    if rec == "KAUFEN":
        rev_cagr = g.get('revenue_cagr_3yr') or g.get('revenue_yoy')
        roe = p.get('roe')
        de = b.get('debt_to_equity')
        st.success(
            f"**{name}** erfüllt mit **{total}/100 Punkten** die Quality-Growth-Kriterien für "
            f"ein langfristiges Investment (5–10 Jahre). "
            + (f"Das Umsatzwachstum von {pct(rev_cagr)} CAGR, " if rev_cagr else "")
            + (f"eine ROE von {pct(roe)} " if roe else "")
            + (f"und ein konservativer Verschuldungsgrad von {de:.2f}x " if de else "")
            + "machen das Unternehmen zu einem attraktiven Quality-Growth-Kandidaten "
            "im Sinne des Fisher/Buffett-Investmentstils."
        )
    elif rec == "HALTEN":
        st.warning(
            f"**{name}** erzielt **{total}/100 Punkte** und ist ein qualitativ gutes Unternehmen, "
            "das jedoch nicht alle Quality-Growth-Kriterien vollständig erfüllt. "
            "Eine Investition ist bei einem attraktiveren Einstiegskurs oder nach Verbesserung "
            "der schwächeren Kennzahlen überlegenswert."
        )
    else:
        st.error(
            f"**{name}** erreicht nur **{total}/100 Punkte** und erfüllt die Quality-Growth-"
            "Mindestschwellen derzeit nicht. Besonders die Bereiche "
            + (", ".join([k for k, v in scores['category_scores'].items()
                          if v['score'] / v['max'] < 0.4]) or "mehrere Kategorien")
            + " weisen Schwächen auf. Das Unternehmen eignet sich nach derzeitigem Stand "
            "nicht für eine langfristige Quality-Growth-Strategie."
        )


# ── Tab 4: Export ──────────────────────────────────────────────────────────────

def _tab_export(metrics: dict, scores: dict, ticker: str):
    st.markdown("### Excel-Export")
    st.markdown(
        "Exportiere die vollständige Analyse als formatierte Excel-Datei. "
        "Die Datei enthält alle Kennzahlen, den Score-Bericht und die historischen Daten."
    )

    try:
        excel_bytes = generate_excel(metrics, scores, ticker)
        filename = f"{ticker}_QualityGrowth_{date.today().strftime('%Y%m%d')}.xlsx"
        st.download_button(
            label="📥  Excel herunterladen",
            data=excel_bytes,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )
        st.caption(f"Dateiname: `{filename}`")
    except Exception as e:
        st.error(f"Excel-Export fehlgeschlagen: {e}")

    st.markdown("---")
    st.markdown("**Die Excel-Datei enthält:**")
    st.markdown(
        "- Header mit Unternehmensdaten und Gesamtempfehlung\n"
        "- Score-Übersicht mit Kategorie-Bewertungen\n"
        "- Detailtabellen für alle 4 Kategorien (Wachstum, Profitabilität, Bilanz, Bewertung)\n"
        "- Historische Daten (Umsatz, EPS, FCF)\n"
        "- Vollständiger Analysebericht mit Stärken & Risiken"
    )


# ── Chart-Funktionen ───────────────────────────────────────────────────────────

def _create_price_chart(df, ticker: str, period: str, currency: str) -> go.Figure:
    """Candlestick-Chart für kurze Zeiträume (1T/1W), sonst Linienchart mit Füllung."""
    use_candle = period in ("1T", "1W")
    first_close = df["Close"].iloc[0]
    last_close = df["Close"].iloc[-1]
    change_pct = (last_close - first_close) / first_close * 100
    line_color = "#4caf50" if change_pct >= 0 else "#ef5350"

    fig = go.Figure()

    if use_candle:
        fig.add_trace(go.Candlestick(
            x=df["Datetime"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name=ticker,
            increasing_line_color="#4caf50",
            decreasing_line_color="#ef5350",
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df["Datetime"],
            y=df["Close"],
            mode="lines",
            line=dict(color=line_color, width=2),
            fill="tozeroy",
            fillcolor=f"rgba({'76,175,80' if change_pct >= 0 else '239,83,80'},0.12)",
            name=ticker,
        ))

    sign = "+" if change_pct >= 0 else ""
    fig.update_layout(
        title=dict(
            text=f"{ticker}  ·  {last_close:.2f} {currency}  "
                 f"<span style='color:{line_color}'>{sign}{change_pct:.2f}%</span>  ({period})",
            font=dict(size=13),
        ),
        xaxis=dict(
            rangeslider=dict(visible=False),
            showgrid=True,
            gridcolor="rgba(255,255,255,0.07)",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.07)",
            tickprefix=f"{currency} ",
        ),
        template="plotly_dark",
        height=340,
        margin=dict(l=10, r=10, t=45, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )
    return fig


def _create_radar_chart(scores: dict) -> go.Figure:
    cat = scores['category_scores']
    categories = ['Wachstum', 'Profitabilität', 'Bilanz', 'Bewertung']
    values = [
        cat['growth']['score'] / cat['growth']['max'] * 100,
        cat['profitability']['score'] / cat['profitability']['max'] * 100,
        cat['balance_sheet']['score'] / cat['balance_sheet']['max'] * 100,
        cat['valuation']['score'] / cat['valuation']['max'] * 100,
    ]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(33, 150, 243, 0.25)',
        line=dict(color='#2196F3', width=2),
        name='Score',
    ))
    fig.add_trace(go.Scatterpolar(
        r=[100, 100, 100, 100, 100],
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(255,255,255,0.03)',
        line=dict(color='rgba(255,255,255,0.1)', width=1),
        name='Maximum',
        showlegend=False,
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=9)),
            bgcolor='rgba(0,0,0,0)',
        ),
        showlegend=False,
        template='plotly_dark',
        height=300,
        margin=dict(l=40, r=40, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def _bar_chart(years, values, title, currency, colors=False) -> go.Figure:
    if colors:
        bar_colors = ['#4caf50' if v >= 0 else '#ef5350' for v in values]
    else:
        bar_colors = '#2196F3'

    fig = go.Figure(go.Bar(
        x=years,
        y=values,
        marker_color=bar_colors,
        text=[_fmt_big(v) for v in values],
        textposition='outside',
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=13)),
        xaxis_title="Jahr",
        yaxis_title=currency,
        template='plotly_dark',
        height=280,
        margin=dict(l=20, r=20, t=40, b=30),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


# ── Formatierungs-Helfer ───────────────────────────────────────────────────────

def _score_card_with_popup(term: str, score: int, max_pts: int):
    """st.metric + ℹ-Popover für eine Score-Kategorie."""
    pct = score / max_pts * 100
    delta = "stark" if pct >= 70 else ("mittel" if pct >= 45 else "schwach")
    c_metric, c_info = st.columns([5, 1])
    with c_metric:
        st.metric(term, f"{score} / {max_pts} Pkt", delta=delta)
    with c_info:
        explanation = GLOSSARY.get(term)
        if explanation:
            with st.popover("ℹ️"):
                st.markdown(f"### {term}")
                st.markdown(explanation)


def _score_delta(score: int, max_pts: int) -> str:
    pct = score / max_pts * 100
    if pct >= 70:
        return "stark"
    elif pct >= 45:
        return "mittel"
    else:
        return "schwach"


def _fmt_big(val) -> str:
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if abs(v) >= 1e12:
            return f"{v/1e12:.2f}T"
        elif abs(v) >= 1e9:
            return f"{v/1e9:.2f}B"
        elif abs(v) >= 1e6:
            return f"{v/1e6:.2f}M"
        else:
            return f"{v:,.0f}"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_consistency_pct(val) -> str:
    if val is None:
        return "N/A"
    return f"{val*100:.0f}%"


def _fmt_fcf_cons(fcf_hist: list) -> str:
    if not fcf_hist:
        return "N/A"
    pos = sum(1 for v in fcf_hist if v > 0)
    return f"{pos}/{len(fcf_hist)} Jahre"


if __name__ == "__main__":
    main()
