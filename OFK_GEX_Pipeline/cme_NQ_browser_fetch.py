#!/usr/bin/env python3
"""
cme_browser_fetch.py  —  Options Greeks Exposure fetcher for NQ E-mini futures (CME via Playwright)

CME endpoints discovered via browser Network tab:
  1. /CmeWS/mvc/Volume/TradeDates?exchange=CBOT
  2. /CmeWS/mvc/Volume/Options/Expirations?productid=146&tradedate={date}
  3. /CmeWS/mvc/Volume/Options/Details?productid={pid}&tradedate={date}&expirationcode={code}&reporttype=F
  4. /CmeWS/mvc/Settlements/Options/Settlements/{pid}/OOF?...

Computed levels (SpotGamma-inspired):
  GEX  = Gamma Exposure       -> sum(OI x gamma x mult x S2)  (pinning vs amplification)
  VEX  = Vanna Exposure        -> sum(OI x vanna x mult x S)   (IV-driven flows)
  CEX  = Charm Exposure        -> sum(OI x charm x mult)       (time-driven flows)
  DEX  = Delta Exposure        -> sum(OI x delta x mult x S)   (directional)

  Derived levels:
  - Gamma Flip (Zero Gamma)  : cumulative GEX changes sign
  - Volatility Trigger       : nearest strike above spot with GEX > 0
  - Call Wall / Put Wall     : strikes with max positive / max negative GEX
  - Risk Pivot               : first strike below spot where GEX turns very negative
  - Vanna Flip               : strike where VEX changes sign
  - Charm Magnet             : strike with max |CEX| (end-of-session price magnet)

Usage:
  python cme_browser_fetch.py --spot 24568
  python cme_browser_fetch.py --test-expiry [--visible]
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

CME_BASE       = "https://www.cmegroup.com"
CME_MAIN_PAGE  = CME_BASE + "/markets/equities/nasdaq/e-mini-nasdaq-100.quotes.options.html#optionProductId=148"
CME_QUOTES_URL = CME_BASE + "/markets/equities/nasdaq/e-mini-nasdaq-100.quotes.html"
CME_SETTLEMENTS_BASE = CME_BASE + "/markets/equities/nasdaq/e-mini-nasdaq-100.settlements.options.html"

# Settlements pages by type (in CME menu order)
# Standard=148, EOM=6745, Mon=9004, Tue=10226, Wed=9009, Thu=10231, Fri=5395
CME_SETTLEMENTS_PAGES = {
    148  : CME_SETTLEMENTS_BASE + "#optionProductId=148",
    6745 : CME_SETTLEMENTS_BASE + "#optionProductId=6745",
    9004 : CME_SETTLEMENTS_BASE + "#optionProductId=9004",
    10226: CME_SETTLEMENTS_BASE + "#optionProductId=10226",
    9009 : CME_SETTLEMENTS_BASE + "#optionProductId=9009",
    10231: CME_SETTLEMENTS_BASE + "#optionProductId=10231",
    5395 : CME_SETTLEMENTS_BASE + "#optionProductId=5395",
}
CME_VOLUME_BASE = CME_BASE + "/markets/equities/nasdaq/e-mini-nasdaq-100.volume.options.html"

# Volume pages by PID (same CME menu order)
CME_VOLUME_PAGES = {
    148  : CME_VOLUME_BASE + "#optionProductId=148",
    6745 : CME_VOLUME_BASE + "#optionProductId=6745",
    9004 : CME_VOLUME_BASE + "#optionProductId=9004",
    10226: CME_VOLUME_BASE + "#optionProductId=10226",
    9009 : CME_VOLUME_BASE + "#optionProductId=9009",
    10231: CME_VOLUME_BASE + "#optionProductId=10231",
    5395 : CME_VOLUME_BASE + "#optionProductId=5395",
}

# Weekly PIDs sharing the same settlements page as their parent
# (e.g. Week2/3/4 Friday all use pid=5395 as reference)
CME_SETTLEMENTS_PARENT = {
    5396: 5395, 5397: 5395, 5398: 5395,   # Friday week 2/3/4
    9006: 9004, 9007: 9004,                # Monday week 3/4
    9010: 9009, 9011: 9009, 9012: 9009,   # Wednesday week 2/3/4
    10227: 10226, 10228: 10226, 10229: 10226,  # Tuesday week 2/3/4
    10232: 10231, 10233: 10231, 10234: 10231,  # Thursday week 2/3/4
}
NQ_FUTURES_ID  = 146
NQ_MULTIPLIER  = 20    # $20 per NQ point
MIN_OI         = 5     # minimum OI per strike to include

# ── JSON output path (centralized in config.py, override via NQ_GEX_JSON env var) ──
from config import NQ_GEX_JSON as GEX_OUTPUT_PATH


# ═══════════════════════════════════════════════════════════════════════════════
# Black-Scholes Greeks
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
    """
    Computes delta, gamma, vanna, charm for a BS option.
    Returns a dict with the 4 Greeks.
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {'delta':0, 'gamma':0, 'vanna':0, 'charm':0}
    try:
        d1, d2 = _d1d2(S, K, T, r, sigma)
        pdf_d1 = _norm_pdf(d1)
        sqrt_T = math.sqrt(T)

        # Delta
        if is_call:
            delta = _norm_cdf(d1)
        else:
            delta = _norm_cdf(d1) - 1.0  # always negative for puts

        # Gamma (identical for calls and puts)
        gamma = pdf_d1 / (S * sigma * sqrt_T)

        # Vanna = ∂delta/∂sigma = ∂²V/∂S∂σ
        # = -pdf(d1) * d2 / sigma
        vanna = -pdf_d1 * d2 / sigma

        # Charm = ∂delta/∂t (delta decay per unit of time)
        # Charm_call = -pdf(d1) * (2rT - d2*sigma*sqrt(T)) / (2T*sigma*sqrt(T))
        # Convention: charm > 0 → delta increases with time
        # Charm_call = -pdf(d1) * (2rT - d2*sigma*sqrt(T)) / (2T*sigma*sqrt(T))
        # Charm_put  = charm_call + r*exp(-rT)*N(-d2)
        charm_call = -pdf_d1 * (2*r*T - d2*sigma*sqrt_T) / (2*T*sigma*sqrt_T)
        if is_call:
            charm = charm_call
        else:
            charm = charm_call + r * math.exp(-r * T) * _norm_cdf(-d2)

        return {'delta': delta, 'gamma': gamma, 'vanna': vanna, 'charm': charm}
    except Exception:
        return {'delta':0, 'gamma':0, 'vanna':0, 'charm':0}


def implied_vol(option_price: float, S: float, K: float, T: float,
                r: float, is_call: bool) -> float:
    """IV via bisection (60 iterations). Returns 0.25 if not converged."""
    if option_price <= 0 or T <= 0:
        return 0.25
    try:
        lo, hi = 1e-4, 5.0
        for _ in range(60):
            mid = (lo + hi) / 2
            d1, d2 = _d1d2(S, K, T, r, mid)
            disc = math.exp(-r * T)
            if is_call:
                price = S*_norm_cdf(d1) - K*disc*_norm_cdf(d2)
            else:
                price = K*disc*_norm_cdf(-d2) - S*_norm_cdf(-d1)
            if price < option_price:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2
    except Exception:
        return 0.25


# ═══════════════════════════════════════════════════════════════════════════════
# Playwright session
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
        log.info("Initializing CME browser...")
        for attempt in range(3):
            try:
                self._page.goto(CME_MAIN_PAGE, wait_until='domcontentloaded', timeout=30000)
                time.sleep(4)
                log.info("CME browser ready")
                break
            except Exception as e:
                log.warning(f"goto attempt {attempt+1}/3: {e}")
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
# CME fetchers
# ═══════════════════════════════════════════════════════════════════════════════

def get_latest_trade_date(session: CMEBrowserSession) -> str:
    url  = f"{CME_BASE}/CmeWS/mvc/Volume/TradeDates?exchange=CBOT&isProtected"
    data = session.fetch_json(url)
    if data and isinstance(data, list) and data:
        td = data[0].get('tradeDate', '')
        if td:
            log.info(f"  Trade date: {td}")
            return td
    # Fallback: last business day
    today = date.today()
    for delta in range(1, 5):
        d = today - timedelta(days=delta)
        if d.weekday() < 5:
            return d.strftime('%Y%m%d')
    return today.strftime('%Y%m%d')


def get_nq_spot_price(session: CMEBrowserSession) -> float:
    """
    Fetches the latest NQ futures price from CME.
    Tries several endpoints with full debug output.
    """
    # Real endpoints discovered via the CME Network tab
    _t = int(time.time() * 1000)
    all_endpoints = [
        CME_BASE + f"/CmeWS/mvc/quotes/v2/146?isProtected&_t={_t}",
        CME_BASE + f"/CmeWS/mvc/quotes/v2/contracts-by-number?isProtected&_t={_t}",
    ]

    for endpoint in all_endpoints:
        # Use fetch_json which already returns parsed JSON,
        # but we need the HTTP status for debug → direct JS call
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

                # Search for a price across all known structures
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
                                if 15000 < price < 40000:
                                    log.info(f"  ✓ Spot NQ: {price:.2f}  (field={field})")
                                    return price
                            except Exception:
                                pass
            except Exception as e:
                log.warning(f"  Parse error: {e}")

    log.warning("  get_nq_spot_price: no valid endpoint found")
    return 0.0


def get_all_expirations(session: CMEBrowserSession, trade_date: str) -> List[Dict]:
    url  = (f"{CME_BASE}/CmeWS/mvc/Volume/Options/Expirations"
            f"?productid={NQ_FUTURES_ID}&tradedate={trade_date}&isProtected")
    data = session.fetch_json(url)
    if not data or not isinstance(data, list):
        log.warning(f"  Expirations: empty or invalid response: {type(data)} {str(data)[:200]}")
        return []
    # DEBUG: print first raw group
    if data:
        log.info(f"  Expirations RAW[0]: {str(data[0])[:600]}")
    # Log the first full expiration too
    if data and data[0].get('expirations'):
        log.info(f"  First expiration full: {str(data[0]['expirations'][0])[:600]}")
    results = []
    for group in data:
        if not isinstance(group, dict): continue
        for exp in group.get('expirations', []):
            if not isinstance(exp, dict): continue
            pid = exp.get('productId', 0)
            ec  = exp.get('expirationCode', '')   # ex: H26
            exp_obj = exp.get('expiration', {})
            code6 = exp_obj.get('code', '') or exp_obj.get('tickerCode', '')  # ex: H6
            key   = exp.get('key', {})
            if pid and ec:
                results.append({
                    'productId'     : pid,
                    'expirationCode': ec,
                    'code6'         : code6,
                    'key'           : key,
                    'label'         : exp.get('label', ''),
                    'isWeekly'      : group.get('weekly', False),
                })
    log.info(f"  {len(results)} expirations")
    return results


def intercept_settlements_by_page(session: CMEBrowserSession,
                                     pid: int, trade_date_fmt: str) -> Dict:
    """
    Navigates to the settlements page of the right type and intercepts the XHR
    that CME automatically triggers → recovers the real monthYear and
    optionExpiration parameters, plus the data directly.
    """
    # Resolve parent pid for weekly child PIDs
    page_pid = CME_SETTLEMENTS_PARENT.get(pid, pid)
    page_url = CME_SETTLEMENTS_PAGES.get(page_pid)
    if not page_url:
        log.debug(f"  No settlements page for pid={pid}")
        return {}

    captured = {}

    def on_response(resp):
        url = resp.url
        if ('Settlements/Options/Settlements' in url
                and str(pid) in url
                and 'tradeDate' in url):
            try:
                data = resp.json()
                if data and not data.get('empty', True):
                    captured['url']  = url
                    captured['data'] = data
                    log.info(f"    [{pid}] XHR intercepted: {url[60:120]}")
            except Exception:
                pass

    session._page.on('response', on_response)
    try:
        session._page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(3)
    except Exception as e:
        log.debug(f"  goto settlements page {page_pid}: {e}")
    finally:
        session._page.remove_listener('response', on_response)

    if not captured:
        log.debug(f"  [{pid}] No XHR intercepted on settlements page")
        return {}

    return captured.get('data', {})



def _get_atm_iv(spot: float, default_iv: float = 0.20) -> float:
    """Estimated ATM IV — used for weeklies without settle prices.
    In production, will be replaced by IV interpolated from the standard surface."""
    # ~20% implied vol for NQ (adjust based on current VIX)
    # VIX ~20 -> daily IV ~ VIX/sqrt(252) -> annualized ~ 0.20
    return default_iv


# Cache to avoid reloading the same volume page for each expiration of the same PID
_volume_page_cache: Dict[int, bool] = {}

def get_oi_volume_details(session: CMEBrowserSession, pid: int,
                          trade_date: str, exp_code: str,
                          estimated_iv: float = 0.20) -> Dict[float, Dict]:
    """
    Fetches OI per strike for weeklies/EOM via Volume/Options/Details.
    Strategy:
      1. Navigate to the volume page of the right type (if not already done for this PID)
         → CME automatically triggers the XHRs, sets cookies
      2. Call the Volume/Details endpoint directly with fetch_json
    """
    def _f(v):
        try: return float(str(v).replace(',','').strip()) if v not in (None,'-','') else 0.0
        except Exception: return 0.0

    # Resolve parent page for this PID
    page_pid = CME_SETTLEMENTS_PARENT.get(pid, pid)
    volume_url = CME_VOLUME_PAGES.get(page_pid)

    # Navigate to volume page if not already done for this page_pid
    if volume_url and page_pid not in _volume_page_cache:
        log.info(f"    [Volume page] Navigating pid={page_pid}: {volume_url}")
        try:
            session._page.goto(volume_url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(2)
            _volume_page_cache[page_pid] = True
        except Exception as e:
            log.warning(f"    [Volume page] goto failed: {e}")

    # Direct Volume/Details API call
    ts  = int(time.time() * 1000)
    url = (f"{CME_BASE}/CmeWS/mvc/Volume/Options/Details"
           f"?productid={pid}&tradedate={trade_date}"
           f"&expirationcode={exp_code}&reporttype=F"
           f"&isProtected&_t={ts}")
    log.info(f"    [Volume/Details] URL: {url}")
    data = session.fetch_json(url)

    rows = []
    if isinstance(data, list):
        rows = data
    elif isinstance(data, dict):
        rows = data.get('rows', data.get('items', data.get('settlements', [])))

    if not rows:
        log.info(f"    [Volume/Details] {pid}/{exp_code} -> 0 strikes (empty)")
        return {}

    by_strike: Dict[float, Dict] = defaultdict(lambda: {
        'c_oi': 0.0, 'p_oi': 0.0,
        'c_settle': 0.0, 'p_settle': 0.0,
        'iv': estimated_iv,
    })

    for row in rows:
        if not isinstance(row, dict): continue
        K = _f(row.get('strikePrice') or row.get('strike') or row.get('strikePx') or 0)
        if K <= 0: continue
        oi = _f(row.get('openInterest') or row.get('oi') or 0)
        opt_type = str(row.get('optionType') or row.get('type') or '').lower()
        if 'put' in opt_type:
            by_strike[K]['p_oi'] = oi
        else:
            by_strike[K]['c_oi'] = oi

    n = len(by_strike)
    log.info(f"    [Volume/Details] {pid}/{exp_code} → {n} strikes")
    return dict(by_strike)


def get_oi_standard_with_intraday(session: CMEBrowserSession, pid: int,
                                   trade_date: str, exp_code: str, *,
                                   contract_id: str, trade_date_fmt: str,
                                   dte: int, estimated_iv: float = 0.20) -> Dict[float, Dict]:
    """
    STANDARD_PIDS (e.g. 148 quarterly NQ): combines
      - Intraday OI via Volume/Options/Details?reporttype=F   (updated during the session)
      - Settle prices via Settlements/Options/Settlements/{pid}/OOF  (used for IV inversion)

    If Volume/Details is empty (market closed / off-hours), full fallback to Settlements
    (which also contains the previous-day EOD OI).
    """
    # 1. Intraday OI
    intraday_oi = get_oi_volume_details(session, pid, trade_date, exp_code,
                                         estimated_iv=estimated_iv)
    # 2. Settle prices (+ EOD OI as fallback)
    settle_data = get_oi_by_strike(session, pid, trade_date, exp_code,
                                    contract_id=contract_id,
                                    trade_date_fmt=trade_date_fmt,
                                    dte=dte)

    if not intraday_oi:
        log.info(f"    [intraday→fallback] {pid}/{exp_code}: Volume/Details empty → Settlements only")
        return settle_data

    # 3. Merge: intraday OI preferred, settle prices from settlements
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


def get_oi_by_strike(session: CMEBrowserSession, pid: int,
                     trade_date: str, exp_code: str,
                     code6: str = '',
                     contract_id: str = '',
                     trade_date_fmt: str = '',
                     dte: int = None) -> Dict[float, Dict]:
    """
    Fetches OI per strike from the Settlements endpoint (available 24/7).
    Used as a fallback (off-hours) or for expirations without Volume/Details data.
    """
    # Settlements contains OI (openInterestCall/Put) and settle prices
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
    log.info(f"    RAW keys={list(data.keys()) if isinstance(data,dict) else type(data)}  preview={str(data)[:300]}")

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
    log.info(f"    OI/settle [{pid}/{exp_code}] → {n} strikes (settlements endpoint)")

    # If empty AND near expiration (0DTE/1DTE): retry with today's date
    # (CME sometimes publishes intraday settlements for imminent expirations)
    if n == 0 and dte is not None and dte <= 2:
        today_fmt = date.today().strftime('%m/%d/%Y')
        if today_fmt != trade_date_fmt:
            log.info(f"    [{pid}/{exp_code}] dte={dte} → retry with today's date {today_fmt}")
            url2 = (f"{CME_BASE}/CmeWS/mvc/Settlements/Options/Settlements"
                    f"/{pid}/OOF?strategy=DEFAULT&optionProductId={pid}"
                    f"&monthYear={contract_id}&optionExpiration={pid}-{exp_code}"
                    f"&tradeDate={today_fmt}&pageSize=500&isProtected&_t={int(time.time()*1000)}")
            try:
                resp2 = session._page.evaluate(
                    "(url) => fetch(url).then(r=>r.json())", url2)
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
                    log.info(f"    [{pid}/{exp_code}] → {n} strikes (today retry)")
            except Exception as e:
                log.debug(f"    retry today failed: {e}")

    return dict(by_strike)


def get_settle_prices(session: CMEBrowserSession, pid: int, *,
                      contract_id: str, exp_code: str,
                      trade_date_fmt: str) -> Dict[float, Dict]:
    ts  = int(time.time() * 1000)
    url = (f"{CME_BASE}/CmeWS/mvc/Settlements/Options/Settlements"
           f"/{pid}/OOF"
           f"?strategy=DEFAULT&optionProductId={pid}"
           f"&monthYear={contract_id}"
           f"&optionExpiration={pid}-{exp_code}"
           f"&tradeDate={trade_date_fmt}"
           f"&pageSize=500&isProtected&_t={ts}")
    data = session.fetch_json(url)
    if not data: return {}

    def _f(v):
        if v in (None, '-', '', 'N/A'): return 0.0
        try: return float(str(v).replace(',','').rstrip('B').rstrip('A'))
        except Exception: return 0.0

    by_strike = defaultdict(lambda: {'c_settle': 0.0, 'p_settle': 0.0})
    for row in (data.get('settlements', []) if isinstance(data, dict) else []):
        if not isinstance(row, dict): continue
        K = _f(row.get('strike') or 0)
        if K <= 0: continue
        settle = _f(row.get('settle') or 0)
        if 'put' in str(row.get('type','')).lower():
            by_strike[K]['p_settle'] = settle
        else:
            by_strike[K]['c_settle'] = settle
    return dict(by_strike)


def _calc_dte(exp_code: str) -> int:
    """DTE from expiry code, e.g. 'H26' → 3rd Friday of March 2026.
    NOTE: assumes 3rd-Friday expiration — incorrect for weeklies."""
    month_map = {'F':1,'G':2,'H':3,'J':4,'K':5,'M':6,
                 'N':7,'Q':8,'U':9,'V':10,'X':11,'Z':12}
    try:
        import calendar
        m  = month_map.get(exp_code[0], 3)
        y  = 2000 + int(exp_code[1:])
        # 3rd Friday
        c  = calendar.monthcalendar(y, m)
        fs = [w[4] for w in c if w[4] != 0]
        exp_date = date(y, m, fs[2] if len(fs) >= 3 else fs[-1])
        return max(0, (exp_date - date.today()).days)
    except Exception:
        return 30


# ═══════════════════════════════════════════════════════════════════════════════
# Greek exposure computation
# ═══════════════════════════════════════════════════════════════════════════════

def compute_greek_exposures(
        oi_data: Dict[float, Dict],
        settle_data: Dict[float, Dict],
        dte: int,
        spot: float,
        r: float = 0.045,
) -> Dict[float, Dict]:
    """
    For each strike: computes GEX, VEX, CEX, DEX (calls + puts separately).

    GEX  = (c_oi × c_gamma  - p_oi × p_gamma)  × mult × S²
    VEX  = (c_oi × c_vanna  + p_oi × p_vanna)  × mult × S
           (calls and puts both have positive vanna for dealers short puts/long calls)
    CEX  = (c_oi × c_charm  + p_oi × p_charm)  × mult
           (OTM charm negative → dealers buy back)
    DEX  = (c_oi × c_delta  + p_oi × p_delta)  × mult × S
           (net dealer delta)

    Dealer convention:
      - Dealers are net LONG calls (positive gamma -> positive GEX = pinning)
      - Dealers are net SHORT puts (positive gamma -> positive GEX)
      - GEX = calls - puts for the correct sign
    """
    T = max(dte / 365.0, 0.5 / 365)
    S = spot if spot > 0 else 20000.0
    exposures = {}

    for K, oi in oi_data.items():
        c_oi = oi.get('c_oi', 0)
        p_oi = oi.get('p_oi', 0)
        if c_oi + p_oi < MIN_OI:
            continue

        s_data  = settle_data.get(K, {})
        c_price = s_data.get('c_settle', 0)
        p_price = s_data.get('p_settle', 0)

        # IV per strike (defaults to 0.25)
        c_iv = implied_vol(c_price, S, K, T, r, True)  if c_price > 0 else 0.25
        p_iv = implied_vol(p_price, S, K, T, r, False) if p_price > 0 else 0.25

        c_g = bs_greeks(S, K, T, r, c_iv, True)
        p_g = bs_greeks(S, K, T, r, p_iv, False)

        S2 = S * S
        # GEX: dealer convention long calls, short puts → calls contrib positive, puts also positive
        # net = calls - puts (puts have positive gamma but dealers are SHORT puts)
        gex = (c_oi * c_g['gamma'] - p_oi * p_g['gamma']) * NQ_MULTIPLIER * S2

        # VEX: vanna measures dDelta/dIV → dealers are exposed to IV change
        # Long call: positive vanna → if IV↑, delta↑, dealers must sell
        # Short put: positive vanna → if IV↓, delta (absolute) ↓, dealers buy back
        vex = (c_oi * c_g['vanna'] + p_oi * abs(p_g['vanna'])) * NQ_MULTIPLIER * S

        # CEX: charm = delta decay over time
        # OTM → delta decays → dealers buy back (bullish flow into expiry)
        cex = (c_oi * c_g['charm'] + p_oi * abs(p_g['charm'])) * NQ_MULTIPLIER

        # DEX: net delta exposure (directional)
        dex = (c_oi * c_g['delta'] + p_oi * p_g['delta']) * NQ_MULTIPLIER * S

        exposures[K] = {
            'gex': gex, 'vex': vex, 'cex': cex, 'dex': dex,
            'c_oi': c_oi, 'p_oi': p_oi,
            'c_iv': c_iv, 'p_iv': p_iv,
            'c_gamma': c_g['gamma'], 'p_gamma': p_g['gamma'],
            'c_delta': c_g['delta'], 'p_delta': p_g['delta'],
            'dte': dte,
        }

    return exposures


def _compute_atm_iv(exposures: Dict[float, Dict], spot: float) -> float:
    """
    ATM IV (annualized) for one expiration.

    Returns the average of c_iv and p_iv at the strike closest to spot.
    Falls back to whichever leg is positive if only one is available.
    Returns 0.0 if no usable IV is found.
    """
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
    """
    Term-structure metrics from per-DTE ATM IVs.

    Returns dict with:
      - iv_back_dte : DTE used for the back-month leg (≥30 DTE if available,
                       else max DTE in the data)
      - iv_back     : ATM IV at iv_back_dte
      - term_slope  : iv_back - iv_front (decimal IV)
      - term_regime : "contango" (slope > +0.5 vp), "backwardation" (slope < -0.5 vp),
                       "flat" (within ±0.5 vp), or "unknown" (no data)
    """
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
    if abs(slope) < 0.005:    # < 0.5 vol pts
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
    """
    Skew 25-delta = IV_put_25Δ - IV_call_25Δ (in IV decimal, e.g. 0.03 = 3 vol pts).

    Picks the OTM call closest to +target_delta and the OTM put closest to
    -target_delta, then returns the difference of their IVs.

    Positive skew → puts cost more than calls → bearish positioning.
    Returns 0.0 if not enough usable strikes or if delta match is too poor.
    """
    if not exposures:
        return 0.0
    # OTM calls: 0 < delta <= 0.5
    call_candidates = [(K, ex) for K, ex in exposures.items()
                       if 0 < ex.get('c_delta', 0) <= 0.5 and ex.get('c_iv', 0) > 0]
    # OTM puts: -0.5 <= delta < 0
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
        log.warning(f"    Skew 25Δ: delta miss too large (call miss={c_miss:.3f}, put miss={p_miss:.3f})"
                    f" → skew ignored")
        return 0.0

    return skew


def compute_key_levels(all_exposures: Dict[float, Dict], spot: float,
                       iv_by_dte: Optional[Dict[int, float]] = None,
                       skew_by_dte: Optional[Dict[int, float]] = None) -> Dict:
    """
    Aggregates all expirations and computes the key SpotGamma levels.

    iv_by_dte   : optional dict DTE -> ATM IV (front-month → IVx).
    skew_by_dte : optional dict DTE -> 25Δ skew (front-month → headline skew).
    """
    # Aggregate per strike
    agg = defaultdict(lambda: {'gex':0.0, 'vex':0.0, 'cex':0.0, 'dex':0.0})
    for K, exp in all_exposures.items():
        agg[K]['gex'] += exp['gex']
        agg[K]['vex'] += exp['vex']
        agg[K]['cex'] += exp['cex']
        agg[K]['dex'] += exp['dex']

    if not agg:
        return {}

    strikes   = sorted(agg.keys())
    total_gex = sum(d['gex'] for d in agg.values())
    total_vex = sum(d['vex'] for d in agg.values())
    total_cex = sum(d['cex'] for d in agg.values())
    total_dex = sum(d['dex'] for d in agg.values())

    # ── Gamma Flip (Zero Gamma) ─────────────────────────────────────────
    # Strike closest to spot where cumulative GEX (starting from spot)
    # changes sign
    gamma_flip = spot
    strikes_by_dist = sorted(strikes, key=lambda k: abs(k - spot))
    running_gex = 0.0
    prev_sign   = None
    for K in strikes_by_dist:
        running_gex += agg[K]['gex']
        sign = 1 if running_gex >= 0 else -1
        if prev_sign is not None and sign != prev_sign:
            gamma_flip = K
            break
        prev_sign = sign

    # ── Volatility Trigger ──────────────────────────────────────────────
    # First strike above spot with GEX > 0 (pinning transition)
    vol_trigger = spot
    for K in sorted(strikes):
        if K >= spot and agg[K]['gex'] > 0:
            vol_trigger = K
            break

    # ── Call Wall / Put Wall ────────────────────────────────────────────
    call_wall = max(agg, key=lambda k: agg[k]['gex'])
    put_wall  = min(agg, key=lambda k: agg[k]['gex'])

    # ── Risk Pivot ──────────────────────────────────────────────────────
    # First strike BELOW spot where GEX becomes very negative
    # (threshold = 10% of total negative GEX)
    neg_gex_total = abs(min(total_gex, 0))
    threshold     = -neg_gex_total * 0.10 if neg_gex_total > 0 else -1e9
    risk_pivot    = spot
    for K in sorted(strikes, reverse=True):
        if K < spot and agg[K]['gex'] < threshold:
            risk_pivot = K
            break

    # ── Vanna Flip ──────────────────────────────────────────────────────
    vanna_flip  = spot
    running_vex = 0.0
    prev_sign   = None
    for K in strikes_by_dist:
        running_vex += agg[K]['vex']
        sign = 1 if running_vex >= 0 else -1
        if prev_sign is not None and sign != prev_sign:
            vanna_flip = K
            break
        prev_sign = sign

    # ── Charm Magnet ─────────────────────────────────────────────────────
    # Strike with max |CEX| = end-of-session magnet (0DTE dominant)
    charm_magnet = max(agg, key=lambda k: abs(agg[k]['cex']))

    # ── GEX Regime ───────────────────────────────────────────────────────
    # +1 = positive gamma (pinning), -1 = negative gamma (amplification)
    gex_regime = 1 if total_gex >= 0 else -1

    # ── IVx (front-month ATM IV) ────────────────────────────────────────
    # Smallest DTE > 0 wins. Used as the headline implied vol metric.
    atm_iv_front = 0.0
    if iv_by_dte:
        positive_dtes = [d for d in iv_by_dte if d > 0 and iv_by_dte[d] > 0]
        if positive_dtes:
            atm_iv_front = iv_by_dte[min(positive_dtes)]

    # ── Skew 25Δ (front-month) ──────────────────────────────────────────
    # Positive = puts richer than calls = bearish positioning.
    skew_25d_front = 0.0
    if skew_by_dte:
        skew_dtes = [d for d in skew_by_dte if d > 0 and skew_by_dte[d] != 0]
        if skew_dtes:
            skew_25d_front = skew_by_dte[min(skew_dtes)]

    # ── Term Structure ──────────────────────────────────────────────────
    term = _compute_term_structure(iv_by_dte or {})

    return {
        # Totals
        'total_gex'    : total_gex,
        'total_vex'    : total_vex,
        'total_cex'    : total_cex,
        'total_dex'    : total_dex,

        # Price levels
        'gamma_flip'   : gamma_flip,
        'vol_trigger'  : vol_trigger,
        'call_wall'    : call_wall,
        'put_wall'     : put_wall,
        'risk_pivot'   : risk_pivot,
        'vanna_flip'   : vanna_flip,
        'charm_magnet' : charm_magnet,

        # Regimes
        'gex_regime'   : gex_regime,
        'vex_regime'   : (1 if total_vex >= 0 else -1),

        # IVx (ATM IV front-month, annualized) + full term structure
        'atm_iv_front' : round(atm_iv_front, 4),
        'iv_by_dte'    : {int(d): round(iv, 4) for d, iv in (iv_by_dte or {}).items()},

        # Skew 25Δ (puts - calls IV, decimal). Positive = bearish.
        'skew_25d_front': round(skew_25d_front, 4),
        'skew_by_dte'   : {int(d): round(s, 4) for d, s in (skew_by_dte or {}).items()},

        # Term Structure (Phase 1.4)
        'iv_back_dte'   : term['iv_back_dte'],
        'iv_back'       : term['iv_back'],
        'term_slope'    : term['term_slope'],
        'term_regime'   : term['term_regime'],

        # Raw per-strike data (for save/debug)
        'by_strike'    : {k: dict(v) for k, v in agg.items()},
        'n_strikes'    : len(strikes),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Main pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_gex_levels(spot: float = 0.0, headless: bool = False) -> Dict:
    """
    Main entry point → returns all levels.
    Called by ml_server_v3.py.

    If spot=0 (default), the price is fetched automatically from CME quotes.
    """
    all_exposures_by_strike = defaultdict(lambda: {
        'gex':0.0, 'vex':0.0, 'cex':0.0, 'dex':0.0
    })
    # ATM IV per DTE (collected once per expiration, used for IVx + term structure)
    iv_by_dte: Dict[int, float] = {}
    # 25Δ skew per DTE (used for headline skew + term structure)
    skew_by_dte: Dict[int, float] = {}

    # Clear module-level cache (stale across multiple calls in same process)
    _volume_page_cache.clear()

    with CMEBrowserSession(headless=headless) as session:
        trade_date     = get_latest_trade_date(session)
        trade_date_fmt = f"{trade_date[4:6]}/{trade_date[6:8]}/{trade_date[:4]}"

        # Auto-fetch the spot if not provided
        if spot <= 0:
            log.info("Fetching NQ spot from CME quotes...")
            spot = get_nq_spot_price(session)
            if spot <= 0:
                log.warning("Spot unavailable → falling back to prior settle from the data")
                # Last resort: use the median strike as a proxy
                spot = 0.0  # will be recomputed after loading the strikes

        expirations = get_all_expirations(session, trade_date)
        if not expirations:
            log.error("No expiration")
            return {}

        # Standard PIDs (settlements available 24/7)
        STANDARD_PIDS = {148}
        # Weekly/EOM PIDs: OI via Volume/Details (market hours only)
        # No settle prices → IV estimated from the standard surface
        WEEKLY_PIDS = {5395, 5396, 5397, 5398,
                       9004, 9006, 9007,
                       9009, 9010, 9011, 9012,
                       10226,10227,10228,10229,
                       10231,10232,10233,10234,
                       6745, 8044}

        processed = set()
        for exp in expirations:
            pid      = exp['productId']
            exp_code = exp['expirationCode']
            key      = (pid, exp_code)
            if key in processed: continue
            processed.add(key)

            dte = _calc_dte(exp_code)

            if pid in WEEKLY_PIDS:
                # Weeklies: OI from Volume/Details (during market hours)
                # settle prices absent → IV estimated from the standard surface
                oi_data = get_oi_volume_details(
                    session, pid, trade_date, exp_code,
                    estimated_iv=_get_atm_iv(spot),
                )
            elif pid in STANDARD_PIDS:
                # STANDARD: merge Volume/Details (intraday OI) + Settlements (settle prices)
                # Automatic fallback to Settlements alone if off-hours
                oi_data = get_oi_standard_with_intraday(
                    session, pid, trade_date, exp_code,
                    contract_id=f"NQ{exp_code}",
                    trade_date_fmt=trade_date_fmt,
                    dte=dte,
                    estimated_iv=_get_atm_iv(spot),
                )
            else:
                oi_data = get_oi_by_strike(
                    session, pid, trade_date, exp_code,
                    exp.get('code6', ''),
                    contract_id=f"NQ{exp_code}",
                    trade_date_fmt=trade_date_fmt,
                    dte=dte,
                )
            if not oi_data: continue

            # settle_data is now included in oi_data (c_settle/p_settle)
            exposures = compute_greek_exposures(oi_data, oi_data, dte, spot)

            # ATM IV + 25Δ skew for this expiration
            if dte > 0 and exposures:
                atm_iv = _compute_atm_iv(exposures, spot)
                if atm_iv > 0:
                    # If multiple PIDs share the same DTE, keep the first seen
                    iv_by_dte.setdefault(dte, atm_iv)
                skew = _compute_skew_25d(exposures)
                if skew != 0:
                    skew_by_dte.setdefault(dte, skew)

            # Aggregate
            for K, ex in exposures.items():
                all_exposures_by_strike[K]['gex'] += ex['gex']
                all_exposures_by_strike[K]['vex'] += ex['vex']
                all_exposures_by_strike[K]['cex'] += ex['cex']
                all_exposures_by_strike[K]['dex'] += ex['dex']

            log.info(f"  {exp['label']:28s} pid={pid:6d} dte={dte:4d} → "
                     f"{len(exposures)} strikes")

    if not all_exposures_by_strike:
        log.error("No data")
        return {}

    # Spot fallback if still 0: median of strikes (more reliable proxy than max GEX)
    if spot <= 0:
        strikes = sorted(all_exposures_by_strike.keys())
        if strikes:
            spot = strikes[len(strikes) // 2]
            log.warning(f"Spot estimated from median strike: {spot:.0f} (fallback)")

    levels = compute_key_levels(dict(all_exposures_by_strike), spot,
                                 iv_by_dte=iv_by_dte, skew_by_dte=skew_by_dte)
    levels['trade_date'] = trade_date
    levels['spot']       = spot

    # ── JSON save ─────────────────────────────────────────────────────────────
    _json_path = GEX_OUTPUT_PATH
    _json_path.parent.mkdir(parents=True, exist_ok=True)
    save = {k: v for k, v in levels.items() if k != 'by_strike'}
    save['by_strike_sample'] = dict(list(levels['by_strike'].items())[:10])
    with open(_json_path, 'w') as f:
        json.dump(save, f, indent=2)
    log.info(f"  JSON saved → {_json_path}")

    log.info(
        f"IVx={levels['atm_iv_front']*100:.1f}%  "
        f"Term={levels['term_regime']}({levels['term_slope']*100:+.2f}vp)  "
        f"Skew25={levels['skew_25d_front']*100:+.2f}vp  "
        f"GEX={levels['total_gex']:.2e}  "
        f"VEX={levels['total_vex']:.2e}  "
        f"flip={levels['gamma_flip']:.0f}  "
        f"trigger={levels['vol_trigger']:.0f}  "
        f"call_wall={levels['call_wall']:.0f}  "
        f"put_wall={levels['put_wall']:.0f}  "
        f"charm_magnet={levels['charm_magnet']:.0f}"
    )
    return levels


# ═══════════════════════════════════════════════════════════════════════════════
# ML server interface (NinjaTrader XGBoost integration)
# ═══════════════════════════════════════════════════════════════════════════════

def gex_to_ml_features(levels: Dict, spot: float, atr: float) -> Dict[str, float]:
    """
    Converts GEX levels into normalized features for the ML model.
    All distances are normalized by ATR for price invariance.

    Returns a dict with exactly the FEATURES_GEX + FEATURES_GREEK_EXP features
    defined in feature_schema_v3.py.
    """
    if not levels or atr <= 0:
        return {k: 0.0 for k in [
            'GEX_DistGammaFlip', 'GEX_DistCallWall', 'GEX_DistPutWall',
            'GEX_Total', 'GEX_Regime',
            'GEX_DistVolTrigger', 'GEX_DistRiskPivot',
            'GEX_DistVannaFlip', 'GEX_DistCharmMagnet',
            'VEX_Total', 'VEX_Regime',
            'CEX_Total', 'DEX_Directional',
        ]}

    def dist_norm(level_price):
        return (spot - level_price) / atr

    # Log-normalized totals (sign preserved)
    def log_norm(val, scale=1e9):
        if val == 0: return 0.0
        return math.copysign(math.log1p(abs(val) / scale), val)

    return {
        # ── Existing features (backward compatibility) ─────────────────
        'GEX_DistGammaFlip'  : dist_norm(levels.get('gamma_flip', spot)),
        'GEX_DistCallWall'   : (levels.get('call_wall', spot) - spot) / atr,
        'GEX_DistPutWall'    : (spot - levels.get('put_wall', spot)) / atr,
        'GEX_Total'          : log_norm(levels.get('total_gex', 0)),
        'GEX_Regime'         : float(levels.get('gex_regime', 0)),

        # ── New levels ────────────────────────────────────────────────
        'GEX_DistVolTrigger' : (levels.get('vol_trigger', spot) - spot) / atr,
        'GEX_DistRiskPivot'  : dist_norm(levels.get('risk_pivot', spot)),
        'GEX_DistVannaFlip'  : dist_norm(levels.get('vanna_flip', spot)),
        'GEX_DistCharmMagnet': abs(levels.get('charm_magnet', spot) - spot) / atr,

        # ── Normalized Greeks exposures ────────────────────────────────
        'VEX_Total'          : log_norm(levels.get('total_vex', 0), 1e8),
        'VEX_Regime'         : 1.0 if levels.get('total_vex', 0) > 0 else -1.0,
        'CEX_Total'          : log_norm(levels.get('total_cex', 0), 1e6),
        'DEX_Directional'    : log_norm(levels.get('total_dex', 0), 1e10),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    # Fix Windows console encoding (cp1252 → utf-8)
    import sys, io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser()
    parser.add_argument('--spot',        type=float, default=0,
                        help="NQ spot price (0=auto from CME quotes)")
    parser.add_argument('--test-expiry', action='store_true')
    parser.add_argument('--test-quotes', action='store_true',
                        help="Test spot price fetch only")
    parser.add_argument('--visible',     action='store_true')
    args = parser.parse_args()

    headless = False  # Always visible — Akamai blocks headless Chromium
    print(f"=== CME Options Greeks Fetcher ({'visible' if not headless else 'headless'}) ===")
    print(f"  Spot: {'auto (CME quotes)' if args.spot==0 else f'{args.spot:.2f} (manual)'}")

    # Test spot fetch only
    if args.test_quotes:
        with CMEBrowserSession(headless=headless) as session:
            price = get_nq_spot_price(session)
            print(f"\n  NQ Spot: {price:.2f}" if price > 0 else "\n  FAILED: no price retrieved")
        return

    if args.test_expiry:
        with CMEBrowserSession(headless=headless) as session:
            td   = get_latest_trade_date(session)
            exps = get_all_expirations(session, td)
            tdf  = f"{td[4:6]}/{td[6:8]}/{td[:4]}"
            print(f"Trade date: {td}")
            for exp in exps[:15]:
                pid      = exp['productId']
                ec       = exp['expirationCode']
                oi_data  = get_oi_by_strike(session, pid, td, ec,
                                             exp.get('code6',''),
                                             contract_id=f"NQ{ec}",
                                             trade_date_fmt=tdf)
                total_oi = sum(d['c_oi']+d['p_oi'] for d in oi_data.values())
                print(f"  {exp['label']:30s} pid={pid:6d}  exp={ec}  "
                      f"strikes={len(oi_data):3d}  OI={total_oi:,.0f}")
        return

    lv   = fetch_gex_levels(args.spot, headless=headless)  # 0 = auto
    spot = lv.get('spot', args.spot)
    if lv:
        print(f"\n=== NQ Options Greeks Levels @ {spot:.0f} ===")
        print('-' * 50)
        print(f"  GEX Total      : {lv['total_gex']:+.3e}  ({'POSITIVE pinning' if lv['gex_regime']==1 else 'NEGATIVE amplification'})")
        print(f"  VEX Total      : {lv['total_vex']:+.3e}  ({'IV down = rally' if lv['total_vex']>0 else 'IV up = sell-off'})")
        print(f"  CEX Total      : {lv['total_cex']:+.3e}")
        print(f"  DEX Total      : {lv['total_dex']:+.3e}  ({'bullish' if lv['total_dex']>0 else 'bearish'})")
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

        # ── Normalized ML features (post-fetch validation) ───────────────────
        # Uses an approximate ATR ~0.5% of spot for display
        # Real production values use the NinjaTrader ATR(14)
        atr_approx = spot * 0.005
        features = gex_to_ml_features(lv, spot, atr_approx)
        print('')
        print('-' * 50)
        print(f"  Normalized ML features (ATR~{atr_approx:.0f} pts ~ 0.5% spot):")
        print('-' * 50)
        
        # Group by type for readability
        dist_features = {k: v for k, v in features.items() if 'Dist' in k}
        other_features = {k: v for k, v in features.items() if 'Dist' not in k}
        
        print("  Distances (in ATR multiples):")
        for k, v in dist_features.items():
            bar = '█' * min(20, int(abs(v) * 3))
            direction = '→' if v >= 0 else '←'
            print(f"    {k:30s}: {v:+7.3f}x ATR  {direction}{bar}")
        
        print("  Regimes and totals:")
        for k, v in other_features.items():
            if k == 'GEX_Regime':
                regime_str = '🟢 PINNING' if v > 0 else ('🔴 AMPLIF' if v < 0 else '⚪ NEUTRAL')
                print(f"    {k:30s}: {v:+7.3f}  {regime_str}")
            elif k == 'VEX_Regime':
                vex_str = 'IV↓=rally' if v > 0 else 'IV↑=selloff'
                print(f"    {k:30s}: {v:+7.3f}  {vex_str}")
            else:
                print(f"    {k:30s}: {v:+7.3f}")
        
        # Sanity checks
        print(f"\n  Sanity checks:")
        gf = lv.get('gamma_flip', 0)
        cw = lv.get('call_wall', 0)
        pw = lv.get('put_wall', 0)
        if spot > gf:
            print(f"    [OK] Spot ({spot:.0f}) > Gamma Flip ({gf:.0f}) -> POSITIVE regime expected")
        else:
            print(f"    [!!] Spot ({spot:.0f}) < Gamma Flip ({gf:.0f}) -> NEGATIVE regime expected")
        if pw < spot < cw:
            print(f"    [OK] Spot inside Put Wall ({pw:.0f}) <-> Call Wall ({cw:.0f}) zone")
        else:
            print(f"    [!!] Spot outside normal PW/CW zone")
        print(f"    [i]  JSON -> {GEX_OUTPUT_PATH}")
    else:
        print("Failed")
        sys.exit(1)

if __name__ == '__main__':
    main()
