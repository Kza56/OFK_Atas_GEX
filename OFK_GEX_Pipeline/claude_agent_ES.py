"""
claude_agent_ES.py — Claude AI briefing agent for ES E-mini S&P500
Reads full_levels_ES.json and generates the briefing via Claude Code CLI
"""
import subprocess
import json
from pathlib import Path

from config import (
    CLAUDE_CMD, PIPELINE_ROOT,
    ES_FULL_JSON as FULL_JSON,
    ES_BRIEFING_JSON, ES_BRIEFING_RAW, ES_PROMPT_FILE,
)

PROJECT_DIR = str(PIPELINE_ROOT)


def run_briefing_ES() -> dict:
    if not FULL_JSON.exists():
        raise FileNotFoundError(f"JSON not found: {FULL_JSON}")

    prompt = (
        f"Read the file {FULL_JSON} "
        f"and apply the skill described in skills/gex_analyst_ES.md. "
        f"Return only the briefing JSON, nothing else, "
        f"no markdown, no backticks, just raw JSON."
    )

    prompt_file = ES_PROMPT_FILE
    prompt_file.write_text(prompt, encoding="utf-8")

    print("Claude Agent ES — generating briefing...")

    result = subprocess.run(
        f'type "{prompt_file}" | "{CLAUDE_CMD}" -p',
        capture_output=True,
        cwd=PROJECT_DIR,
        shell=True
    )

    prompt_file.unlink(missing_ok=True)

    try:
        stdout = result.stdout.decode("utf-8")
        stderr = result.stderr.decode("utf-8")
    except Exception:
        stdout = result.stdout.decode("cp1252", errors="replace")
        stderr = result.stderr.decode("cp1252", errors="replace")

    if result.returncode != 0:
        raise RuntimeError(f"Claude Code error:\n{stderr}")

    raw_file = ES_BRIEFING_RAW
    raw_file.write_text(stdout, encoding="utf-8")

    raw = stdout.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
    if raw.endswith("```"):
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()

    briefing = json.loads(raw)

    out = ES_BRIEFING_JSON
    out.write_text(json.dumps(briefing, indent=2, ensure_ascii=False), encoding="utf-8")

    # Versioning du briefing (pour backtest #8)
    try:
        from config import HISTORY_DIR
        bdir = HISTORY_DIR / "briefings"
        bdir.mkdir(parents=True, exist_ok=True)
        td = (briefing.get("trade_date") or "").replace("-", "")
        if td and len(td) == 8:
            (bdir / f"ES_briefing_{td}.json").write_text(
                json.dumps(briefing, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

    # Résumé console
    r = briefing.get("regime", {})
    b = briefing.get("biais",  {})

    gex_label = (r.get("gex_label") or r.get("label") or "?").upper()
    gex_B     = r.get("total_gex_B") or "?"
    direction = (b.get("direction") or "?").upper()
    conviction= b.get("conviction") or "?"
    one_liner = briefing.get("resume_une_ligne") or briefing.get("one_liner") or ""

    # Contexte _meta (VIX + macro + data_quality)
    mc = briefing.get("meta_context", {})
    vix      = mc.get("vix")
    vix_reg  = mc.get("vix_regime", "?")
    vix_term = mc.get("vix_term", "?")
    macro_bl = mc.get("macro_in_blackout", False)
    macro_ev = mc.get("macro_next_event") or "RAS"
    macro_mn = mc.get("macro_minutes_to_next", -1)
    data_q   = mc.get("data_quality", "?")

    print(f"\n{'='*62}")
    print(f"  BRIEFING ES  —  {briefing.get('date','?')}")
    print(f"{'='*62}")
    if vix is not None:
        vix_str = f"{vix:.1f}" if isinstance(vix, (int, float)) else str(vix)
        print(f"  VIX        : {vix_str} ({vix_reg})  Term: {vix_term}")
    if macro_bl:
        print(f"  Macro      : *** BLACKOUT EN COURS *** ({macro_ev})")
    elif macro_mn is not None and 0 < macro_mn <= 60:
        print(f"  Macro      : {macro_ev} dans {macro_mn}min")
    elif macro_ev != "RAS":
        print(f"  Macro      : prochain = {macro_ev}")
    print(f"  Data       : {data_q}")
    print(f"{'─'*62}")
    print(f"  GEX Regime : {gex_label}  ({gex_B}B)")
    print(f"  Biais      : {direction}  [{conviction}]")
    print(f"  >> {one_liner}")
    print(f"{'='*62}")
    print(f"  Briefing -> {out}")

    return briefing


if __name__ == "__main__":
    run_briefing_ES()
