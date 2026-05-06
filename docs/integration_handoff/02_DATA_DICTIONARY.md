# 02 — Data Dictionary: each metric explained

## CME structural levels (49d+)

### `gamma_flip` — Gamma Flip

- **Definition**: Strike where market makers' net gamma exposure (GEX) flips from positive to negative.
- **Calculation**: Linear interpolation of cumulative GEX profile (call GEX + put GEX) per strike; the first zero-crossing starting from spot.
- **Source**: CME NQ/ES options (OI × gamma × contract × 100), 49d+ expirations.
- **Unit**: NQ price (or ES).
- **Typical range**: 500-2000 pts from spot.
- **Missing value**: `0` if no crossing found (rare, extremely directional market).
- **Directional interpretation**:
  - Spot **above** Gamma Flip → **positive gamma**: dealers buy dips / sell rallies = stabilized market, range-bound.
  - Spot **below** → **negative gamma**: dealers amplify the move = elevated volatility, possible trend.
  - This is the **most important level** in the system — it determines the volatility regime.

### `vol_trigger` — Vol Trigger

- **Definition**: First strike above spot where GEX is significantly positive.
- **Calculation**: First strike `>= spot` with `GEX > threshold` (positive GEX).
- **Source**: CME NQ/ES options, 49d+.
- **Unit**: NQ price.
- **Typical range**: 0-500 pts above spot.
- **Interpretation**:
  - Spot above Vol Trigger → reduced volatility (dealers hedge against the move).
  - Spot below → unconstrained volatility.

### `call_wall` — Call Wall (CME structural)

- **Definition**: Strike with maximum positive GEX (largest concentration of call gamma sold by dealers).
- **Calculation**: `argmax(GEX)` over all CME 49d+ strikes.
- **Source**: CME.
- **Unit**: NQ price.
- **Typical range**: 500-3000 pts above spot.
- **Interpretation**:
  - Acts as a **major resistance**. Price struggles to break above.
  - If broken → short squeeze, bullish gamma explosion.
  - `call_wall_gex` gives the wall's magnitude (larger = stronger resistance).

### `put_wall` — Put Wall (CME structural)

- **Definition**: Strike with the strongest negative GEX (largest concentration of put gamma).
- **Calculation**: `argmin(GEX)` over all CME 49d+ strikes.
- **Source**: CME.
- **Unit**: NQ price.
- **Typical range**: 500-3000 pts below spot.
- **Interpretation**:
  - Acts as a **major support**. Price often bounces.
  - If broken → crash, bearish gamma cascade.
  - `put_wall_gex` gives the magnitude (always negative).

### `risk_pivot` — Risk Pivot

- **Definition**: First strike below spot where GEX becomes strongly negative.
- **Calculation**: First strike `< spot` with `GEX < -threshold`.
- **Unit**: NQ price.
- **Interpretation**: "Regime change" zone — if price drops below the Risk Pivot, dealers shift to amplification mode and volatility explodes.

### `vanna_flip` — Vanna Flip

- **Definition**: Strike where net Vanna exposure (VEX) flips sign.
- **Calculation**: Zero-crossing of cumulative VEX profile.
- **Source**: CME, 49d+ expirations.
- **Unit**: NQ price.
- **Interpretation**:
  - Vanna = delta sensitivity to implied vol.
  - Above Vanna Flip with falling IV → buying flow (dealers hedge by buying the underlying).
  - Below with rising IV → selling flow.

### `charm_magnet` — Charm Magnet

- **Definition**: Strike with the largest absolute Charm exposure (CEX).
- **Calculation**: `argmax(|CEX|)` over CME strikes.
- **Unit**: NQ price.
- **Interpretation**:
  - Charm = delta variation with time (theta on delta).
  - The Charm Magnet attracts price at **end of day** (last RTH hour).
  - More relevant on 0DTE (see `charm_magnet_0dte`).

---

## CBOE intraday levels (0-7 DTE)

### `call_wall_intraday_nq` / `put_wall_intraday_nq`

- **Definition**: Same concepts as CME Call/Put Wall but computed on short expirations (0-7 DTE, CBOE QQQ/SPY).
- **Calculation**: `argmax(GEX)` / `argmin(GEX)` over CBOE 0-7 DTE chain.
- **Unit**: NQ price (converted from QQQ via ratio).
- **Typical range**: 50-500 pts from spot (much tighter than CME structural).
- **Interpretation**: **Intraday** support/resistance — relevant for 5-30 min scalping. Changes on every CBOE refresh (5 min).

### `c_trans_intraday_nq` / `p_trans_intraday_nq` — Transition Levels

- **Definition**: Intraday gamma transition strikes.
- **Calculation**:
  - `c_trans`: first strike above spot where call GEX dominates put GEX (transition into positive gamma).
  - `p_trans`: first strike below spot where put GEX dominates (transition into negative gamma).
- **Unit**: NQ price.
- **Interpretation**: Define the **5 gamma zones**:
  1. Above intraday Call Wall → Squeeze+ (very bullish)
  2. Between C-Trans and intraday Call Wall → Positive gamma (mean-reversion)
  3. Between P-Trans and C-Trans → Transition zone (neutral)
  4. Between intraday Put Wall and P-Trans → Negative gamma (trend)
  5. Below intraday Put Wall → Squeeze- (very bearish)

### `dex_plus_intraday_nq` / `dex_minus_intraday_nq` — DEX Levels

- **Definition**: Strikes with the largest positive/negative delta exposure (DEX).
- **Calculation**: `argmax(DEX)` / `argmin(DEX)` over CBOE 0-7 DTE chain.
- **Unit**: NQ price.
- **Interpretation**:
  - `D+`: zone where dealers are most long delta → price is "attracted" to this level by hedging.
  - `D-`: zone where dealers are most short delta → same attraction effect.
  - Act as **magnets** for price.
  - `dex_plus_intraday_dex` / `dex_minus_intraday_dex`: DEX magnitude at this strike.

### `abs_gex_intraday_1/2/3_nq` — Abs GEX (Pin Risk)

- **Definition**: The 3 strikes with the highest |GEX| (regardless of sign).
- **Calculation**: Top-3 of `|GEX|` over CBOE 0-7 DTE chain.
- **Unit**: NQ price.
- **Interpretation**:
  - **Pinning** zones — price tends to stagnate ("pin") at these levels because dealer hedging creates a stabilizing feedback.
  - The higher the |GEX|, the stronger the pinning effect.

### `gex_wall_ext_1/2/3/4_nq` — Extended GEX Walls

- **Definition**: 4 additional GEX levels beyond the main walls.
- **Calculation**: Sort all strikes by |GEX|, exclude main walls, select the next 4.
- **Unit**: NQ price.
- **Field `_side`**: `"call"` or `"put"` — indicates whether the wall is dominated by calls (resistance) or puts (support).
- **Interpretation**: Secondary support/resistance levels. Useful when price moves beyond the main walls.

---

## 0DTE metrics

### `max_pain_0dte_nq`

- **Definition**: Strike that minimizes total 0DTE option value (maximum pain point for option buyers).
- **Calculation**: For each strike, sum of call + put losses → the minimum.
- **Unit**: NQ price.
- **Interpretation**: Price tends toward Max Pain at end of day (especially expiration Fridays).

### `pin_strike_0dte_nq`

- **Definition**: 0DTE strike with the highest gamma.
- **Calculation**: `argmax(gamma)` over the 0DTE chain.
- **Unit**: NQ price.
- **Interpretation**: Maximum intraday pinning zone — relevant for afternoon scalping.

### `charm_magnet_0dte_nq`

- **Definition**: 0DTE strike with the highest |charm|.
- **Unit**: NQ price.
- **Interpretation**: End-of-day magnet for 0DTE expirations.

---

## Volatility metrics

### `atm_iv_intraday` — Intraday ATM IV

- **Definition**: Weighted at-the-money implied volatility, computed on CBOE 0-7 DTE expirations.
- **Calculation**: IV of the strike closest to spot for the front expiration (0-7 DTE), vega-weighted.
- **Unit**: decimal ratio (e.g. `0.22` = 22% annualized).
- **Typical range**: 0.10 – 0.60.

### `skew_25d_intraday` — Skew 25Δ

- **Definition**: IV difference between 25-delta puts and 25-delta calls.
- **Calculation**: `IV(put 25Δ) - IV(call 25Δ)` on CBOE front expiration.
- **Unit**: ratio (vol points). E.g. `0.033` = 3.3 vol points.
- **Typical range**: 0.00 – 0.15.
- **Interpretation**:
  - High skew (>5 vp) → strong demand for downside protection → risk-off sentiment.
  - Low skew (<2 vp) → complacency, low put demand.
  - `skew_25d_intraday_dte`: DTE of the expiration used.

### `term_intraday_regime` — IV term structure

- **Definition**: Slope of the IV term structure between front and back expirations (0-7 DTE).
- **Calculation**: `IV(back) - IV(front)`; if negative = backwardation, positive = contango.
- **Values**:
  - `"contango"`: IV front < IV back → normal, no immediate stress.
  - `"backwardation"`: IV front > IV back → near-term stress (traders pay more for immediate protection).
  - `"flat"`: slope < 0.005 in absolute value.
  - `"unknown"`: insufficient data.
- **`term_intraday_slope`**: numeric slope value (positive = contango, negative = backwardation… **note**: in the JSON, it's `back - front`, so positive = contango).

### `iv_rank_intraday` — IV Rank (IVR)

- **Definition**: Percentile of current IV relative to the last 252 trading days.
- **Calculation**: `IVR = (IV_current - IV_min_252d) / (IV_max_252d - IV_min_252d) × 100`.
- **Unit**: percent (0-100).
- **Sub-fields**:
  - `ivr`: the value (0-100).
  - `status`: `"ok"` (≥20 days history), `"partial"` (5-19), `"insufficient"` (<5).
  - `iv_min`, `iv_max`: window bounds.
  - `n_samples`: number of days of history available.
- **Interpretation**:
  - IVR > 80 → IV high relative to history → potential vol mean-reversion.
  - IVR < 20 → IV low → potential expansion.

---

## VIX context

### `vix` / `vix9d`

- **Definition**: VIX index (30-day) and VIX9D (9-day) from Yahoo Finance.
- **Unit**: index points.
- **Typical range**: VIX 10-45, VIX9D 8-50.

### `vix_regime`

- **Definition**: VIX level classification.
- **Values**:
  - `"low"`: VIX < 14 → complacency.
  - `"normal"`: 14-20 → normal conditions.
  - `"elevated"`: 20-28 → moderate stress, scores attenuated (×0.6).
  - `"extreme"`: > 28 → crash/panic, Context Score forced to 0.

### `vix_term`

- **Definition**: VIX term structure (9d vs 30d).
- **Values**:
  - `"contango"`: VIX9D < VIX → normal, no panic.
  - `"backwardation"`: VIX9D > VIX + 0.5 → near-term fear.
  - `"flat"`: spread < 0.5.

### `vix_dod_change`

- **Definition**: Day-over-day VIX change.
- **Unit**: points.
- **Interpretation**: rise > 2 pts = significant fear move.

---

## Macro context

### `macro_in_blackout`

- **Definition**: `true` if a high-impact USD macro event is within a ±30 minute window.
- **Source**: Forex Factory calendar (USD, High/Medium impact).
- **Interpretation**: During a blackout, Context Score is forced to 0 (event risk too high).

### `macro_next_event`

- **Definition**: Next USD macro event.
- **Sub-fields**: `title`, `datetime_utc`, `impact`, `forecast`, `previous`.
- **`macro_minutes_to_next`**: minutes until the next event. If ≤ 30 → blackout.

---

## Aggregate Greeks

### `total_gex` — Total Gamma Exposure

- **Definition**: Sum of GEX over all strikes.
- **Unit**: dollars (raw value, typically 10⁹ – 10¹¹).
- **Interpretation**: Positive total GEX → positive gamma regime (stabilizing). Negative → negative gamma regime (amplifying).

### `total_vex` — Total Vanna Exposure

- **Definition**: Sum of Vanna exposure.
- **Interpretation**: Positive VEX → if IV falls, dealers buy spot (bullish). Negative VEX → opposite.

### `total_cex` — Total Charm Exposure

- **Definition**: Sum of Charm exposure.
- **Interpretation**: Indicates the magnitude of the end-of-day "gravitational pull".

### `total_dex` — Total Delta Exposure

- **Definition**: Sum of net dealer delta exposure.
- **Interpretation**: Positive DEX → net long dealers → passive bullish bias.

### `gex_regime` / `vex_regime`

- **Definition**: Sign of total GEX/VEX.
- **Values**: `1` (positive) or `-1` (negative).
- **Interpretation**:
  - `gex_regime = 1` → dealers dampen moves (range).
  - `gex_regime = -1` → dealers amplify moves (trend).
