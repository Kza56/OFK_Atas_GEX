# Translation Glossary — OFK_Atas_GEX FR → EN

This glossary captures the terminology decisions used to translate all `.md`
files in the repo. It must be reused as-is for the `.py` and `.cs` files in the
upcoming Claude Code pass to keep the whole codebase consistent.

---

## 1. JSON keys (briefing files)

These are the keys written by `claude_agent_*.py` into `briefing_*.json` (the
`full_levels_*.json` keys are already English and must NOT be touched).

| FR (current) | EN (target) | Notes |
|--------------|-------------|-------|
| `heure_generation` | `generation_time` | string `"HH:MM ET"` |
| `biais` | `bias` | object root |
| `niveaux` | `levels` | array root |
| `prix_nq_approx` | `approx_price_nq` | per-level field |
| `prix_es_approx` | `approx_price_es` | per-level field |
| `prix_nq` | `price_nq` | legacy |
| `prix_es` | `price_es` | legacy |
| `distance_spot_pct` | `spot_distance_pct` | per-level field |
| `comportement_dealers` | `dealer_behavior` | per-level field |
| `commentaire` | `comment` | when used as field name |
| `implication_vol` | `vol_implication` | regime field |
| `raison` | `reason` | bias field |
| `plan_rth` | `rth_plan` | object root |
| `zone_achat` | `buy_zone` | rth_plan field |
| `zone_vente` | `sell_zone` | rth_plan field |
| `invalidation_haussiere` | `bullish_invalidation` | rth_plan field |
| `invalidation_baissiere` | `bearish_invalidation` | rth_plan field |
| `logique` | `logic` | rth_plan field |
| `alertes_risque` | `risk_alerts` | array root |
| `resume_une_ligne` | `one_line_summary` | string root |
| `range_bas_nq` / `range_haut_nq` | `range_low_nq` / `range_high_nq` | already in `full_levels_*.json` too |
| `range_bas_es` / `range_haut_es` | `range_low_es` / `range_high_es` | same |
| `range_bas_qqq` / `range_haut_qqq` | `range_low_qqq` / `range_high_qqq` | same |
| `range_bas_spy` / `range_haut_spy` | `range_low_spy` / `range_high_spy` | same |

## 2. JSON enum values

| FR (current) | EN (target) | Field |
|--------------|-------------|-------|
| `"haussier"` | `"bullish"` | bias.direction |
| `"baissier"` | `"bearish"` | bias.direction |
| `"neutre"` | `"neutral"` | bias.direction |
| `"positif"` | `"positive"` | regime.gex_label |
| `"négatif"` / `"negatif"` | `"negative"` | regime.gex_label |
| `"faible"` | `"low"` | bias.conviction |
| `"modérée"` / `"moderee"` | `"moderate"` | bias.conviction |
| `"forte"` | `"high"` | bias.conviction |
| `"squeeze_haussier"` | `"bullish_squeeze"` | regime.gamma_zone |
| `"squeeze_baissier"` | `"bearish_squeeze"` | regime.gamma_zone |

## 3. String prefixes

| FR (current) | EN (target) |
|--------------|-------------|
| `"BLACKOUT MACRO :"` | `"MACRO BLACKOUT:"` |

## 4. Common comment / docstring vocabulary

| FR | EN |
|----|----|
| niveau / niveaux | level / levels |
| chargé / non chargé | loaded / not loaded |
| écraser / écrasé | overwrite / overwritten |
| écrit / écriture | written / writing |
| lecture / lit | read / reads |
| rafraîchir / refresh | refresh |
| stale | stale (kept) |
| obligatoire | mandatory / required |
| facultatif / optionnel | optional |
| défaut / par défaut | default |
| seuil | threshold |
| fourchette / plage | range |
| règle | rule |
| règles absolues | absolute rules |
| zone d'achat / vente | buy zone / sell zone |
| haussier / baissier | bullish / bearish |
| comprimée | compressed |
| expansion | expansion |
| amplifiée | amplified |
| amortie / dampened | dampened |
| pinning, dealers, scalping, fade, squeeze | (preserved as-is, English jargon) |
| matin / matinal | morning |
| journée | day |
| séance | session |
| ouverture / fermeture | open / close |
| jour férié | holiday |
| boucle | loop |
| cycle | cycle |
| échec / échoué | fail / failed |
| timeout | timeout (kept) |
| données | data |
| dégradé | degraded |
| santé pipeline | pipeline health |
| corrompu | corrupt |
| historique | history / historical |
| snapshot | snapshot (kept) |
| rétention | retention |
| consommateur | consumer |
| émetteur / écrivain | writer |

## 5. Status / regime values (other than enum already listed)

| FR | EN |
|----|----|
| `"qualité dégradée"` | `"degraded quality"` |
| `"fiabilité briefing très basse"` | `"briefing reliability very low"` |
| `"Données pipeline EN ERREUR"` | `"Pipeline data ERROR"` |
| `"En cours"` | `"In progress"` |
| `"Aucun"` / `"Aucune"` | `"None"` |
| `"Inconnu"` | `"Unknown"` |
| `"OK"` | `"OK"` (kept) |
| `"PARTIEL"` | `"PARTIAL"` |
| `"ERREUR"` | `"ERROR"` |

## 6. ATAS UI strings (`[Display(Name=...)]`, `[Description=...]`, `GroupName=...`)

These are visible to traders. Translate every one of them to English. Keep
group prefixes like `01.`, `02.` to preserve display ordering.

| FR pattern | EN pattern |
|------------|------------|
| `"01.Source"` | `"01.Source"` (kept) |
| `"02.Affichage"` | `"02.Display"` |
| `"03.Couleurs"` | `"03.Colors"` |
| `"04.Alertes"` | `"04.Alerts"` |
| `"05.Replay"` | `"05.Replay"` (kept) |
| `"06.Avancé"` | `"06.Advanced"` |
| `"Refresh (min)"` | `"Refresh (min)"` (kept) |
| `"Afficher ..."` | `"Show ..."` |
| `"Masquer ..."` | `"Hide ..."` |
| `"Activer ..."` | `"Enable ..."` |
| `"Désactiver ..."` | `"Disable ..."` |
| `"Couleur ..."` | `"Color ..."` |
| `"Épaisseur"` | `"Thickness"` |
| `"Taille police"` | `"Font size"` |
| `"Étiquette"` | `"Label"` |
| `"Niveau"` | `"Level"` |
| `"Seuil"` | `"Threshold"` |
| `"Décalage"` | `"Offset"` |
| `"Bouton ..."` | `"Button ..."` |
| `"Bannière ..."` | `"Banner ..."` |
| `"Panneau ..."` | `"Panel ..."` |

## 7. ATAS log / alert / banner messages

These appear at runtime in ATAS. All to be translated.

Examples:

| FR | EN |
|----|----|
| `"JSON chargé"` | `"JSON loaded"` |
| `"JSON non chargé — vérifier JSON Path"` | `"JSON not loaded — check JSON Path"` |
| `"JSON rechargé"` | `"JSON reloaded"` |
| `"Loop intraday actif mais JSON figé"` | `"Intraday loop active but JSON frozen"` |
| `"vérifier le process Python"` | `"check the Python process"` |
| `"pipeline désynchro indicateur"` | `"pipeline schema desync vs indicator"` |
| `"≠ attendu"` | `"≠ expected"` |
| `"chargé"` (suffix) | `"loaded"` |

## 8. Things to leave as-is

- Variable names, function names, class names, file names
- ATAS API types and enums (`DrawingLayouts.Historical`, `IndicatorDataProvider.NewPanel`, etc.)
- Trading jargon: `pinning`, `dealers`, `scalping`, `fade`, `squeeze`, `walls`, `flip`, `term`, `skew`, `ATM`, `OTM`, `straddle`, `strangle`, `0DTE`, `DTE`, `OI`, `IV`, `IVR`, `RTH`, `ETH`
- Ticker / contract codes: NQ, ES, QQQ, SPY, VIX, VIX9D
- File paths and directory names
- Code identifiers in any language

## 9. Backward-compat reading rules

The Python readers in `claude_agent_*.py`, `generate_pdf_*.py`, and
`backtest_briefings.py` already accept BOTH French and English keys, e.g.:

```python
b = briefing.get("bias", briefing.get("biais", {}))
levels_key = "levels" if "levels" in briefing else "niveaux"
```

**Keep this dual-read pattern** so that existing French snapshots in
`data/history/briefings/` and `data/samples/` continue to render correctly. New
snapshots will be written with English keys only.
