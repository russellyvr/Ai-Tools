#!/usr/bin/env python3
"""Routing self-improvement analyzer for GitHub Copilot CLI.

Deterministic (LLM-free) KPI computation over the local session store
(~/.copilot/session-store.db) and session event logs (events.jsonl).

Outputs:
  - routing/report-latest.md   human-readable weekly report
  - routing/state.json         appended KPI snapshot history (trend data)
  - exit code 0 = all KPIs within targets, 1 = one or more KPI breaches
    (the /route-tune skill uses breaches to drive bounded self-tuning)

Usage:  python analyze_routing.py [--days N] [--quiet]
"""
import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

BASE = os.environ.get("COPILOT_HOME") or os.path.join(
    os.path.expanduser("~"), ".copilot"
)
DB = os.path.join(BASE, "session-store.db")
ROUTING = os.path.join(BASE, "routing")
TARGETS = os.path.join(ROUTING, "targets.json")
STATE = os.path.join(ROUTING, "state.json")
REPORT = os.path.join(ROUTING, "report-latest.md")
SESSIONS_DIR = os.path.join(BASE, "session-state")


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def classify_tier(model, patterns):
    if not model:
        return "UNKNOWN"
    m = model.lower()
    for tier in ("ECONOMY", "STANDARD", "FRONTIER"):
        for pat in patterns.get(tier, []):
            if re.search(pat, m):
                return tier
    return "UNKNOWN"


def query_usage(days):
    """Aggregate assistant_usage_events over the window, split main vs subagent."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    rows = con.execute(
        """SELECT model,
                  CASE WHEN COALESCE(parent_tool_call_id,'')='' AND COALESCE(agent_id,'')=''
                       THEN 'main' ELSE 'subagent' END AS role,
                  COUNT(*) AS calls,
                  SUM(COALESCE(input_tokens,0)) AS in_tok,
                  SUM(COALESCE(cache_read_tokens,0)) AS cr_tok,
                  SUM(COALESCE(cache_write_tokens,0)) AS cw_tok,
                  SUM(COALESCE(output_tokens,0)) AS out_tok,
                  SUM(COALESCE(total_nano_aiu,0)) AS aiu
           FROM assistant_usage_events
           WHERE substr(created_at,1,10) >= ?
           GROUP BY model, role""",
        (cutoff,),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def scan_task_dispatches(days):
    """Parse recent events.jsonl files for task-tool dispatches (agent_type, model, effort)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    dispatches = []
    if not os.path.isdir(SESSIONS_DIR):
        return dispatches
    for sid in os.listdir(SESSIONS_DIR):
        path = os.path.join(SESSIONS_DIR, sid, "events.jsonl")
        try:
            if not os.path.isfile(path):
                continue
            if datetime.fromtimestamp(os.path.getmtime(path), timezone.utc) < cutoff:
                continue
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if '"task"' not in line:
                        continue
                    try:
                        ev = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for tr in (ev.get("data") or {}).get("toolRequests") or []:
                        if tr.get("name") != "task":
                            continue
                        a = tr.get("arguments") or {}
                        dispatches.append({
                            "session": sid,
                            "agent_type": a.get("agent_type", "?"),
                            "model": a.get("model"),  # None = pinned/config default
                            "effort": a.get("reasoning_effort"),
                            "name": a.get("name", ""),
                        })
        except OSError:
            continue
    return dispatches


def compute(days=None, quiet=False):
    targets = load_json(TARGETS, {})
    days = days or targets.get("window_days", 7)
    patterns = targets.get("tier_patterns", {})
    kpis_t = targets.get("kpis", {})
    mech_types = set(targets.get("mechanical_agent_types", ["explore", "task"]))

    usage = query_usage(days)
    total_aiu = sum(r["aiu"] for r in usage) or 1
    frontier_aiu = sum(r["aiu"] for r in usage if classify_tier(r["model"], patterns) == "FRONTIER")
    main_rows = [r for r in usage if r["role"] == "main"]
    main_calls = sum(r["calls"] for r in main_rows) or 1
    # Cache-aware weighting (v3.1, Mac feedback §4.1): input_tokens includes
    # cache traffic; weight by price class so cheap cache reads don't inflate
    # the context-cost KPI. uncached=1.0, cache_write=1.25, cache_read=0.1.
    w = targets.get("cache_weights", {"uncached": 1.0, "cache_write": 1.25, "cache_read": 0.1})
    main_in = 0
    for r in main_rows:
        uncached = max(r["in_tok"] - r["cr_tok"] - r["cw_tok"], 0)
        main_in += (uncached * w["uncached"] + r["cw_tok"] * w["cache_write"]
                    + r["cr_tok"] * w["cache_read"])

    dispatches = scan_task_dispatches(days)
    mech = [d for d in dispatches if d["agent_type"] in mech_types]
    # A mechanical dispatch complies if it omitted model (config pin applies) or named an ECONOMY model.
    mech_econ = [d for d in mech if d["model"] is None
                 or classify_tier(d["model"], patterns) == "ECONOMY"]
    # Escalation proxy: retry-style names or explicit tier-up overrides on mechanical types.
    escalated = [d for d in mech if d["model"] is not None
                 and classify_tier(d["model"], patterns) in ("STANDARD", "FRONTIER")]

    kpis = {
        "window_days": days,
        "total_nano_aiu": total_aiu,
        "frontier_cost_share": round(frontier_aiu / total_aiu, 4),
        "avg_main_weighted_input_per_turn": round(main_in / main_calls),
        "task_dispatches": len(dispatches),
        "mechanical_dispatches": len(mech),
        "economy_share_of_mechanical_dispatches":
            round(len(mech_econ) / len(mech), 4) if mech else None,
        "subagent_escalation_rate":
            round(len(escalated) / len(mech), 4) if mech else None,
        "usage_by_model": sorted(usage, key=lambda r: -r["aiu"]),
    }

    breaches = []
    if kpis["frontier_cost_share"] > kpis_t.get("frontier_cost_share_max", 1):
        breaches.append(f"frontier_cost_share {kpis['frontier_cost_share']:.0%} > "
                        f"target {kpis_t['frontier_cost_share_max']:.0%}")
    if kpis["avg_main_weighted_input_per_turn"] > kpis_t.get("avg_main_weighted_input_per_turn_max", 10**9):
        breaches.append(f"avg_main_weighted_input/turn {kpis['avg_main_weighted_input_per_turn']:,} > "
                        f"target {kpis_t['avg_main_weighted_input_per_turn_max']:,}")
    if kpis["economy_share_of_mechanical_dispatches"] is not None and \
       kpis["economy_share_of_mechanical_dispatches"] < kpis_t.get("economy_share_of_mechanical_dispatches_min", 0):
        breaches.append(f"economy_share_of_mechanical {kpis['economy_share_of_mechanical_dispatches']:.0%} < "
                        f"target {kpis_t['economy_share_of_mechanical_dispatches_min']:.0%}")
    if kpis["subagent_escalation_rate"] is not None and \
       kpis["subagent_escalation_rate"] > kpis_t.get("subagent_escalation_rate_max", 1):
        breaches.append(f"subagent_escalation_rate {kpis['subagent_escalation_rate']:.0%} > "
                        f"target {kpis_t['subagent_escalation_rate_max']:.0%} (pins may be too cheap)")

    snapshot = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kpis": {k: v for k, v in kpis.items() if k != "usage_by_model"},
        "breaches": breaches,
    }
    state = load_json(STATE, {"snapshots": []})
    state["snapshots"] = (state.get("snapshots") or [])[-51:] + [snapshot]
    os.makedirs(ROUTING, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)

    prev = state["snapshots"][-2]["kpis"] if len(state["snapshots"]) > 1 else None
    write_report(kpis, kpis_t, breaches, prev)
    if not quiet:
        print(open(REPORT, encoding="utf-8").read())
    return 1 if breaches else 0


def trend(cur, prev, key, pct=False):
    if prev is None or prev.get(key) is None or cur.get(key) is None:
        return ""
    d = cur[key] - prev[key]
    if d == 0:
        return " (=)"
    arrow = "up" if d > 0 else "down"
    return f" ({arrow} {abs(d):.1%})" if pct else f" ({arrow} {abs(d):,})"


def write_report(kpis, targets, breaches, prev):
    fmt_pct = lambda v: "n/a" if v is None else f"{v:.1%}"
    lines = [
        "# Model Routing Report",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')} | window: {kpis['window_days']}d",
        "",
        "## KPIs vs targets",
        "| KPI | Actual | Target | Status |",
        "|---|---|---|---|",
        f"| Frontier cost share | {fmt_pct(kpis['frontier_cost_share'])}"
        f"{trend(kpis, prev, 'frontier_cost_share', pct=True)} | "
        f"<= {targets.get('frontier_cost_share_max', 1):.0%} | "
        f"{'BREACH' if kpis['frontier_cost_share'] > targets.get('frontier_cost_share_max', 1) else 'ok'} |",
        f"| Avg main weighted input/turn | {kpis['avg_main_weighted_input_per_turn']:,}"
        f"{trend(kpis, prev, 'avg_main_weighted_input_per_turn')} | "
        f"<= {targets.get('avg_main_weighted_input_per_turn_max', 0):,} | "
        f"{'BREACH' if kpis['avg_main_weighted_input_per_turn'] > targets.get('avg_main_weighted_input_per_turn_max', 10**9) else 'ok'} |",
        f"| Economy share of mechanical dispatches | {fmt_pct(kpis['economy_share_of_mechanical_dispatches'])} | "
        f">= {targets.get('economy_share_of_mechanical_dispatches_min', 0):.0%} | "
        f"{'BREACH' if kpis['economy_share_of_mechanical_dispatches'] is not None and kpis['economy_share_of_mechanical_dispatches'] < targets.get('economy_share_of_mechanical_dispatches_min', 0) else 'ok'} |",
        f"| Subagent escalation rate | {fmt_pct(kpis['subagent_escalation_rate'])} | "
        f"<= {targets.get('subagent_escalation_rate_max', 1):.0%} | "
        f"{'BREACH' if kpis['subagent_escalation_rate'] is not None and kpis['subagent_escalation_rate'] > targets.get('subagent_escalation_rate_max', 1) else 'ok'} |",
        "",
        f"Task dispatches: {kpis['task_dispatches']} total, {kpis['mechanical_dispatches']} mechanical.",
        "",
        "## Cost by model",
        "| Model | Role | Calls | Input(uncached) | CacheRead | Output | nano-AIU |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in kpis["usage_by_model"][:12]:
        unc = max(r["in_tok"] - r.get("cr_tok", 0) - r.get("cw_tok", 0), 0)
        lines.append(f"| {r['model']} | {r['role']} | {r['calls']} | "
                     f"{unc:,} | {r.get('cr_tok', 0):,} | {r['out_tok']:,} | {r['aiu']:,} |")
    lines += ["", "## Breaches"]
    lines += [f"- {b}" for b in breaches] or ["- none"]
    lines += ["", "_Run `/route-tune` in Copilot CLI to review and apply bounded self-tuning._", ""]
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=None)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    sys.exit(compute(days=a.days, quiet=a.quiet))
