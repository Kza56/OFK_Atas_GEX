#!/usr/bin/env python3
"""
cme_ES_browser_fetch.py  —  Options Greeks Exposure fetcher ES E-mini S&P500 (CME via Playwright)

Endpoints CME découverts via Network tab:
  1. /CmeWS/mvc/Volume/TradeDates?exchange=CBOT
  2. /CmeWS/mvc/Volume/Options/Expirations?productid=133&tradedate={date}
  3. /CmeWS/mvc/Volume/Options/Details?productid={pid}&tradedate={date}&expirationcode={code}&reporttype=F
  4. /CmeWS/mvc/Settlements/Options/Settlements/{pid}/OOF?...

Niveaux calculés (inspirés SpotGamma):
  GEX  = Gamma Exposure       → Σ OI × gamma × mult × S²  (pinning vs amplification)
  VEX  = Vanna Exposure       → Σ OI × vanna × mult × S   (flux IV-driven)
  CEX  = Charm Exposure       → Σ OI × charm × mult       (flux time-driven)
  DEX  = Delta Exposure       → Σ OI × delta × mult × S   (directionnel)

  Niveaux dérivés:
  - Gamma Flip (Zero Gamma)  : GEX cumulé change de signe
  - Volatility Trigger       : strike le plus proche du spot avec GEX > 0
  - Call Wall / Put Wall     : strikes à GEX max positif / max négatif
  - Risk Pivot               : premier strike sous spot où GEX devient très négatif
  - Vanna Flip               : strike où VEX change de signe
  - Charm Magnet             : strike avec |CEX| maximal (aimant de fin de session)

IDs CME ES E-mini S&P 500:
  Futures (spot)  : 133
  Standard (Eur.) : 136
  EOM + American  : 138
  Monday          : 8292
  Tuesday         : 10132
  Wednesday       : 8227
  Thursday        : 10137
  Friday          : 2915
  Multiplicateur  : $50/point

Usage:
  python cme_ES_browser_fetch.py
  python cme_ES_browser_fetch.py --spot 5500
  python cme_ES_browser_fetch.py --test-expiry
"""

import argparse, json, logging, math, sys, time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from playwright.sync_api import sync_playwright

logging.basicConfig(level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

CME_BASE             = "https://www.cmegroup.com"
CME_MAIN_PAGE        = CME_BASE + "/markets/equities/sp/e-mini-sandp500.quotes.options.html#optionProductId=136"
CME_QUOTES_URL       = CME_BASE + "/markets/equities/sp/e-mini-sandp500.quotes.html"
CME_SETTLEMENTS_BASE = CME_BASE + "/markets/equities/sp/e-mini-sandp500.settlements.options.html"
CME_VOLUME_BASE      = CME_BASE + "/markets/equities/sp/e-mini-sandp500.volume.options.html"

# Pages settlements par type (dans l'ordre du menu CME)
# Standard=136, EOM+American=138, Mon=8292, Tue=10132, Wed=8227, Thu=10137, Fri=2915
CME_SETTLEMENTS_PAGES = {
    136  : CME_SETTLEMENTS_BASE + "#optionProductId=136",
    138  : CME_SETTLEMENTS_BASE + "#optionProductId=138",
    8292 : CME_SETTLEMENTS_BASE + "#optionProductId=8292",
    10132: CME_SETTLEMENTS_BASE + "#optionProductId=10132",
    8227 : CME_SETTLEMENTS_BASE + "#optionProductId=8227",
    10137: CME_SETTLEMENTS_BASE + "#optionProductId=10137",
    2915 : CME_SETTLEMENTS_BASE + "#optionProductId=2915",
}

# Pages volume par PID
CME_VOLUME_PAGES = {
    136  : CME_VOLUME_BASE + "#optionProductId=136",
    138  : CME_VOLUME_BASE + "#optionProductId=138",
    8292 : CME_VOLUME_BASE + "#optionProductId=8292",
    10132: CME_VOLUME_BASE + "#optionProductId=10132",
    8227 : CME_VOLUME_BASE + "#optionProductId=8227",
    10137: CME_VOLUME_BASE + "#optionProductId=10137",
    2915 : CME_VOLUME_BASE + "#optionProductId=2915",
}

# PIDs weeklies enfants (week 2/3/4) — à compléter si CME en expose
# Pour l'instant on suppose un seul PID par jour (à vérifier en prod)
CME_SETTLEMENTS_PARENT = {
    # Ajouter ici les PIDs week2/3/4 si découverts via Network tab
    # ex: 2916: 2915,  # Friday week 2
}

ES_FUTURES_ID  = 133   # ID futures ES pour le spot price
ES_MULTIPLIER  = 50    # $50 par point ES
MIN_OI         = 5     # OI minimum par strike pour inclure

# ── Chemin de sortie JSON (centralisé dans config.py, override via ES_GEX_JSON env var) ──
from config import ES_GEX_JSON as GEX_OUTPUT_PATH


# ═══════════════════════════════════════════════════════════════════════════════
# Black-Scholes Greeks (identique NQ)
# ═══════════════════════════════════════════════════════════════════════════════

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def _d1d2(S, K, T, r, sigma) -> Tuple[float, float]:
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / sq
    return d1, d1 - sq

def bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
              is_call: bool) -> Dict[str, float]:
    """Calcule delta, gamma, vanna, charm pour une option BS."""
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {'delta':0, 'gamma':0, 'vanna':0, 'charm':0}
    try:
        d1, d2 = _d1d2(S, K, T, r, sigma)
        pdf_d1 = _norm_pdf(d1)
        sqrt_T = math.sqrt(T)

        delta = _norm_cdf(d1) if is_call else _norm_cdf(d1) - 1.0
        gamma = pdf_d1 / (S * sigma * sqrt_T)
        vanna = -pdf_d1 * d2 / sigma
        charm_call = -pdf_d1 * (2*r*T - d2*sigma*sqrt_T) / (2*T*sigma*sqrt_T)
        charm = charm_call if is_call else charm_call + r * math.exp(-r * T) * _norm_cdf(-d2)

        return {'delta': delta, 'gamma': gamma, 'vanna': vanna, 'charm': charm}
    except Exception:
        return {'delta':0, 'gamma':0, 'vanna':0, 'charm':0}


def implied_vol(option_price: float, S: float, K: float, T: float,
                r: float, is_call: bool) -> float:
    """IV par bisection (60 itérations). Retourne 0.20 si non convergé."""
    if option_price <= 0 or T <= 0:
        return 0.20
    try:
        lo, hi = 1e-4, 5.0
        for _ in range(60):
            mid = (lo + hi) / 2
            d1, d2 = _d1d2(S, K, T, r, mid)
            disc = math.exp(-r * T)
            price = S*_norm_cdf(d1) - K*disc*_norm_cdf(d2) if is_call \
                    else K*disc*_norm_cdf(-d2) - S*_norm_cdf(-d1)
            if price < option_price: lo = mid
            else: hi = mid
        return (lo + hi) / 2
    except Exception:
        return 0.20


# ═══════════════════════════════════════════════════════════════════════════════
# Session Playwright
# ═══════════════════════════════════════════════════════════════════════════════

class CMEBrowserSession:
    def __init__(self, headless: bool = False):
        self._headless = headless
        self._pw = self._browser = self._page = None

    def __enter__(self):
        self._pw      = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self._headless,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-http2']
        )
        ctx = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )
        self._page = ctx.new_page()
        log.info("Initialisation navigateur CME ES...")
        for attempt in range(3):
            try:
                self._page.goto(CME_MAIN_PAGE, wait_until='domcontentloaded', timeout=30000)
                time.sleep(4)
                log.info("Navigateur CME ES prêt")
                break
            except Exception as e:
                log.warning(f"goto tentative {attempt+1}/3: {e}")
                time.sleep(2)
        return self

    def __exit__(self, *_):
        try:
            if self._browser: self._browser.close()
            if self._pw:      self._pw.stop()
        except Exception:
            pass

    def fetch_json(self, url: str) -> Optional[Any]:
        result = self._page.evaluate("""
            async (url) => {
                try {
                    const r = await fetch(url, {
                        credentials: 'include',
                        headers: {'Accept': 'application/json, text/plain, */*'}
                    });
                    const text = await r.text();
                    return {status: r.status, body: text};
                } catch(e) { return {status: 0, error: e.toString()}; }
            }
        """, url)
        status = result.get('status', 0)
        body   = result.get('body', '')
        if status != 200 or not body or body[0] not in ('{', '['):
            if status != 200:
                log.debug(f"  HTTP {status}: {url[-60:]}")
            return None
        try:
            return json.loads(body)
        except Exception:
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# Fetchers CME
# ═══════════════════════════════════════════════════════════════════════════════

def get_latest_trade_date(session: CMEBrowserSession) -> str:
    url  = f"{CME_BASE}/CmeWS/mvc/Volume/TradeDates?exchange=CBOT&isProtected"
    data = session.fetch_json(url)
    if data and isinstance(data, list) and data:
        td = data[0].get('tradeDate', '')
        if td:
            log.info(f"  Trade date: {td}")
            return td
    # Fallback: dernier jour de bourse
    today = date.today()
    for delta in range(1, 5):
        d = today - timedelta(days=delta)
        if d.weekday() < 5:
            return d.strftime('%Y%m%d')
    return today.strftime('%Y%m%d')


def get_es_spot_price(session: CMEBrowserSession) -> float:
    """Récupère le dernier prix du ES futures depuis CME."""
    _t = int(time.time() * 1000)
    endpoints = [
        CME_BASE + f"/CmeWS/mvc/quotes/v2/{ES_FUTURES_ID}?isProtected&_t={_t}",
        CME_BASE + f"/CmeWS/mvc/quotes/v2/contracts-by-number?isProtected&_t={_t}",
    ]

    for endpoint in endpoints:
        result = session._page.evaluate("""
            async (url) => {
                try {
                    const r = await fetch(url, {
                        credentials: 'include',
                        headers: {'Accept': 'application/json, text/plain, */*'}
                    });
                    const text = await r.text();
                    return {status: r.status, body: text};
                } catch(e) { return {status: 0, error: e.toString()}; }
            }
        """, endpoint)

        status = result.get('status', 0)
        body   = result.get('body', '')
        short  = endpoint.split('?')[0].split('/')[-1]
        log.info(f"  QUOTE [{short}] HTTP {status}  body: {body[:120]}")

        if status == 200 and body and body[0] in ('{', '['):
            try:
                data = json.loads(body)
                candidates = []
                if isinstance(data, dict):
                    for key in ('quotes', 'data', 'rows', 'results'):
                        if key in data and isinstance(data[key], list):
                            candidates = data[key]
                            break
                    if not candidates:
                        candidates = [data]
                elif isinstance(data, list):
                    candidates = data

                for q in candidates:
                    if not isinstance(q, dict): continue
                    for field in ('last', 'lastPrice', 'close', 'settlePrice',
                                  'priorSettle', 'priorSettlement', 'settlement'):
                        v = str(q.get(field, '') or '').replace(',', '').strip()
                        if v and v not in ('-', '0', 'N/A', ''):
                            try:
                                price = float(v)
                                if 3000 < price < 10000:  # plage valide pour ES
                                    log.info(f"  ✓ Spot ES: {price:.2f}  (champ={field})")
                                    return price
                            except Exception:
                                pass
            except Exception as e:
                log.warning(f"  Erreur parse: {e}")

    log.warning("  get_es_spot_price: aucun endpoint valide")
    return 0.0


def get_all_expirations(session: CMEBrowserSession, trade_date: str) -> List[Dict]:
    url  = (f"{CME_BASE}/CmeWS/mvc/Volume/Options/Expirations"
            f"?productid={ES_FUTURES_ID}&tradedate={trade_date}&isProtected")
    data = session.fetch_json(url)
    if not data or not isinstance(data, list):
        log.warning(f"  Expirations: réponse vide ou invalide")
        return []
    results = []
    for group in data:
        if not isinstance(group, dict): continue
        for exp in group.get('expirations', []):
            if not isinstance(exp, dict): continue
            pid = exp.get('productId', 0)
            ec  = exp.get('expirationCode', '')
            exp_obj = exp.get('expiration', {})
            code6   = exp_obj.get('code', '') or exp_obj.get('tickerCode', '')
            key     = exp.get('key', {})
            if pid and ec:
                results.append({
                    'productId'     : pid,
                    'expirationCode': ec,
                    'code6'         : code6,
                    'key'           : key,
                    'label'         : exp.get('label', ''),
                    'isWeekly'      : group.get('weekly', False),
                })
    log.info(f"  {len(results)} expirations ES")
    return results


def get_oi_by_strike(session: CMEBrowserSession, pid: int,
                     trade_date: str, exp_code: str,
                     code6: str = '',
                     contract_id: str = '',
                     trade_date_fmt: str = '',
                     dte: int = None) -> Dict[float, Dict]:
    """Récupère l'OI par strike via l'endpoint Settlements."""
    ts  = int(time.time() * 1000)
    url = (f"{CME_BASE}/CmeWS/mvc/Settlements/Options/Settlements"
           f"/{pid}/OOF"
           f"?strategy=DEFAULT&optionProductId={pid}"
           f"&monthYear={contract_id}"
           f"&optionExpiration={pid}-{exp_code}"
           f"&tradeDate={trade_date_fmt}"
           f"&pageSize=500&isProtected&_t={ts}")
    log.info(f"    URL: {url}")
    data = session.fetch_json(url)
    if not data:
        log.warning(f"    OI/settle [{pid}/{exp_code}] → None")
        return {}

    def _f(v):
        if v in (None, '-', '', 'N/A'): return 0.0
        try: return float(str(v).replace(',','').rstrip('B').rstrip('A'))
        except Exception: return 0.0

    by_strike = defaultdict(lambda: {'c_oi': 0.0, 'p_oi': 0.0, 'c_settle': 0.0, 'p_settle': 0.0})
    rows = data.get('settlements', []) if isinstance(data, dict) else []
    for row in rows:
        if not isinstance(row, dict): continue
        K = _f(row.get('strike') or 0)
        if K <= 0: continue
        settle = _f(row.get('settle') or 0)
        oi     = _f(row.get('openInterest') or row.get('oi') or 0)
        is_put = 'put' in str(row.get('type', '')).lower()
        if is_put:
            by_strike[K]['p_settle'] = settle
            by_strike[K]['p_oi']     = oi
        else:
            by_strike[K]['c_settle'] = settle
            by_strike[K]['c_oi']     = oi

    n = len(by_strike)
    log.info(f"    OI/settle [{pid}/{exp_code}] → {n} strikes")

    # Retry avec date du jour pour les expirations imminentes (0DTE/1DTE)
    if n == 0 and dte is not None and dte <= 2:
        today_fmt = date.today().strftime('%m/%d/%Y')
        if today_fmt != trade_date_fmt:
            log.info(f"    [{pid}/{exp_code}] dte={dte} → retry avec date du jour {today_fmt}")
            url2 = (f"{CME_BASE}/CmeWS/mvc/Settlements/Options/Settlements"
                    f"/{pid}/OOF?strategy=DEFAULT&optionProductId={pid}"
                    f"&monthYear={contract_id}&optionExpiration={pid}-{exp_code}"
                    f"&tradeDate={today_fmt}&pageSize=500&isProtected&_t={int(time.time()*1000)}")
            try:
                resp2 = session._page.evaluate("(url) => fetch(url).then(r=>r.json())", url2)
                rows2 = resp2.get('settlements', []) if isinstance(resp2, dict) else []
                for row in rows2:
                    if not isinstance(row, dict): continue
                    K = _f(row.get('strike') or 0)
                    if K <= 0: continue
                    settle = _f(row.get('settle') or 0)
                    oi     = _f(row.get('openInterest') or 0)
                    is_put = 'put' in str(row.get('type', '')).lower()
                    if is_put:
                        by_strike[K]['p_settle'] = settle
                        by_strike[K]['p_oi']     = oi
                    else:
                        by_strike[K]['c_settle'] = settle
                        by_strike[K]['c_oi']     = oi
                n = len(by_strike)
                if n > 0:
                    log.info(f"    [{pid}/{exp_code}] → {n} strikes (retry today)")
            except Exception as e:
                log.debug(f"    retry today échoué: {e}")

    return dict(by_strike)


def _calc_dte(exp_code: str) -> int:
    """DTE depuis code expiry ex: 'K26' → 3ème vendredi de mai 2026."""
    month_map = {'F':1,'G':2,'H':3,'J':4,'K':5,'M':6,
                 'N':7,'Q':8,'U':9,'V':10,'X':11,'Z':12}
    try:
        import calendar
        m  = month_map.get(exp_code[0], 3)
        y  = 2000 + int(exp_code[1:])
        c  = calendar.monthcalendar(y, m)
        fs = [w[4] for w in c if w[4] != 0]
        exp_date = date(y, m, fs[2] if len(fs) >= 3 else fs[-1])
        return max(0, (exp_date - date.today()).days)
    except Exception:
        return 30


# Cache volume pages
_volume_page_cache: Dict[int, bool] = {}

# PIDs standard (settlements 24h/24, Volume/Details intraday) vs weeklies (Volume/Details only)
STANDARD_PIDS = {136, 138}                              # European Standard + EOM American
WEEKLY_PIDS   = {8292, 10132, 8227, 10137, 2915}        # Mon, Tue, Wed, Thu, Fri


def get_oi_standard_with_intraday(session: CMEBrowserSession, pid: int,
                                   trade_date: str, exp_code: str, *,
                                   contract_id: str, trade_date_fmt: str,
                                   dte: int, estimated_iv: float = 0.18) -> Dict[float, Dict]:
    """
    STANDARD_PIDS (ex: 136, 138) : combine
      - OI intraday via Volume/Options/Details?reporttype=F   (mis à jour pendant la session)
      - Settle prices via Settlements/Options/Settlements/{pid}/OOF  (utilisés pour l'IV inversion)

    Si Volume/Details est vide (marché fermé / off-hours), fallback total sur Settlements
    (qui contient aussi l'OI EOD veille).
    """
    intraday_oi = get_oi_volume_details(session, pid, trade_date, exp_code,
                                         estimated_iv=estimated_iv)
    settle_data = get_oi_by_strike(session, pid, trade_date, exp_code,
                                    contract_id=contract_id,
                                    trade_date_fmt=trade_date_fmt,
                                    dte=dte)

    if not intraday_oi:
        log.info(f"    [intraday→fallback] {pid}/{exp_code}: Volume/Details vide → Settlements seul")
        return settle_data

    merged: Dict[float, Dict] = {}
    all_strikes = set(intraday_oi.keys()) | set(settle_data.keys())
    for K in all_strikes:
        iod = intraday_oi.get(K, {})
        sed = settle_data.get(K, {})
        merged[K] = {
            'c_oi'    : iod.get('c_oi', 0) or sed.get('c_oi', 0),
            'p_oi'    : iod.get('p_oi', 0) or sed.get('p_oi', 0),
            'c_settle': sed.get('c_settle', 0),
            'p_settle': sed.get('p_settle', 0),
        }
    log.info(f"    [intraday merge] {pid}/{exp_code}: "
             f"intraday OI={len(intraday_oi)} + settle EOD={len(settle_data)} → merged={len(merged)}")
    return merged


def get_oi_volume_details(session: CMEBrowserSession, pid: int,
                          trade_date: str, exp_code: str,
                          estimated_iv: float = 0.18) -> Dict[float, Dict]:
    """Récupère l'OI par strike via Volume/Options/Details."""
    def _f(v):
        try: return float(str(v).replace(',','').strip()) if v not in (None,'-','') else 0.0
        except Exception: return 0.0

    page_pid   = CME_SETTLEMENTS_PARENT.get(pid, pid)
    volume_url = CME_VOLUME_PAGES.get(page_pid)

    if volume_url and page_pid not in _volume_page_cache:
        log.info(f"    [Page volume] Navigation pid={page_pid}")
        try:
            session._page.goto(volume_url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(2)
            _volume_page_cache[page_pid] = True
        except Exception as e:
            log.warning(f"    [Page volume] goto échoué: {e}")

    ts  = int(time.time() * 1000)
    url = (f"{CME_BASE}/CmeWS/mvc/Volume/Options/Details"
           f"?productid={pid}&tradedate={trade_date}"
           f"&expirationcode={exp_code}&reporttype=F"
           f"&isProtected&_t={ts}")
    data = session.fetch_json(url)

    rows = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get('rows', data.get('items', data.get('settlements', [])))

    if not rows:
        log.info(f"    [Volume/Details] {pid}/{exp_code} → 0 strikes")
        return {}

    by_strike: Dict[float, Dict] = defaultdict(lambda: {
        'c_oi': 0.0, 'p_oi': 0.0,
        'c_settle': 0.0, 'p_settle': 0.0,
        'iv': estimated_iv,
    })

    for row in rows:
        if not isinstance(row, dict): continue
        K = _f(row.get('strikePrice') or row.get('strike') or 0)
        if K <= 0: continue
        oi       = _f(row.get('openInterest') or row.get('oi') or 0)
        opt_type = str(row.get('optionType') or row.get('type') or '').lower()
        if 'put' in opt_type:
            by_strike[K]['p_oi'] = oi
        else:
            by_strike[K]['c_oi'] = oi

    log.info(f"    [Volume/Details] {pid}/{exp_code} → {len(by_strike)} strikes")
    return dict(by_strike)


# ═══════════════════════════════════════════════════════════════════════════════
# Calcul des expositions Greeks
# ═══════════════════════════════════════════════════════════════════════════════

def compute_greek_exposures(
        oi_data: Dict[float, Dict],
        settle_data: Dict[float, Dict],
        dte: int,
        spot: float,
        r: float = 0.045,
) -> Dict[float, Dict]:
    """Pour chaque strike: calcule GEX, VEX, CEX, DEX."""
    T = max(dte / 365.0, 0.5 / 365)
    S = spot if spot > 0 else 5000.0
    exposures = {}

    for K, oi in oi_data.items():
        c_oi = oi.get('c_oi', 0)
        p_oi = oi.get('p_oi', 0)
        if c_oi + p_oi < MIN_OI:
            continue

        s_data  = settle_data.get(K, {})
        c_price = s_data.get('c_settle', 0)
        p_price = s_data.get('p_settle', 0)

        c_iv = implied_vol(c_price, S, K, T, r, True)  if c_price > 0 else 0.18
        p_iv = implied_vol(p_price, S, K, T, r, False) if p_price > 0 else 0.18

        c_g = bs_greeks(S, K, T, r, c_iv, True)
        p_g = bs_greeks(S, K, T, r, p_iv, False)

        S2   = S * S
        mult = ES_MULTIPLIER

        gex = (c_oi * c_g['gamma'] - p_oi * p_g['gamma']) * mult * S2
        vex = (c_oi * c_g['vanna'] + p_oi * abs(p_g['vanna'])) * mult * S
        cex = (c_oi * c_g['charm'] + p_oi * p_g['charm']) * mult
        dex = (c_oi * c_g['delta'] + p_oi * p_g['delta']) * mult * S

        exposures[K] = {
            'gex': gex, 'vex': vex, 'cex': cex, 'dex': dex,
            'c_oi': c_oi, 'p_oi': p_oi,
            'c_iv': round(c_iv, 4), 'p_iv': round(p_iv, 4),
            'c_delta': c_g['delta'], 'p_delta': p_g['delta'],
        }

    return exposures


# ═══════════════════════════════════════════════════════════════════════════════
# Agrégation des niveaux
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_atm_iv(exposures: Dict[float, Dict], spot: float) -> float:
    """ATM IV (annualized) for one expiration: avg of c_iv and p_iv at the
    strike closest to spot. Returns 0.0 if no usable IV is found."""
    if not exposures or spot <= 0:
        return 0.0
    atm_strike = min(exposures.keys(), key=lambda k: abs(k - spot))
    ex = exposures[atm_strike]
    c_iv = ex.get('c_iv', 0) or 0
    p_iv = ex.get('p_iv', 0) or 0
    if c_iv > 0 and p_iv > 0:
        return (c_iv + p_iv) / 2
    return c_iv or p_iv or 0.0


def _compute_term_structure(iv_by_dte: Dict[int, float]) -> Dict[str, Any]:
    """Term-structure metrics from per-DTE ATM IVs.
    Returns iv_back_dte, iv_back, term_slope, term_regime
    (contango / backwardation / flat / unknown)."""
    if not iv_by_dte:
        return {'iv_back_dte': 0, 'iv_back': 0.0, 'term_slope': 0.0, 'term_regime': 'unknown'}
    valid = {d: iv for d, iv in iv_by_dte.items() if d > 0 and iv > 0}
    if not valid:
        return {'iv_back_dte': 0, 'iv_back': 0.0, 'term_slope': 0.0, 'term_regime': 'unknown'}
    front_dte = min(valid)
    iv_front  = valid[front_dte]
    back_candidates = [d for d in valid if d > front_dte]
    back_dte = min(back_candidates) if back_candidates else front_dte
    iv_back  = valid[back_dte]
    slope = iv_back - iv_front
    if abs(slope) < 0.005:
        regime = 'flat'
    elif slope > 0:
        regime = 'contango'
    else:
        regime = 'backwardation'
    return {
        'iv_back_dte': int(back_dte),
        'iv_back'    : round(iv_back, 4),
        'term_slope' : round(slope, 4),
        'term_regime': regime,
    }


def _compute_skew_25d(exposures: Dict[float, Dict], target_delta: float = 0.25,
                      max_delta_miss: float = 0.10) -> float:
    """Skew 25-delta = IV_put_25Δ - IV_call_25Δ (decimal IV).
    Positive = puts richer = bearish. Returns 0.0 if delta match too poor."""
    if not exposures:
        return 0.0
    call_candidates = [(K, ex) for K, ex in exposures.items()
                       if 0 < ex.get('c_delta', 0) <= 0.5 and ex.get('c_iv', 0) > 0]
    put_candidates  = [(K, ex) for K, ex in exposures.items()
                       if -0.5 <= ex.get('p_delta', 0) < 0 and ex.get('p_iv', 0) > 0]
    if not call_candidates or not put_candidates:
        return 0.0
    c_strike, c_ex = min(call_candidates, key=lambda x: abs(x[1]['c_delta'] - target_delta))
    p_strike, p_ex = min(put_candidates,  key=lambda x: abs(x[1]['p_delta'] + target_delta))

    c_delta_actual = c_ex['c_delta']
    p_delta_actual = abs(p_ex['p_delta'])
    c_miss = abs(c_delta_actual - target_delta)
    p_miss = abs(p_delta_actual - target_delta)

    skew = p_ex['p_iv'] - c_ex['c_iv']

    log.info(f"    Skew 25Δ: call K={c_strike:.0f} Δ={c_delta_actual:.3f} IV={c_ex['c_iv']*100:.1f}%"
             f"  |  put K={p_strike:.0f} Δ={p_ex['p_delta']:.3f} IV={p_ex['p_iv']*100:.1f}%"
             f"  →  skew={skew*100:+.2f} vp")

    if c_miss > max_delta_miss or p_miss > max_delta_miss:
        log.warning(f"    Skew 25Δ: delta miss trop grand (call miss={c_miss:.3f}, put miss={p_miss:.3f})"
                    f" → skew ignoré")
        return 0.0

    return skew


def aggregate_levels(all_exposures: Dict[float, Dict], spot: float,
                     iv_by_dte: Optional[Dict[int, float]] = None,
                     skew_by_dte: Optional[Dict[int, float]] = None) -> Dict:
    """Agrège toutes les expirations et calcule les niveaux dérivés.

    iv_by_dte   : optional dict DTE -> ATM IV (front-month → IVx).
    skew_by_dte : optional dict DTE -> 25Δ skew (front-month → headline skew).
    """
    combined = defaultdict(lambda: {'gex':0,'vex':0,'cex':0,'dex':0,'c_oi':0,'p_oi':0})
    for K, exp in all_exposures.items():
        combined[K]['gex'] += exp['gex']
        combined[K]['vex'] += exp['vex']
        combined[K]['cex'] += exp['cex']
        combined[K]['dex'] += exp['dex']
        combined[K]['c_oi'] += exp['c_oi']
        combined[K]['p_oi'] += exp['p_oi']

    strikes = sorted(combined.keys())
    if not strikes:
        return {}

    # Totaux
    total_gex = sum(combined[k]['gex'] for k in strikes)
    total_vex = sum(combined[k]['vex'] for k in strikes)
    total_cex = sum(combined[k]['cex'] for k in strikes)
    total_dex = sum(combined[k]['dex'] for k in strikes)

    # Gamma Flip — GEX cumulé change de signe
    gamma_flip = spot
    cumulative = 0.0
    for k in strikes:
        prev       = cumulative
        cumulative += combined[k]['gex']
        if prev != 0 and (prev < 0) != (cumulative < 0):
            gamma_flip = k
            break

    # Vol Trigger — strike le plus proche du spot avec GEX > 0
    vol_trigger = spot
    above_spot = [k for k in strikes if k >= spot and combined[k]['gex'] > 0]
    if above_spot:
        vol_trigger = min(above_spot)

    # Call Wall — GEX max positif
    call_wall = max(strikes, key=lambda k: combined[k]['gex'])

    # Put Wall — GEX max négatif
    put_wall = min(strikes, key=lambda k: combined[k]['gex'])

    # Risk Pivot — premier strike sous spot avec GEX très négatif
    below_spot = [k for k in strikes if k < spot]
    risk_pivot = spot
    if below_spot:
        gex_mean    = abs(total_gex / len(strikes)) if strikes else 1
        very_neg    = [k for k in below_spot if combined[k]['gex'] < -gex_mean * 0.5]
        risk_pivot  = max(very_neg) if very_neg else min(below_spot, key=lambda k: combined[k]['gex'])

    # Vanna Flip — VEX change de signe
    vanna_flip = spot
    cum_vex    = 0.0
    for k in strikes:
        prev_v  = cum_vex
        cum_vex += combined[k]['vex']
        if prev_v != 0 and (prev_v < 0) != (cum_vex < 0):
            vanna_flip = k
            break

    # Charm Magnet — |CEX| maximal
    charm_magnet = max(strikes, key=lambda k: abs(combined[k]['cex']))

    # ── IVx (front-month ATM IV) ────────────────────────────────────────
    atm_iv_front = 0.0
    if iv_by_dte:
        positive_dtes = [d for d in iv_by_dte if d > 0 and iv_by_dte[d] > 0]
        if positive_dtes:
            atm_iv_front = iv_by_dte[min(positive_dtes)]

    # ── Skew 25Δ (front-month) ──────────────────────────────────────────
    skew_25d_front = 0.0
    if skew_by_dte:
        skew_dtes = [d for d in skew_by_dte if d > 0 and skew_by_dte[d] != 0]
        if skew_dtes:
            skew_25d_front = skew_by_dte[min(skew_dtes)]

    # ── Term Structure ──────────────────────────────────────────────────
    term = _compute_term_structure(iv_by_dte or {})

    return {
        'gamma_flip'  : gamma_flip,
        'vol_trigger' : vol_trigger,
        'call_wall'   : call_wall,
        'put_wall'    : put_wall,
        'risk_pivot'  : risk_pivot,
        'vanna_flip'  : vanna_flip,
        'charm_magnet': charm_magnet,
        'total_gex'   : total_gex,
        'total_vex'   : total_vex,
        'total_cex'   : total_cex,
        'total_dex'   : total_dex,
        'gex_regime'  : 1 if total_gex >= 0 else -1,
        'vex_regime'  : 1 if total_vex >= 0 else -1,
        'atm_iv_front': round(atm_iv_front, 4),
        'iv_by_dte'   : {int(d): round(iv, 4) for d, iv in (iv_by_dte or {}).items()},
        'skew_25d_front': round(skew_25d_front, 4),
        'skew_by_dte'   : {int(d): round(s, 4) for d, s in (skew_by_dte or {}).items()},
        'iv_back_dte' : term['iv_back_dte'],
        'iv_back'     : term['iv_back'],
        'term_slope'  : term['term_slope'],
        'term_regime' : term['term_regime'],
        'n_strikes'   : len(strikes),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Fetch principal
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_gex_levels(manual_spot: float = 0, headless: bool = False) -> Dict:
    """Fetch complet : trade date → expirations → OI/settle → Greeks → niveaux."""
    with CMEBrowserSession(headless=headless) as session:

        trade_date = get_latest_trade_date(session)
        tdf        = f"{trade_date[4:6]}/{trade_date[6:8]}/{trade_date[:4]}"
        log.info(f"Trade date: {trade_date}  fmt: {tdf}")

        spot = manual_spot if manual_spot > 0 else get_es_spot_price(session)
        if spot <= 0:
            log.error("Impossible de récupérer le spot ES — utilisez --spot XXXX")
            return {}
        log.info(f"Spot ES: {spot:.2f}")

        expirations = get_all_expirations(session, trade_date)
        if not expirations:
            log.error("Aucune expiration trouvée")
            return {}

        all_exposures: Dict[float, Dict] = {}
        # ATM IV per DTE (collected once per expiration, used for IVx + term structure)
        iv_by_dte: Dict[int, float] = {}
        # 25Δ skew per DTE (used for headline skew)
        skew_by_dte: Dict[int, float] = {}

        for exp in expirations:
            pid = exp['productId']
            ec  = exp['expirationCode']
            dte = _calc_dte(ec)

            log.info(f"  Traitement {exp['label']}  pid={pid}  exp={ec}  dte={dte}")

            if pid in WEEKLY_PIDS:
                # Weeklies : OI depuis Volume/Details (pendant marché)
                # settle prices absents → IV estimée (ATM ~18%)
                oi_data = get_oi_volume_details(
                    session, pid, trade_date, ec,
                    estimated_iv=0.18,
                )
            elif pid in STANDARD_PIDS:
                # STANDARD : merge Volume/Details (OI intraday) + Settlements (settle prices)
                # Fallback automatique sur Settlements seul si off-hours
                oi_data = get_oi_standard_with_intraday(
                    session, pid, trade_date, ec,
                    contract_id=f"ES{ec}",
                    trade_date_fmt=tdf,
                    dte=dte,
                    estimated_iv=0.18,
                )
            else:
                oi_data = get_oi_by_strike(
                    session, pid, trade_date, ec,
                    exp.get('code6', ''),
                    contract_id=f"ES{ec}",
                    trade_date_fmt=tdf,
                    dte=dte,
                )

            if not oi_data:
                log.info(f"  {pid}/{ec} → vide, skip")
                continue

            settle_data = oi_data  # settlements inclus dans la même réponse (ou fallback)
            exposures   = compute_greek_exposures(oi_data, settle_data, dte, spot)

            # ATM IV + Skew 25Δ pour cette expiration
            if dte > 0 and exposures:
                atm_iv = _compute_atm_iv(exposures, spot)
                if atm_iv > 0:
                    iv_by_dte.setdefault(dte, atm_iv)
                skew = _compute_skew_25d(exposures)
                if skew != 0:
                    skew_by_dte.setdefault(dte, skew)

            for K, exp_data in exposures.items():
                if K not in all_exposures:
                    all_exposures[K] = {'gex':0,'vex':0,'cex':0,'dex':0,'c_oi':0,'p_oi':0}
                for key in ('gex','vex','cex','dex','c_oi','p_oi'):
                    all_exposures[K][key] += exp_data[key]

            log.info(f"  {pid}/{ec} → {len(exposures)} strikes avec Greeks")

        if not all_exposures:
            log.error("Aucune exposition calculée")
            return {}

        levels = aggregate_levels(all_exposures, spot,
                                  iv_by_dte=iv_by_dte, skew_by_dte=skew_by_dte)
        levels['spot']       = spot
        levels['trade_date'] = trade_date

        # Sauvegarder le JSON
        GEX_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        GEX_OUTPUT_PATH.write_text(json.dumps(levels, indent=2))
        log.info(f"JSON sauvegardé → {GEX_OUTPUT_PATH}")

        log.info(
            f"ES GEX: flip={levels['gamma_flip']:.0f}  "
            f"trigger={levels['vol_trigger']:.0f}  "
            f"call_wall={levels['call_wall']:.0f}  "
            f"put_wall={levels['put_wall']:.0f}  "
            f"charm_magnet={levels['charm_magnet']:.0f}"
        )
        return levels


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import sys, io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="CME ES Options Greeks Fetcher")
    parser.add_argument('--spot',        type=float, default=0,
                        help="Prix spot ES (0=auto depuis CME quotes)")
    parser.add_argument('--test-expiry', action='store_true',
                        help="Tester la liste des expirations uniquement")
    parser.add_argument('--test-quotes', action='store_true',
                        help="Tester uniquement la récupération du spot")
    args = parser.parse_args()

    headless = False  # Toujours visible — Akamai bloque le headless Chromium
    print(f"=== CME ES Options Greeks Fetcher ({'visible' if not headless else 'headless'}) ===")
    print(f"  Spot: {'auto (CME quotes)' if args.spot==0 else f'{args.spot:.2f} (manuel)'}")

    if args.test_quotes:
        with CMEBrowserSession(headless=headless) as session:
            price = get_es_spot_price(session)
            print(f"\n  ES Spot: {price:.2f}" if price > 0 else "\n  ECHEC: aucun prix récupéré")
        return

    if args.test_expiry:
        with CMEBrowserSession(headless=headless) as session:
            td   = get_latest_trade_date(session)
            exps = get_all_expirations(session, td)
            tdf  = f"{td[4:6]}/{td[6:8]}/{td[:4]}"
            print(f"Trade date: {td}")
            for exp in exps[:15]:
                pid     = exp['productId']
                ec      = exp['expirationCode']
                oi_data = get_oi_by_strike(session, pid, td, ec,
                                            exp.get('code6',''),
                                            contract_id=f"ES{ec}",
                                            trade_date_fmt=tdf)
                total_oi = sum(d['c_oi']+d['p_oi'] for d in oi_data.values())
                print(f"  {exp['label']:30s} pid={pid:6d}  exp={ec}  "
                      f"strikes={len(oi_data):3d}  OI={total_oi:,.0f}")
        return

    lv   = fetch_gex_levels(args.spot, headless=headless)
    spot = lv.get('spot', args.spot)
    if lv:
        print(f"\n=== Niveaux Options Greeks ES @ {spot:.0f} ===")
        print('-' * 50)
        print(f"  GEX Total      : {lv['total_gex']:+.3e}  ({'POSITIF pinning' if lv['gex_regime']==1 else 'NEGATIF amplification'})")
        print(f"  VEX Total      : {lv['total_vex']:+.3e}  ({'IV down = rally' if lv['total_vex']>0 else 'IV up = sell-off'})")
        print(f"  CEX Total      : {lv['total_cex']:+.3e}")
        print(f"  DEX Total      : {lv['total_dex']:+.3e}  ({'haussier' if lv['total_dex']>0 else 'baissier'})")
        print('-' * 50)
        print(f"  Gamma Flip     : {lv['gamma_flip']:.0f}  (spot={spot:.0f}, diff={spot-lv['gamma_flip']:+.0f})")
        print(f"  Vol Trigger    : {lv['vol_trigger']:.0f}")
        print(f"  Call Wall      : {lv['call_wall']:.0f}")
        print(f"  Put Wall       : {lv['put_wall']:.0f}")
        print(f"  Risk Pivot     : {lv['risk_pivot']:.0f}")
        print(f"  Vanna Flip     : {lv['vanna_flip']:.0f}")
        print(f"  Charm Magnet   : {lv['charm_magnet']:.0f}")
        print(f"  Strikes        : {lv['n_strikes']}")
        print(f"  Trade Date     : {lv['trade_date']}")
        print(f"  JSON → {GEX_OUTPUT_PATH}")
    else:
        print("Echec")
        sys.exit(1)


if __name__ == '__main__':
    main()
