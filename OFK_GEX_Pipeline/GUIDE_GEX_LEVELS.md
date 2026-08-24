# User Guide — OFK Suite GEX Levels

Reference document to understand the levels displayed on your NQ and ES
charts, how to use them for intraday scalping, and which ones matter for
swing trading.

---

## 1. The basics: why options move the futures

### Market makers (MM) and hedging

When you trade NQ/ES, you are not only playing against other traders: you
are also playing against **option dealers** (banks, electronic MMs).

- Retail and institutional players buy options (calls, puts).
- Dealers **sell** them.
- To stay risk-neutral, dealers **hedge**: they buy or sell the underlying
  (here, NQ or ES).
- **This hedging creates the buy/sell flows** you see on the chart.

Understanding where options are concentrated = understanding where dealers
will buy/sell = understanding the chart's key levels.

### The core concept: positive vs negative GEX

**GEX** (Gamma Exposure) measures how strongly dealers react to each price
move.

- **Positive GEX** (dealers long gamma):
  - Price goes up → dealers **sell** to stay neutral.
  - Price goes down → dealers **buy**.
  - Effect: they **dampen** moves.
  - Consequence: tight ranges, mean-reversion, pinning.

- **Negative GEX** (dealers short gamma):
  - Price goes up → dealers **buy** to stay neutral.
  - Price goes down → dealers **sell**.
  - Effect: they **amplify** moves.
  - Consequence: violent breakouts, momentum, explosive vol.

> **Today (panel)**: if GEX +33B → market in pinning / range / mean-reversion
> mode. If GEX turns negative → we switch to "expansion" mode and respect
> breakouts.

---

## 2. CME structural levels (long term, ~49 DTE)

These levels **change little during the day**. They are the **macro anchors**
valid for the full session, sometimes for several days.

### Gamma Flip ⭐⭐⭐⭐⭐ (most important)

- **What is it?** The price where cumulative gamma flips from positive to negative.
- **Why critical?** It is the dealer regime threshold.
- **Above Gamma Flip**: stable regime, compressed vol, ranges.
- **Below**: unstable regime, explosive vol, violent breakouts.
- **Strength**: ⭐⭐⭐⭐⭐ scalping AND swing.
- **How to trade it?**
  - Clean break to the downside → regime flip, **gamma_flip alert
    triggered**, wait for confirmation then follow.
  - First touch from above → possible fade (support test).
  - Often a hard S/R — can bounce several times.

### Vol Trigger ⭐⭐⭐⭐

- **What is it?** Strike where put gamma becomes dominant.
- **Read**: breaking down = vol about to explode. Breaking up = back to calm zone.
- **How to trade it?** Confluence with Gamma Flip = powerful setup.

### Call Wall (CME structural) ⭐⭐⭐⭐ swing / ⭐⭐⭐ scalping

- **What is it?** The strike with the **largest call gamma** (call option
  where dealers have the most exposure).
- **Effect**: upside magnet (dealers sell to defend it).
- **How to trade it?**
  - Scalping: the intraday version is more relevant (see section 3).
  - Swing: strong ceiling level over several days/weeks.
  - Clean break + close above → bullish squeeze (rare, follow).

### Put Wall (CME structural) ⭐⭐⭐⭐ swing / ⭐⭐⭐ scalping

- Mirror of the Call Wall, below. Strong floor, primary support.
- Clean break = bearish squeeze.

### Risk Pivot (trapdoor) ⭐⭐⭐

- **What is it?** Level below which risk accelerates dramatically.
- **Trading**: invalidation level for swing longs. If broken to the
  downside, the market can drop hard (negative gamma amplifies).

### Vanna Flip ⭐⭐⭐

- **What is it?** Level where vanna changes sign (gamma's sensitivity to vol).
- **Trading**: useful in swing to anticipate regime flips when vol moves.
  Secondary in pure scalping.

### Charm Magnet (CME 49d) ⭐⭐

- **What is it?** Strike toward which delta decay drags the price.
- More useful in swing (over multiple expirations). For scalping, prefer
  the 0DTE version.

### Structural Top OI #1, #2, #3 ⭐⭐ swing

- **What is it?** The 3 strikes with the largest open interest, all
  expirations combined.
- **Trading**: market "memory" levels, often historical S/R. Interesting
  confluence but not a trigger on their own.

---

## 3. CBOE intraday levels (0-7 DTE) — the heart of scalping

⚠️ **These levels are the most important for your scalping style.**

They use 0 to 7-day expiration options, which have the strongest impact on
intraday price because their gamma is the most concentrated.

> **Technical note**: the pipeline reads QQQ options (for NQ) or SPY (for
> ES), then converts strikes via the current NQ/QQQ or ES/SPY ratio. You
> see levels already converted to NQ/ES points.

### Intraday Call Wall ⭐⭐⭐⭐⭐

- **What is it?** The Call Wall, but on 0-7 DTE options.
- **Scalping strength**: ⭐⭐⭐⭐⭐ — one of your 2-3 primary levels.
- **Behavior**:
  - Approach from below → **strong resistance**, MMs sell NQ to defend.
  - First rejection → short setup, short duration (2:1 ratio).
  - Clean break + close above → bullish squeeze, flip to long.
- **Winning combo**: Call Wall ID + POSITIVE gamma zone + low VIX → fade
  the approach, target Pin 0DTE or cTrans below.

### Intraday Put Wall ⭐⭐⭐⭐⭐

- Mirror: primary intraday support.
- **Approach from above** → **long bounce**.
- **Clean break** + close below → bearish squeeze, flip to short.

### cTrans (call gamma transition) ⭐⭐⭐⭐

- **What is it?** The strike where cumulative net gamma exceeds +10%.
- **Read**: upper bound of the "transition" zone (not yet call-dominated).
- **Above**: POSITIVE gamma zone → mean-reversion possible.
- **Below** (but > pTrans): TRANSITION zone → neutral.

### pTrans (put gamma transition) ⭐⭐⭐⭐

- Mirror: lower bound of the "transition" zone.
- **Below**: NEGATIVE gamma zone → breakouts possible.
- **Above**: TRANSITION zone → neutral.

### D+ DEX (Delta Exposure +) ⭐⭐⭐⭐

- **What is it?** Strike with the largest cumulative call delta (dealers
  buy NQ to hedge).
- **Effect**: upside magnet — dealer buy flow drags price toward it.
- **Trading idea**: if spot < D+, wait for it to approach → moderate long
  bias (hedging pulls toward the strike).

### D- DEX (Delta Exposure -) ⭐⭐⭐⭐

- **What is it?** Strike with the largest cumulative put delta (dealers
  sell NQ to hedge).
- **Effect**: downside magnet.
- **Trading idea**: if spot > D-, wait for it to approach → moderate short
  bias.

### Intraday Top OI #1, #2, #3 ⭐⭐⭐

- The 3 0-7d strikes with the largest OI.
- Often confluent with intraday Call/Put Wall — confirmation.
- Use as **confluence levels**, not as standalone triggers.

### Abs GEX 1, 2, 3 (pin risk) ⭐⭐⭐

- **What is it?** The 3 strikes with the largest absolute gamma magnitude
  (calls + puts combined).
- **Effect**: intense pinning risk.
- **Trading idea**: price approaching one of these strikes in the second
  half of the session → tight range expected, scalp the bounds Abs±20 ticks.

### GEX Ext 7, 8, 9, 10 ⭐⭐

- Strikes outside the main walls where significant gamma still exists.
- Secondary magnets.
- **Use**: confluence to validate a setup, or short-distance TP targets.

---

## 4. 0DTE levels (afternoon only)

⚠️ **Relevant only after 14:00 ET (20:00 Paris)**, when 0DTE OI becomes
dominant and decay accelerates.

### Pin Strike 0DTE ⭐⭐⭐⭐⭐ (after 14:00 ET)

- **What is it?** The strike with the largest gamma on options expiring
  today.
- **Effect**: **extremely powerful** end-of-session magnet.
- **Trading idea**:
  - If price is close (±20 ticks) → tight range expected.
  - Winning setup: fade range extreme approaches toward the Pin.
  - **DO NOT** trade breakouts in this zone — often a fakeout.
- Strength: ⭐⭐⭐⭐⭐ after 14:00 ET, ⭐ before.

### Charm Magnet 0DTE ⭐⭐⭐⭐ (last hour)

- **What is it?** Strike where charm (delta decay) is at maximum.
- **Effect**: active mainly in the last session hour, attracts price.
- Often = Pin Strike 0DTE near close.
- **Trading**: confluence with Pin Strike → "temporal resistance" level
  toward which price tends.

### Max Pain 0DTE ⭐⭐⭐ (afternoon)

- **What is it?** Strike where the largest amount of 0DTE options expire
  worthless.
- **Effect**: end-of-session magnet, but weaker than Pin Strike.
- Often confluent with Pin Strike or Charm Magnet.

---

## 5. Classic options levels

### Max Pain (all expirations) ⭐⭐

- Mirror of 0DTE but aggregated across all expirations.
- More useful in swing than scalping.

### Expected Move High / Low ⭐⭐⭐

- **What is it?** Probable range based on the ATM 0DTE straddle
  (TastyTrade method: `ATM × 0.6 + OTM1 × 0.3 + OTM2 × 0.1`).
- **Read**: 90% probability that price stays within this band for the day.
- **Trading idea**:
  - Exit from the bounds = extreme move → often a quick return to the
    zone (mean-reversion).
  - Inside → normal range.

---

## 6. Volatility context (regime, not price level)

These metrics **dictate your style** of trading. Do not ignore them.

### Intraday IVx (CBOE 0-7 DTE)

- ATM IV of near-expiration options.
- **Read**:
  - **< 12%** → very low vol, very tight ranges, **strong mean-rev**.
  - **12-20%** → normal, classic scalping.
  - **> 20%** → high vol, **widen stops**, watch for gaps.

### Structural IVx (CME 49d)

- Long-term ATM IV.
- Gives the **macro vol regime**. Not a scalping trigger.

### Skew 25Δ ⭐⭐⭐⭐

- **What is it?** IV difference between 25Δ put and 25Δ call.
- **Read** (positive = puts more expensive, defensive market):
  - **1-3 vp**: normal.
  - **3-5 vp**: caution on aggressive shorts, high hedging demand.
  - **> 5 vp**: ⚠️ **ALERT** — massive put protection today, gap-down
    possible. **Reduce short size, widen stops.**
  - **< 0 vp** (rare): market very complacent on puts, watch out.
- > Structural CME 49d skew may be inflated by illiquid OTM calls — the
> briefing PDF reminds you of this.

### Term IV (front vs back) ⭐⭐⭐⭐

- IV curve slope.
- **Backwardation** (front > back, slope > +0.5 vp) → **acute STRESS**,
  breakouts likely, careful with mean-reversion.
- **Contango** (front < back, slope < -0.5 vp) → calm, mean-reversion
  dominant. The "comfortable scalping" regime.
- **Flat** → neutral.

### IVR (IV Rank) ⭐⭐⭐

- **What is it?** Position of current IVx over the last 252 days.
- **Read**:
  - **< 30**: historically "low" vol (compress before pop possible).
  - **30-70**: normal.
  - **> 70**: "high" vol (rare, watch for squeezes).
  - **> 90**: extreme → attenuates the directional score (×0.5).
- ⚠️ If you see `IVR insufficient` (less than 5 days of history), IVR is
  not computable — let the pipeline run a few days to populate it.

---

## 7. VIX (macro regime)

VIX is your main **go/no-go filter**.

| Regime | Range | Behavior |
|--------|-------|----------|
| **low** | < 14 | complacency, tight ranges, **comfortable scalping** |
| **normal** | 14-20 | classic regime, **normal scalping** |
| **elevated** | 20-28 | **widen stops, reduce size** |
| **extreme** | > 28 | ⚠️ **AVOID scalping**, chaotic market |

VIX vs VIX9D:
- **VIX9D > VIX** (backwardation) → acute stress now, immediate vol.
- **VIX9D < VIX** (contango) → near-term vol lower than average → calm.

> The **Context Score** already includes this filter:
> - VIX `extreme` → score forced to 0 (BLOCKED).
> - VIX `elevated` → score attenuated ×0.6.

---

## 8. The 5 gamma zones (TanukiTrade-style)

Spot position relative to `Put Wall < pTrans < cTrans < Call Wall`:

| Zone | Position | Regime | Style to apply |
|------|----------|--------|----------------|
| 🟢 BULLISH SQUEEZE | spot > Call Wall | Bullish explosive vol | **Follow momentum**, no fade |
| 🟢 POSITIVE | cTrans < spot < CW | Mean-reversion | **Fade the bounds** (CW reject, cTrans bounce) |
| 🟡 TRANSITION | pTrans < spot < cTrans | Neutral | Tight range, **caution**, small size |
| 🔴 NEGATIVE | PW < spot < pTrans | Amplified vol | **Directional breakouts**, follow the move |
| 🔴 BEARISH SQUEEZE | spot < Put Wall | Bearish panic | **Follow bearish**, no fade |

**Golden rule**: adapt your strategy to the zone, not the other way around.

---

## 9. The Context Score (-100 to +100)

The separate panel "OFK NQ/ES Context Score" aggregates everything into a
**single directional score**:

| Score | Tag | Meaning |
|-------|-----|---------|
| +70 to +100 | **BULLISH HIGH** | Strong long, high conviction |
| +30 to +69 | **BULLISH** | Moderate long |
| -29 to +29 | **NEUTRAL** | Stay flat or wait |
| -69 to -30 | **BEARISH** | Moderate short |
| -100 to -70 | **BEARISH HIGH** | Strong short, high conviction |
| 0 + BLOCKED tag | **BLOCKED** | VIX extreme / macro / data error → do not trade |

This is your **macro compass**: check it before every trade. If BLOCKED or
NEUTRAL, do not force.

---

## 10. Position sizing (% to use)

The panel computes an adaptive size %:
- **100%** = normal conditions (normal VIX, ok macro, ok data).
- **< 100%**: a factor degrades conditions (high VIX, macro nearby,
  partial data).

Multiplier = `VIX × Macro × Data Quality`:
- VIX low/normal × 1.0, elevated × 0.6, extreme × 0.0.
- Macro blackout × 0.0, < 30min × 0.3, ok × 1.0.
- Data ok × 1.0, partial × 0.7, error × 0.0.

> **Example**: VIX 24 (elevated) + macro in 25min → 0.6 × 0.3 = 18%.
> You reduce your size by 82%.

---

## 11. Typical workflow — how to put it all together

### Morning (before open, ~30 min before 9:30 ET)

1. **Click `GEX LEVELS NQ`** (launches run_morning_NQ.py + reloads the panel).
2. **Read the briefing PDF** (📄 Briefing button):
   - Macro bias (BULLISH / NEUTRAL / BEARISH).
   - Key zone identified by the configured AI briefing provider (range scalp / pin / squeeze).
   - Buy/sell zones.
   - Alerts (explosive skew, term backwardation, etc.).
3. **Enable `Loop intraday: ON`** → CBOE auto-refresh every 5 min.
4. **On the chart**, identify:
   - **Intraday Call Wall + Put Wall** → day's bounds.
   - **Pin Strike 0DTE** → end-of-session magnet (watch from 14:00 ET).
   - **Gamma Flip** → regime flip level, major S/R.

### During the session (RTH 9:30-16:00 ET)

1. **Watch the Context Score**:
   - 🟢 Green (BULLISH/HIGH) → long bias.
   - 🔴 Red (BEARISH/HIGH) → short bias.
   - ⚪ Gray (NEUTRAL/BLOCKED) → **do not trade**.
2. **Identify your gamma zone** (see table in section 8).
3. **Pick your setup** based on the zone:
   - **POSITIVE** → fade intraday CW/PW approaches.
   - **NEGATIVE** → follow breakouts.
   - **TRANSITION** → tight range, minimal scalping.
   - **SQUEEZE** → follow the momentum, no fade.
4. **Confirm with vol context**:
   - Low VIX + normal skew + contango → mean-rev safe.
   - VIX > 20 + skew > 5 + backwardation → absolute caution, reduced size.
5. **Watch on-chart banners**: real-time alerts when price crosses a level
   or approaches a pin.

### Most reliable setups (strength ⭐⭐⭐⭐⭐)

1. **Intraday Put Wall bounce in POSITIVE gamma**
   - Spot approaches intraday PW from above.
   - POSITIVE zone confirmed.
   - VIX < 20.
   - → Long with stop below PW, target cTrans or EM Low.
   - **R:R ratio ≥ 2:1.**

2. **Intraday Call Wall reject in POSITIVE gamma**
   - Spot approaches intraday CW from below.
   - POSITIVE zone confirmed.
   - VIX < 20.
   - → Short with stop above CW, target cTrans or Pin 0DTE.
   - **R:R ratio ≥ 2:1.**

3. **Gamma Flip break + bar close**
   - Price cleanly breaks Gamma Flip.
   - Bar closes on the right side (no return wick).
   - → Follow the move, target the next structural level.
   - **Bias**: regime flip, scalp the momentum on 2-3 bars then reassess.

4. **Pin 0DTE after 14:00 ET (tight range)**
   - Spot within ±20 ticks of Pin Strike 0DTE.
   - POSITIVE or TRANSITION zone.
   - → Scalp the range: long on lows toward Pin, short on highs toward Pin.

### Setups to AVOID (guaranteed drawdown)

1. **Extreme VIX (>28)** → chaotic market, stay out.
2. **Macro blackout** (FOMC, NFP, CPI, ISM, FOMC Minutes) ±30 min → flat.
3. **Data quality "error"** in the panel → corrupt JSON, do not trade.
4. **Bullish/bearish squeeze in POSITIVE gamma**: counter-intuitive,
   often a fakeout.
5. **Skew > 5vp on a short**: massive put protection, gap-down possible —
   reduce size, widen stops.
6. **Trade against the gamma zone**: being short in POSITIVE without a
   strong signal = systematic counter-trend.

---

## 12. Quick cheatsheet

| Level | Scalping strength | Swing strength | Source |
|-------|:-:|:-:|--------|
| **Gamma Flip** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | CME |
| **Intraday Call Wall** | ⭐⭐⭐⭐⭐ | ⭐⭐ | CBOE 0-7d |
| **Intraday Put Wall** | ⭐⭐⭐⭐⭐ | ⭐⭐ | CBOE 0-7d |
| **Pin 0DTE** (PM) | ⭐⭐⭐⭐⭐ after 14:00 | – | CBOE 0DTE |
| Charm Magnet 0DTE | ⭐⭐⭐⭐ last hour | – | CBOE 0DTE |
| cTrans / pTrans | ⭐⭐⭐⭐ | ⭐⭐ | CBOE 0-7d |
| D+ / D- DEX | ⭐⭐⭐⭐ | ⭐⭐ | CBOE 0-7d |
| Vol Trigger | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | CME |
| Top OI ID #1 | ⭐⭐⭐ | ⭐ | CBOE 0-7d |
| Abs GEX 1/2/3 | ⭐⭐⭐ | – | CBOE 0-7d |
| Risk Pivot | ⭐⭐⭐ | ⭐⭐⭐⭐ | CME |
| Max Pain 0DTE (PM) | ⭐⭐⭐ | – | CBOE 0DTE |
| Expected Move H/L | ⭐⭐⭐ | ⭐⭐ | CBOE 0DTE |
| Structural Call Wall | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | CME |
| Structural Put Wall | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | CME |
| Top OI #1/2/3 (struct) | ⭐⭐ | ⭐⭐⭐⭐ | CBOE all-DTE |
| Vanna Flip | ⭐⭐ | ⭐⭐⭐ | CME |
| Charm Magnet (49d) | ⭐⭐ | ⭐⭐⭐ | CME |
| Max Pain | ⭐⭐ | ⭐⭐⭐ | CBOE all-DTE |
| GEX Ext 7-10 | ⭐⭐ | – | CBOE 0-7d |

### Regime cheatsheet

| Indicator | Value | Reaction |
|-----------|-------|----------|
| VIX | < 14 | comfortable scalping, tight stops OK |
| VIX | 14-20 | normal |
| VIX | 20-28 | widen stops, size -40% |
| VIX | > 28 | **FLAT, do not trade** |
| GEX | > 0 | mean-reversion, fade the bounds |
| GEX | < 0 | momentum, follow breakouts |
| Skew 25Δ | < 3 vp | normal |
| Skew 25Δ | 3-5 vp | caution on shorts |
| Skew 25Δ | > 5 vp | **ALERT** gap-down risk |
| Term | contango | calm, mean-rev OK |
| Term | flat | neutral |
| Term | backwardation | stress, breakouts likely, caution |

---

## 13. Classic pitfalls (DO NOT do)

1. **Ignore the Context Score**: the chart setup may be perfect, but if
   the score says NEUTRAL/BLOCKED, the macro context does not validate it.
   Respect the score.

2. **Trade against the gamma zone**: being short in POSITIVE without a
   strong signal = counter-trend, guaranteed drawdowns.

3. **Trade during macro blackout**: high-impact USD events move futures
   violently. ±30 min before/after → flat.

4. **Trade Pin 0DTE before 14:00 ET**: before this time, 0DTE OI is not
   yet dominant. The pin is weak, bounces are random.

5. **Ignore skew > 5 vp on a short**: market is pricing in massive put
   protection today — a trigger event can cause a brutal gap-down. Reduce
   short size, widen stops, or stay flat.

6. **Trade in acute backwardation without reducing size**: this is stress,
   drawdowns are brutal. Cut to 50% of your normal size.

7. **Trade with data_quality = error**: the pipeline could not fetch
   correctly, displayed levels may be stale. Re-run `run_morning_NQ.py`
   or wait for the next refresh.

8. **Open too many positions during a SQUEEZE**: a bullish or bearish
   squeeze = unidirectional momentum + explosive vol. One position, no
   wild pyramiding.

---

## 14. Quick glossary

- **GEX** (Gamma Exposure): aggregate sensitivity of dealer option gamma.
- **DEX** (Delta Exposure): aggregate delta sensitivity.
- **VEX** (Vega Exposure): vol sensitivity.
- **CEX** (Charm Exposure): delta sensitivity to time passage.
- **0DTE** (Zero Days To Expiration): options expiring today.
- **DTE**: Days To Expiration.
- **OI** (Open Interest): number of option contracts outstanding.
- **IV** (Implied Volatility): implied vol computed from option price.
- **ATM** (At The Money): strike = spot.
- **OTM** (Out of The Money): strike far from spot, less liquid.
- **Strike**: option exercise price.
- **Skew**: IV asymmetry between same-delta puts and calls.
- **Term structure**: IV slope as a function of time to expiration.
- **Charm**: delta decay (delta decreases over time for an OTM).
- **Vanna**: delta sensitivity to a vol change.
- **Pin risk**: risk that price gets "pinned" to a strike by dealer
  hedging at session end.
- **MM** (Market Maker) / Dealer: entity that sells options to retail and
  institutional clients, and hedges its position.

---

## 15. Going further

- The daily **Codex PDF briefing** (generated by run_morning) provides
  the detailed analysis for the upcoming session: bias, zones, alerts,
  recommended setups.
- The **intraday Replay** (🎬 button) lets you replay how levels evolved
  during a past session — useful for post-mortem.
- The **Context Score panel** gives the real-time directional score based
  on all the signals above, with detailed components (PW bounce, GF+,
  squeeze+, etc.).

> Final rule: a single level alone does not trigger a trade. **Confluence**
> (2-3 levels + gamma zone + Context Score + VIX) gives the best setups.
