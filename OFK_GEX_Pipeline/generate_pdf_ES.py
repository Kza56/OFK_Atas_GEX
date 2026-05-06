"""
generate_pdf_ES.py — Génère le briefing ES en PDF fond sombre
Usage  : py generate_pdf_ES.py
Output : <DATA_DIR>/briefing_ES_YYYY-MM-DD.pdf  (DATA_DIR from config.py)
"""
import json
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

from config import ES_BRIEFING_JSON as BRIEFING_JSON, DATA_DIR as OUTPUT_DIR

BG          = colors.HexColor("#0d1117")
BG2         = colors.HexColor("#161b22")
BG3         = colors.HexColor("#1c2128")
C_WHITE     = colors.HexColor("#e6edf3")
C_BORDER    = colors.HexColor("#30363d")
C_GREEN     = colors.HexColor("#3fb950")
C_GREEN_BG  = colors.HexColor("#0d2e18")
C_RED       = colors.HexColor("#f85149")
C_RED_BG    = colors.HexColor("#2e0d0d")
C_ORANGE    = colors.HexColor("#d29922")
C_ORANGE_BG = colors.HexColor("#2e1f00")
C_YELLOW    = colors.HexColor("#e3b341")
C_BLUE      = colors.HexColor("#58a6ff")
C_PURPLE    = colors.HexColor("#bc8cff")
C_TEAL      = colors.HexColor("#39d353")

LEVEL_CFG = {
    "gamma_flip"          : ("Gamma Flip",      C_YELLOW),
    "hvl"                 : ("HVL/Trigger",     C_ORANGE),
    "vol_trigger"         : ("Vol Trigger",     C_ORANGE),
    "call_wall"           : ("Call Wall",       C_GREEN),
    "put_wall"            : ("Put Wall",        C_RED),
    "call_wall_intraday"  : ("CW intraday",     C_GREEN),
    "put_wall_intraday"   : ("PW intraday",     C_RED),
    "risk_pivot"          : ("Risk Pivot",      colors.HexColor("#ff6b6b")),
    "vanna_flip"          : ("Vanna Flip",      C_PURPLE),
    "charm_magnet"        : ("Charm Magnet",    C_BLUE),
    "max_pain"            : ("Max Pain",        C_WHITE),
    "expected_move_high"  : ("EM High",         C_TEAL),
    "expected_move_low"   : ("EM Low",          C_TEAL),
    # Phase 3 - transition levels (TanukiTrade-style)
    "c_trans_intraday"    : ("cTrans (call dom.)", colors.HexColor("#78dc8c")),
    "p_trans_intraday"    : ("pTrans (put dom.)",  colors.HexColor("#dc8c8c")),
    # Phase 4 - DEX (Delta Exposure)
    "dex_plus_intraday"   : ("D+ (delta+)",     colors.HexColor("#5cc8ff")),
    "dex_minus_intraday"  : ("D- (delta-)",     colors.HexColor("#ff82c8")),
    # 0DTE
    "max_pain_0dte"       : ("Max Pain 0DTE",   colors.HexColor("#c8c8c8")),
    "pin_strike_0dte"     : ("Pin 0DTE",        colors.HexColor("#ffa500")),
    "charm_magnet_0dte"   : ("Charm 0DTE",      colors.HexColor("#c864ff")),
    # Top OI intraday
    "top_oi_intraday_1"   : ("Top OI ID #1",    C_YELLOW),
    "top_oi_intraday_2"   : ("Top OI ID #2",    C_YELLOW),
    "top_oi_intraday_3"   : ("Top OI ID #3",    C_YELLOW),
}

def S(name, **kw):
    return ParagraphStyle(name, **kw)

def es_val(d):
    if isinstance(d, dict):
        return (d.get("es") or d.get("es_approx") or
                d.get("prix_es_approx") or d.get("prix_es") or "?")
    return d or "?"

def build_pdf_ES(briefing: dict) -> Path:
    date_str = briefing.get("date", "YYYY-MM-DD")
    output   = OUTPUT_DIR / f"briefing_ES_{date_str}.pdf"

    W_PAGE, H_PAGE = A4
    M = 12*mm
    W = W_PAGE - 2*M

    doc = SimpleDocTemplate(str(output), pagesize=A4,
        topMargin=M, bottomMargin=M, leftMargin=M, rightMargin=M)

    story = []
    PAD  = 5
    LPAD = 10

    T_H1   = S("h1",  fontName="Helvetica-Bold",       fontSize=16,  textColor=C_WHITE, alignment=TA_CENTER, leading=20)
    T_SUB  = S("sub", fontName="Helvetica",             fontSize=8.5, textColor=C_WHITE, alignment=TA_CENTER, leading=11)
    T_SECT = S("sec", fontName="Helvetica-Bold",        fontSize=7.5, textColor=C_WHITE, leading=10, spaceBefore=2, letterSpacing=1.2)
    T_IMPL = S("im",  fontName="Helvetica",             fontSize=9,   textColor=C_WHITE, leading=13)
    T_BODY = S("bd",  fontName="Helvetica",             fontSize=9,   textColor=C_WHITE, leading=13)
    T_CMPT = S("cm",  fontName="Helvetica",             fontSize=8,   textColor=C_WHITE, leading=11)
    T_PLAN = S("pl",  fontName="Helvetica-Bold",        fontSize=9,   textColor=C_WHITE, leading=12)
    T_ALT  = S("al",  fontName="Helvetica",             fontSize=8.5, textColor=C_WHITE, leading=12)
    T_RES  = S("re",  fontName="Helvetica-BoldOblique", fontSize=9.5, textColor=C_WHITE, alignment=TA_CENTER, leading=14)
    T_FOOT = S("ft",  fontName="Helvetica",             fontSize=7,   textColor=C_WHITE, alignment=TA_CENTER)

    def rs(bg, border=True):
        st = [
            ("BACKGROUND",   (0,0),(-1,-1), bg),
            ("TOPPADDING",   (0,0),(-1,-1), PAD),
            ("BOTTOMPADDING",(0,0),(-1,-1), PAD),
            ("LEFTPADDING",  (0,0),(-1,-1), LPAD),
            ("RIGHTPADDING", (0,0),(-1,-1), LPAD),
        ]
        if border:
            st.append(("LINEBELOW",(0,0),(-1,-1),0.3,C_BORDER))
        return TableStyle(st)

    heure = (briefing.get("heure_generation") or "").replace(" ET","").strip()

    # Header
    hdr = Table([[Paragraph("GEX AGENT — ES SCALPING BRIEFING", T_H1)]], colWidths=[W])
    hdr.setStyle(rs(BG2)); story.append(hdr)

    sub = Table([[Paragraph(
        f"Session RTH  .  {date_str}  .  {heure} ET  .  ES E-mini S&P500 (CME)", T_SUB
    )]], colWidths=[W])
    sub.setStyle(rs(BG3)); story.append(sub)

    acc = Table([[""]], colWidths=[W])
    acc.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),C_BLUE),
                              ("TOPPADDING",(0,0),(-1,-1),1),("BOTTOMPADDING",(0,0),(-1,-1),1)]))
    story.append(acc); story.append(Spacer(1, 2*mm))

    # MARKET CONTEXT (VIX + Macro + Data quality)
    mc = briefing.get("meta_context", {})
    vix      = mc.get("vix")
    vix_reg  = (mc.get("vix_regime") or "?").upper()
    vix_term = mc.get("vix_term") or "?"
    macro_bl = mc.get("macro_in_blackout", False)
    macro_ev = mc.get("macro_next_event") or "RAS"
    macro_mn = mc.get("macro_minutes_to_next", -1)
    data_q   = (mc.get("data_quality") or "?").upper()

    vix_str = f"{vix:.1f}" if isinstance(vix, (int, float)) else "?"
    vix_color_map = {
        "LOW":      (C_GREEN,  C_GREEN_BG),
        "NORMAL":   (C_GREEN,  C_GREEN_BG),
        "ELEVATED": (C_ORANGE, C_ORANGE_BG),
        "EXTREME":  (C_RED,    C_RED_BG),
    }
    vix_col, vix_bg = vix_color_map.get(vix_reg, (C_WHITE, BG2))
    vix_text = f"<b>VIX {vix_str}</b><br/><font size=7>{vix_reg} . {vix_term}</font>"

    if macro_bl:
        macro_text = f"<b>BLACKOUT</b><br/><font size=7>{macro_ev}</font>"
        macro_col, macro_bg = C_RED, C_RED_BG
    elif isinstance(macro_mn, (int, float)) and 0 < macro_mn <= 30:
        macro_text = f"<b>MACRO {int(macro_mn)}min</b><br/><font size=7>{macro_ev}</font>"
        macro_col, macro_bg = C_RED, C_RED_BG
    elif isinstance(macro_mn, (int, float)) and 30 < macro_mn <= 60:
        macro_text = f"<b>MACRO {int(macro_mn)}min</b><br/><font size=7>{macro_ev}</font>"
        macro_col, macro_bg = C_ORANGE, C_ORANGE_BG
    else:
        macro_text = f"<b>MACRO RAS</b><br/><font size=7>{macro_ev}</font>"
        macro_col, macro_bg = C_GREEN, C_GREEN_BG

    data_color_map = {
        "OK":      (C_GREEN,  C_GREEN_BG),
        "PARTIAL": (C_ORANGE, C_ORANGE_BG),
        "ERROR":   (C_RED,    C_RED_BG),
    }
    data_col, data_bg = data_color_map.get(data_q, (C_WHITE, BG2))
    data_text = f"<b>DATA {data_q}</b>"

    story.append(Paragraph("MARKET CONTEXT", T_SECT))
    ctx_row = [
        Paragraph(vix_text,
            S("vix",fontName="Helvetica-Bold",fontSize=11,textColor=vix_col,alignment=TA_CENTER,leading=14)),
        Paragraph(macro_text,
            S("mac",fontName="Helvetica-Bold",fontSize=11,textColor=macro_col,alignment=TA_CENTER,leading=14)),
        Paragraph(data_text,
            S("dq", fontName="Helvetica-Bold",fontSize=11,textColor=data_col,alignment=TA_CENTER,leading=14)),
    ]
    ctx_t = Table([ctx_row], colWidths=[W*0.34, W*0.34, W*0.32])
    ctx_t.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(0,0), vix_bg),
        ("BACKGROUND",   (1,0),(1,0), macro_bg),
        ("BACKGROUND",   (2,0),(2,0), data_bg),
        ("TOPPADDING",   (0,0),(-1,-1), 6),("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING",  (0,0),(-1,-1), 8),("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",    (0,0),(-1,-1), 0.3, C_BORDER),
    ]))
    story.append(ctx_t)

    interp = mc.get("interpretation") or ""
    if interp:
        interp_t = Table([[Paragraph(interp, T_BODY)]], colWidths=[W])
        interp_t.setStyle(rs(BG2))
        story.append(interp_t)
    story.append(Spacer(1, 2*mm))

    # Regime
    r = briefing.get("regime", {})
    gex_label  = (r.get("gex_label") or r.get("label") or "?").upper()
    net_gex    = r.get("net_gex") or 0
    gex_B      = r.get("total_gex_B") or (f"{net_gex/1e9:.2f}" if net_gex else "?")
    impl       = r.get("implication_vol") or r.get("implication") or ""
    regime_pos = gex_label in ("POSITIVE", "POSITIF")
    regime_bg  = C_GREEN_BG if regime_pos else C_RED_BG
    regime_col = C_GREEN    if regime_pos else C_RED

    story.append(Paragraph("GEX REGIME", T_SECT))
    reg = Table([[
        Paragraph(f"<b>GEX REGIME : {gex_label}</b>",
            S("rl",fontName="Helvetica-Bold",fontSize=13,textColor=regime_col,leading=17)),
        Paragraph(f"<b>{gex_B}B</b>",
            S("rb",fontName="Helvetica-Bold",fontSize=13,textColor=regime_col,alignment=TA_RIGHT,leading=17)),
    ]], colWidths=[W*0.7, W*0.3])
    reg.setStyle(rs(regime_bg)); story.append(reg)
    impl_t = Table([[Paragraph(impl, T_IMPL)]], colWidths=[W])
    impl_t.setStyle(rs(BG2)); story.append(impl_t)
    story.append(Spacer(1, 2*mm))

    # Biais
    b = briefing.get("biais", briefing.get("bias", {}))
    direction  = (b.get("direction") or "?").upper()
    conviction = b.get("conviction") or "?"
    raison     = b.get("raison") or b.get("reason") or ""
    biais_bg   = {"BULLISH":C_GREEN_BG,"BEARISH":C_RED_BG,"BULLISH":C_GREEN_BG,"BEARISH":C_RED_BG,"NEUTRAL":C_ORANGE_BG,"NEUTRAL":C_ORANGE_BG}.get(direction,C_ORANGE_BG)
    biais_col  = {"BULLISH":C_GREEN,   "BEARISH":C_RED,   "BULLISH":C_GREEN,   "BEARISH":C_RED,   "NEUTRAL":C_ORANGE,   "NEUTRAL":C_ORANGE  }.get(direction,C_ORANGE)

    story.append(Paragraph("DAILY BIAS", T_SECT))
    bt = Table([[
        Paragraph(f"<b>BIAIS : {direction}</b>",
            S("bl",fontName="Helvetica-Bold",fontSize=13,textColor=biais_col,leading=17)),
        Paragraph(f"conviction: <b>{conviction}</b>",
            S("bc",fontName="Helvetica",fontSize=9,textColor=biais_col,alignment=TA_RIGHT,leading=17)),
    ]], colWidths=[W*0.6, W*0.4])
    bt.setStyle(rs(biais_bg)); story.append(bt)
    rt = Table([[Paragraph(raison, T_BODY)]], colWidths=[W])
    rt.setStyle(rs(BG2)); story.append(rt)
    story.append(Spacer(1, 2*mm))

    # Niveaux
    story.append(Paragraph("KEY LEVELS", T_SECT))
    hdr_row = [
        Paragraph("<b>Type</b>",                 S("nh1",fontName="Helvetica-Bold",fontSize=7.5,textColor=C_WHITE)),
        Paragraph("<b>ES</b>",                   S("nh2",fontName="Helvetica-Bold",fontSize=7.5,textColor=C_WHITE,alignment=TA_CENTER)),
        Paragraph("<b>Dist.</b>",                S("nh3",fontName="Helvetica-Bold",fontSize=7.5,textColor=C_WHITE,alignment=TA_CENTER)),
        Paragraph("<b>Comportement dealers</b>", S("nh4",fontName="Helvetica-Bold",fontSize=7.5,textColor=C_WHITE)),
    ]
    rows = [hdr_row]
    levels_key = "niveaux" if "niveaux" in briefing else "levels"
    for i, n in enumerate(briefing.get(levels_key, [])):
        ntype = n.get("type", "?")
        prix  = (n.get("prix_es_approx") or n.get("prix_es") or
                 n.get("nq_price") or n.get("es_price") or "?")
        dist  = n.get("distance_spot_pct") or n.get("distance_pct") or 0
        compt = n.get("comportement_dealers") or n.get("dealer_behavior") or ""
        label, col = LEVEL_CFG.get(ntype, (ntype, C_WHITE))
        dist_str = f"{dist:+.2f}%" if isinstance(dist,(int,float)) else "?"
        dist_col = (C_GREEN if isinstance(dist,(int,float)) and dist > 0
                    else C_RED if isinstance(dist,(int,float)) and dist < 0
                    else C_WHITE)
        rows.append([
            Paragraph(f"<b>{label}</b>",
                S(f"lt{i}",fontName="Helvetica-Bold",fontSize=9,textColor=col,leading=12)),
            Paragraph(f"<b>{prix}</b>",
                S(f"es{i}",fontName="Helvetica-Bold",fontSize=11,textColor=C_WHITE,alignment=TA_CENTER,leading=14)),
            Paragraph(dist_str,
                S(f"dd{i}",fontName="Helvetica-Bold",fontSize=9,textColor=dist_col,alignment=TA_CENTER,leading=12)),
            Paragraph(compt, T_CMPT),
        ])

    niv = Table(rows, colWidths=[W*0.14,W*0.10,W*0.09,W*0.67], repeatRows=1)
    ts = [
        ("BACKGROUND",(0,0),(-1,0),BG),
        ("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4),
        ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),6),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
        ("LINEBELOW",(0,0),(-1,-1),0.3,C_BORDER),
    ]
    for i in range(1, len(rows)):
        ts.append(("BACKGROUND",(0,i),(-1,i), BG2 if (i-1)%2==0 else BG3))
    niv.setStyle(TableStyle(ts)); story.append(niv)
    story.append(Spacer(1, 2*mm))

    # Plan RTH
    p = briefing.get("plan_rth", briefing.get("rth_plan", {}))
    za = es_val(p.get("buy_zone_es")             or p.get("buy_zone_es")             or p.get("buy_zone_nq"))
    zv = es_val(p.get("sell_zone_es")             or p.get("sell_zone_es")            or p.get("sell_zone_nq"))
    ih = es_val(p.get("bullish_invalidation_es") or p.get("bullish_invalidation_es") or p.get("bullish_invalidation_nq"))
    ib = es_val(p.get("bearish_invalidation_es") or p.get("bearish_invalidation_es") or p.get("bearish_invalidation_nq"))

    story.append(Paragraph("RTH PLAN", T_SECT))
    plan_items = [
        ("Buy zone",             za, C_GREEN),
        ("Sell zone",             zv, C_RED),
        ("Bullish invalidation", ih, C_ORANGE),
        ("Bearish invalidation", ib, C_ORANGE),
    ]
    plan_data = []
    for lbl, val, col in plan_items:
        plan_data.append([
            Paragraph(lbl, T_PLAN),
            Paragraph(f"<b>ES {val}</b>",
                S(f"pv{lbl}",fontName="Helvetica-Bold",fontSize=10,textColor=col,alignment=TA_LEFT,leading=13)),
        ])
    plan_t = Table(plan_data, colWidths=[W*0.5, W*0.5])
    plan_t.setStyle(TableStyle([
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[BG2,BG3]),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
        ("LEFTPADDING",(0,0),(-1,-1),LPAD),("RIGHTPADDING",(0,0),(-1,-1),LPAD),
        ("LINEBELOW",(0,0),(-1,-1),0.3,C_BORDER),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ]))
    story.append(plan_t); story.append(Spacer(1, 2*mm))

    # Alertes
    alertes_key = "alertes_risque" if "alertes_risque" in briefing else "risk_alerts"
    alertes = briefing.get(alertes_key, [])
    if alertes:
        story.append(Paragraph("RISK ALERTS", T_SECT))
        alert_data = []
        for i, a in enumerate(alertes, 1):
            alert_data.append([
                Paragraph(f"<b>{i}</b>",
                    S(f"ai{i}",fontName="Helvetica-Bold",fontSize=10,textColor=C_WHITE,alignment=TA_CENTER,leading=13)),
                Paragraph(a, T_ALT),
            ])
        at = Table(alert_data, colWidths=[W*0.05, W*0.95])
        at.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,-1),C_RED_BG),
            ("ROWBACKGROUNDS",(1,0),(1,-1),[BG2,BG3]),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(-1,-1),8),("RIGHTPADDING",(0,0),(-1,-1),10),
            ("LINEBELOW",(0,0),(-1,-1),0.3,C_BORDER),("VALIGN",(0,0),(-1,-1),"TOP"),
        ]))
        story.append(at); story.append(Spacer(1, 2*mm))

    # Résumé
    resume = briefing.get("resume_une_ligne") or briefing.get("one_liner") or ""
    if resume:
        res = Table([[Paragraph(f">>  {resume}", T_RES)]], colWidths=[W])
        res.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,-1),C_BLUE),
            ("TOPPADDING",(0,0),(-1,-1),8),("BOTTOMPADDING",(0,0),(-1,-1),8),
            ("LEFTPADDING",(0,0),(-1,-1),14),
        ]))
        story.append(res); story.append(Spacer(1, 2*mm))

    # Footer
    story.append(HRFlowable(width=W, thickness=0.3, color=C_BORDER))
    story.append(Paragraph(
        "GEX Agent ES  |  CME ES Options + CBOE SPY  |  Personal use only — not financial advice",
        T_FOOT))


    # Auto-cleanup: delete previous ES PDFs for the same contract
    for old_pdf in OUTPUT_DIR.glob("briefing_ES_*.pdf"):
        if old_pdf != output:
            try:
                old_pdf.unlink()
            except Exception:
                pass

    def on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BG)
        canvas.rect(0,0,W_PAGE,H_PAGE,fill=1,stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    return output


if __name__ == "__main__":
    print("Loading ES briefing...")
    briefing = json.loads(BRIEFING_JSON.read_text(encoding="utf-8"))
    print("Generating PDF...")
    path = build_pdf_ES(briefing)
    print(f"PDF generated: {path}")
