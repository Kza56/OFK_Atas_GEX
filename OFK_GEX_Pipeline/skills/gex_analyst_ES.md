# Skill: GEX Analyst ES — Intraday Scalping Briefing for ES E-mini S&P500

## Instruction
Read the file full_levels_ES.json (path configured in config.py, defaults to
OFK_GEX_Pipeline/data/full_levels_ES.json) and generate the briefing
according to the schema below. Reply with VALID JSON ONLY, nothing else.

## Permanent context — focus INTRADAY SCALPING
- Instrument        : ES E-mini S&P500 (CME, $50/point)
- Target session    : RTH 09:30–16:00 ET
- Style             : 5–30 minute scalping (max intraday)
- Language          : ENGLISH mandatory for all texts

## Data source hierarchy

### GEX levels (structural — remain valid intraday)
- gamma_flip, vol_trigger, risk_pivot, vanna_flip, charm_magnet
- call_wall, put_wall: structural CME multi-day walls (often far from spot)
- total_gex, total_vex, gex_regime

### INTRADAY levels (CBOE 0-7 DTE — PRIMARY for scalping)
- **call_wall_intraday_es**, **put_wall_intraday_es**: 0-7 DTE walls
- call_wall_intraday_gex, put_wall_intraday_gex
- **top_oi_intraday[]**: 3 top OI strikes 0-7 DTE
                         (items: strike_spy, strike_es, call_oi, put_oi, total_oi)
- walls_intraday_max_dte

### Transition levels cTrans/pTrans (Phase 3 — TanukiTrade Gamma Classification Engine)
- **c_trans_intraday_es**: level above which call gamma dominates
                            (cumulative net GEX > 10% of total absolute gamma 0-7 DTE)
- **p_trans_intraday_es**: level below which put gamma dominates
- They define 3 structural intraday regimes:
  - above cTrans → **positive gamma zone** (mean-reversion, compressed vol)
  - between pTrans and cTrans → **transition zone** (neither dampened nor amplified)
  - below pTrans → **negative gamma zone** (amplified vol, directional)
- More granular than simple HVL/gamma_flip.
- trans_intraday_max_dte: max DTE used (default 7)

### DEX D+/D- (Phase 4 — directional hedging pressure)
- **dex_plus_intraday_es**: strike with maximum positive net delta
                             → dealers BUY the underlying (bullish hedging)
- **dex_minus_intraday_es**: strike with maximum negative net delta
                              → dealers SELL (bearish hedging)
- dex_plus_intraday_dex / dex_minus_intraday_dex: raw DEX value (contracts × delta × 100)
- Complementary to Call/Put Walls (gamma captures sensitivity; DEX captures direction).
- D+ acts as a bullish magnet; D- acts as a bearish magnet.

### Expected Move TastyTrade (Phase 2)
- **expected_move_tt_es**: straddle-weighted EM (ATM_straddle × 0.6 + OTM1 × 0.3 + OTM2 × 0.1)
- expected_move_tt_dte: DTE of the expiration used (often 0DTE)
- More accurate than IV-based: uses real bid/ask, captures real skew and hedging cost.
- expected_move_iv_es: legacy IV-based formula (fallback)
- range_high_es / range_low_es now use TT if available, otherwise IV.

### 0DTE levels (very relevant in afternoon / end of session)
- **max_pain_0dte_es**     : Max Pain computed on options expiring today
                              (or tomorrow if no expiration today)
- **pin_strike_0dte_es**   : strike with maximum |gamma|×OI 0DTE = strongest magnet
- **charm_magnet_0dte_es** : OTM strike closest to spot (with OI > 5%)
                              toward which charm decay drags price near close
- zero_dte_oi_total: total 0DTE OI (signal quality — if < 50k, unreliable)
- zero_dte_dte: 0 if true 0DTE, 1 if fallback

### INTRADAY volatility (PRIMARY)
- **atm_iv_intraday**       : CBOE 0-7 DTE IVx
- atm_iv_intraday_dte       : DTE of the measurement (ideally 0-3)
- **skew_25d_intraday**     : CBOE front-most skew
- **term_intraday_regime**  : backwardation / contango / flat (CBOE 0-3d vs ~30d)
- term_intraday_slope       : positive = backwardation = stress
- term_intraday_iv_front, term_intraday_iv_back

### IV Rank (NEW — historical context)
- **iv_rank_intraday**      : object {ivr, iv_min, iv_max, n_samples, status, lookback}
                               IVR = position of current IVx within 252-day window
                               Status: 'ok' (>=20d hist), 'partial' (5-19), 'insufficient' (<5)
- iv_rank_structural        : same for atm_iv_structural (CME 49d)

### STRUCTURAL volatility (SECONDARY)
- atm_iv_structural, skew_25d_structural, term_structural_regime, term_structural_slope
- WARNING: skew_structural CME may be inflated by illiquid OTM calls.

### CBOE metrics converted to NQ
- max_pain_es, expected_move_es, range_low_es, range_high_es, pcr

### Market context _meta (NEW — VIX + macro + pipeline health)
The `_meta` block in full_levels_ES.json contains:
- **vix**, **vix9d**, **vix_dod_change**: spot VIX, 9-day VIX, day-over-day change
- **vix_regime**: "low" (<14) / "normal" (14-20) / "elevated" (20-28) / "extreme" (>28)
- **vix_term**: "backwardation" (VIX9D > VIX, stress) / "flat" / "contango" (calm)
- **vix_term_slope**: VIX9D - VIX
- **macro_in_blackout**: true if a high-impact USD macro event is in progress (±30min)
- **macro_blackout_until_utc**: ISO datetime when blackout ends
- **macro_next_event_title**: next high-impact event title (e.g. "FOMC Statement")
- **macro_minutes_to_next**: minutes until next event (-1 if none known)
- **json_schema_version**: JSON structure version (must match the ATAS indicator)
- **data_quality**: "ok" (CME+CBOE+VIX present) / "partial" / "error"
- **last_update_utc**: ISO datetime of last refresh

## Interpretation rules (scalping)

### Intraday IVx
- < 12% → very low vol, very tight ranges, strong mean-reversion
- 12-20% → normal vol, classic scalping
- > 20% → high vol, widen stops

### Intraday IV Rank (qualifies IVx vs history)
- ivr < 30 (status 'ok') → historically LOW vol → strong mean-reversion,
  scalp vol crush, vol selling viable
- ivr 30-70 → normal vol
- ivr > 70 → historically HIGH vol → reversion to the mean likely
  on vol itself (IV moves more constrained)
- If status != 'ok' (< 20d hist), treat IVR with caution

### Intraday 25Δ skew
- 1-3 vp: normal
- 3-5 vp: caution on shorts
- > 5 vp: aggressive put hedging alert → bearish gap risk
- If skew_intraday is low but skew_structural is high → ignore the structural one.

### Intraday term
- backwardation (slope > +0.5 vp) → IMMEDIATE STRESS, breakouts likely,
  avoid mean-reversion, widen stops
- contango (slope < -0.5 vp) → calm, mean-reversion favored
- flat → follow the GEX levels

### 0DTE (contextual use)
- During morning/regular afternoon: pin_strike_0dte is a probable magnet
- Near session end (after 14:30 ET): charm_magnet_0dte = strong magnet.
  Price typically gravitates toward this strike in the last 60-90 minutes.
- If pin_strike_0dte sits between intraday PW and intraday CW, that is the
  likely center of the session's range.
- If zero_dte_oi_total < 50000 (low liquidity), do not overweight these levels.

### Gamma regime (cTrans/pTrans + intraday Call Wall/Put Wall)
- **spot > intraday Call Wall** → bullish SQUEEZE, dealers short-gamma above
  → explosive vol, fade unlikely, momentum trade
- **spot ∈ [cTrans, intraday Call Wall]** → POSITIVE gamma zone
  → strong mean-reversion, fade moves toward cTrans, tight ranges
- **spot ∈ [pTrans, cTrans]** → TRANSITION zone
  → no clear bias, follow other signals (skew, term, DEX)
- **spot ∈ [intraday Put Wall, pTrans]** → NEGATIVE gamma zone
  → amplified moves, directional breakouts, widen stops
- **spot < intraday Put Wall** → bearish SQUEEZE, panic
  → bearish explosive vol, no fade, bearish momentum

### DEX (dealer directional pressure)
- **D+ near spot** = bullish magnet; target if spot < D+ and positive momentum
- **D- near spot** = bearish magnet; target if spot > D- and negative momentum
- **D+ and D- far from spot**: little directional urgency → follow gamma
- DEX acts as a secondary target after the gamma walls.

### VIX regime (_meta.vix_regime)
- **low** (<14): complacency, very tight ranges, strong mean-reversion, normal size
- **normal** (14-20): classic scalping
- **elevated** (20-28): widen stops 30-50%, reduce size, prefer breakouts
- **extreme** (>28): **AVOID SCALPING** — risk_alerts MANDATORY, max bias conviction "moderate"

### VIX term (_meta.vix_term)
- **backwardation** (VIX9D > VIX): immediate stress, headline news risk, breakouts likely
- **flat**: neutral
- **contango** (VIX9D < VIX): calm, mean-reversion preferred

### Macro blackout (_meta.macro_in_blackout / macro_minutes_to_next)
- **macro_in_blackout = true**: high-impact USD macro event IN PROGRESS
  → mandatory NEUTRAL rth_plan, risk_alerts MUST mention the blackout
  → one_line_summary MUST start with "MACRO BLACKOUT:"
- **macro_minutes_to_next ≤ 30**: imminent event
  → risk_alerts MUST mention event + delay + title
  → max bias conviction "moderate"
- **macro_minutes_to_next ≤ 60**: flag in rth_plan.logic

### Data quality (_meta.data_quality)
- **ok**: everything nominal, briefing reliable
- **partial**: a source missing (CBOE or CME) → flag in risk_alerts,
  mention that the briefing is "degraded quality"
- **error**: pipeline broken → all zones must be cautious,
  risk_alerts[0] = "Pipeline data ERROR — briefing reliability very low"

## rth_plan rules (MANDATORY — NEVER leave "?" placeholders)

### If gex_regime = 1 (POSITIVE, pinning), term in contango or flat
- **buy_zone** = p_trans_intraday_es (preferred) else put_wall_intraday_es else range_low_es
- **sell_zone** = c_trans_intraday_es (preferred) else call_wall_intraday_es else range_high_es
- **bullish_invalidation** = call_wall_intraday_es — beyond = bullish squeeze
- **bearish_invalidation** = put_wall_intraday_es — below = bearish squeeze

### If gex_regime = 1 but term in BACKWARDATION (immediate stress)
- **buy_zone** = range_low_es (= TastyTrade EM low if available) — wide stops
- **sell_zone** = range_high_es (= TastyTrade EM high if available)
- **bullish_invalidation** = call_wall_intraday + 0.3%
- **bearish_invalidation** = put_wall_intraday - 0.3%

### If gex_regime = -1 (NEGATIVE, explosive)
- **buy_zone** = gamma_flip (bullish break to confirm)
- **sell_zone** = gamma_flip (bearish rejection)
- **bullish_invalidation** = call_wall_intraday_es else call_wall (structural)
- **bearish_invalidation** = put_wall_intraday_es else put_wall

### DEX override (high priority if near spot)
- If dex_plus_intraday_es is between spot and initial sell_zone (<50% of distance)
  → adjust sell_zone toward dex_plus_intraday_es (closer target).
- If dex_minus_intraday_es is between spot and initial buy_zone
  → adjust buy_zone toward dex_minus_intraday_es.

### Auxiliary levels
- top_oi_intraday[0].strike_es can serve as secondary support/resistance
- charm_magnet_0dte_es near spot → afternoon scalp target

## Absolute rules
- Reply with VALID JSON ONLY, nothing else
- No markdown, no text outside JSON, no backticks
- All texts in ENGLISH
- **rth_plan: ALWAYS filled with concrete numbers, never null/0/?**
- **Always use INTRADAY metrics as primary**
- If IVR status = 'ok', include it in vol_implication
- If pin_strike_0dte is near spot (<1.5%), mention it in rth_plan.logic
- **gamma_zone MANDATORY in regime** — determine from spot position vs cTrans/pTrans/CW/PW
- Include cTrans, pTrans, D+ and D- in levels[] if they are within <2% of spot
- rth_plan.logic MUST mention the gamma_zone (positive / transition / negative / squeeze)
- **meta_context MANDATORY** — copy _meta from source JSON, never fabricate
- If _meta.vix_regime = "extreme" → risk_alerts[0] MUST mention it
- If _meta.macro_in_blackout = true → NEUTRAL rth_plan, one_line_summary starts with "MACRO BLACKOUT:"
- If _meta.macro_minutes_to_next ≤ 30 → risk_alerts MUST mention the event + delay
- If _meta.data_quality != "ok" → risk_alerts MUST mention the degradation

## JSON response format (strict)

{
  "date": "YYYY-MM-DD",
  "spot_es": 0,
  "trade_date": "YYYYMMDD",
  "generation_time": "HH:MM ET",

  "regime": {
    "gex_label": "positive" | "negative",
    "total_gex_B": 0.00,
    "total_vex_B": 0.00,
    "ivx_intraday_pct": 0.0,
    "ivr_intraday_pct": null | 0.0,
    "ivr_status": "ok" | "partial" | "insufficient",
    "skew_25d_intraday_vp": 0.0,
    "term_intraday_regime": "contango" | "backwardation" | "flat" | "unknown",
    "term_intraday_slope_vp": 0.0,
    "gamma_zone": "bullish_squeeze" | "positive" | "transition" | "negative" | "bearish_squeeze" | "unknown",
    "vol_implication": "short EN text — combine IVx + IVR (if ok) + Term + GEX + gamma_zone"
  },

  "bias": {
    "direction": "bullish" | "bearish" | "neutral",
    "conviction": "low" | "moderate" | "high",
    "reason": "short EN text — combine intraday skew + intraday term + GEX"
  },

  "levels": [
    {
      "type": "gamma_flip" | "vol_trigger" | "call_wall" | "put_wall" | "risk_pivot" | "vanna_flip" | "charm_magnet" | "max_pain" | "expected_move_high" | "expected_move_low" | "call_wall_intraday" | "put_wall_intraday" | "top_oi_intraday_1" | "top_oi_intraday_2" | "top_oi_intraday_3" | "max_pain_0dte" | "pin_strike_0dte" | "charm_magnet_0dte" | "c_trans_intraday" | "p_trans_intraday" | "dex_plus_intraday" | "dex_minus_intraday",
      "approx_price_es": 0,
      "spot_distance_pct": 0.00,
      "dealer_behavior": "short EN text"
    }
  ],

  "rth_plan": {
    "buy_zone": 0,
    "sell_zone": 0,
    "bullish_invalidation": 0,
    "bearish_invalidation": 0,
    "logic": "short EN text explaining zone choices (mention pin_strike_0dte if near spot)"
  },

  "risk_alerts": [
    "short EN text — max 3 alerts, prioritize in this order: VIX extreme, macro blackout/imminent, degraded data_quality, backwardation, high skew, extreme IVR"
  ],

  "meta_context": {
    "vix": 0.0,
    "vix_regime": "low" | "normal" | "elevated" | "extreme" | "unknown",
    "vix_term": "backwardation" | "flat" | "contango" | "unknown",
    "vix_dod_change": 0.0,
    "macro_in_blackout": false,
    "macro_next_event": "event title or null",
    "macro_minutes_to_next": -1,
    "data_quality": "ok" | "partial" | "error",
    "interpretation": "short EN text — actionable summary of VIX + macro context for today's scalping"
  },

  "one_line_summary": "short EN text — actionable intraday scalping setup with precise zones (prefix 'MACRO BLACKOUT:' if _meta.macro_in_blackout)"
}
