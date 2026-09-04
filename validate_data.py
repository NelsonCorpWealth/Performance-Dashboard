#!/usr/bin/env python3
"""
validate_data.py - gate before commit.

The routine (Claude) pulls from YCharts and writes data.json (strategies + sleeves). Claude is
flexible; this script is strict. Nothing reaches the live dashboard unless
it passes.

    python validate_data.py data.json          -> exit 0 = safe to commit
    python validate_data.py data.json --prev old.json   (also diff)

Exit codes: 0 ok, 1 invalid, 2 file/parse error.
"""
import sys, json, datetime, argparse

EXPECTED_BENCHMARKS = ["SPYM", "DIA", "QQQ", "AGG", "UUP", "PDBC"]
EXPECTED_STRATEGIES = {
    "Conservative": 597220,
    "Moderate": 552644,
    "Aggressive": 597223,
    "Absolute Return Conservative": 604837,
    "Absolute Return Moderate": 555767,
    "Absolute Return Moderate-Aggressive": 604832,
    "All Tactical": 1297251,
    "Macro": 1729042,
    "Tax Conservative": 1146887,
    "Tax Moderate": 1146880,
    "Tax Aggressive": 1146891,
    "IA3 High Income": 1589463,
    "IA3 Cash Management": 1589508
}
EXPECTED_SLEEVES = {
    "Core Stock": 548985,
    "Tactical Stock L/S": 1141466,
    "Tactical Stock L/S (S&P)": 1470892,
    "Regional Stock L/S": 1141467,
    "Defined Risk": 1145523,
    "Big Picture L/S (SPHB/USMV)": 1184181,
    "Bond Duration L/S (XLK/XLE)": 1271763,
    "Dollar L/S (AMLP/GDX)": 1195046,
    "Economic Regime": 1962097,
    "Real Estate": 1145687,
    "Commodity": 1146127,
    "Dollar": 1146153,
    "Core Bond 1": 548980,
    "Tax Core Stock": 1146835,
    "Tax Tactical Stock": 1146853,
    "Tax Tactical Stock L/S": 1146860,
    "Tax Regional Stock": 1146845,
    "Tax Var Rate Preferred": 1534983,
    "Tax Core Bond BOXX": 1277723,
    "Tax Int-Term Muni 1": 1277725
}
WEIGHT_TOL = 0.005          # each model must sum to 1.0 +/- this
MAX_AS_OF_AGE_DAYS = 5      # covers a long weekend + holiday
YTD_SANE = (-0.60, 1.50)    # -60% .. +150%; outside this is almost surely a parse error
PCT_LEAK = 1.5              # a YTD > 150% probably means percent wasn't converted to decimal


def fail(msgs):
    for m in msgs: print("FAIL:", m)
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--prev", help="previous data.json to diff against")
    a = ap.parse_args()

    try:
        d = json.load(open(a.path, encoding="utf-8"))
    except Exception as e:
        print("FAIL: cannot read/parse:", e); return 2

    errs, warns = [], []

    # --- as-of date ---
    as_of = d.get("ytd_as_of") or d.get("as_of")
    if not as_of:
        errs.append("missing ytd_as_of")
    else:
        try:
            dt = datetime.date.fromisoformat(as_of)
            age = (datetime.date.today() - dt).days
            if age < 0: errs.append(f"as_of {as_of} is in the future")
            elif age > MAX_AS_OF_AGE_DAYS: errs.append(f"as_of {as_of} is {age} days old (max {MAX_AS_OF_AGE_DAYS})")
            if dt.weekday() >= 5: warns.append(f"as_of {as_of} falls on a weekend")
        except ValueError:
            errs.append(f"as_of {as_of!r} is not YYYY-MM-DD")

    # --- benchmarks ---
    b = d.get("benchmarks")
    if not isinstance(b, list): errs.append("benchmarks missing")
    else:
        tick = [str(x.get("ticker","")).upper() for x in b]
        if tick != EXPECTED_BENCHMARKS:
            errs.append(f"benchmark tickers {tick} != expected {EXPECTED_BENCHMARKS}")
        for x in b:
            y = x.get("ytd")
            if y is None: errs.append(f"benchmark {x.get('name')} has no ytd")
            elif not isinstance(y,(int,float)): errs.append(f"benchmark {x.get('name')} ytd not numeric")
            elif abs(y) > PCT_LEAK: errs.append(f"benchmark {x.get('name')} ytd={y} looks like percent, not decimal")
            elif not (YTD_SANE[0] <= y <= YTD_SANE[1]): warns.append(f"benchmark {x.get('name')} ytd={y:.4f} unusual")

    # --- strategies + sleeves ---
    def check_list(key, expected):
        m = d.get(key)
        if not isinstance(m, list): errs.append(f"{key} missing"); return []
        names = [x.get("name") for x in m]
        if names != list(expected):
            errs.append(f"{key} names/order {names} != expected {list(expected)}")
        for x in m:
            n = x.get("name")
            if x.get("portfolio_id") != expected.get(n):
                errs.append(f"{key}/{n}: portfolio_id {x.get('portfolio_id')} != {expected.get(n)}")
            y = x.get("ytd")
            if y is None: errs.append(f"{key}/{n}: no ytd")
            elif not isinstance(y,(int,float)): errs.append(f"{key}/{n}: ytd not numeric")
            elif abs(y) > PCT_LEAK: errs.append(f"{key}/{n}: ytd={y} looks like percent, not decimal")
            elif not (YTD_SANE[0] <= y <= YTD_SANE[1]): warns.append(f"{key}/{n}: ytd={y:.4f} unusual")
            h = x.get("holdings")
            if not isinstance(h, list) or not h:
                errs.append(f"{key}/{n}: no holdings"); continue
            tot = 0.0
            for hh in h:
                t = str(hh.get("ticker","")).upper(); w = hh.get("weight")
                if not t: errs.append(f"{key}/{n}: holding with empty ticker")
                if t.startswith("P:"): errs.append(f"{key}/{n}: unflattened sleeve {t}")
                if t in ("$:CASH","M:FZFXX","M:FDRXX"): errs.append(f"{key}/{n}: cash not mapped to CASH ({t})")
                if not isinstance(w,(int,float)) or w <= 0: errs.append(f"{key}/{n}: bad weight for {t}: {w}")
                elif w > 1.0: errs.append(f"{key}/{n}: weight {w} for {t} > 1.0 (percent not converted?)")
                else: tot += w
            if abs(tot - 1.0) > WEIGHT_TOL:
                errs.append(f"{key}/{n}: weights sum to {tot:.4f}, not 1.0 (a sleeve failed to expand?)")
        return m

    strategies = check_list("strategies", EXPECTED_STRATEGIES)
    sleeves = check_list("sleeves", EXPECTED_SLEEVES)
    m = strategies + sleeves
    if "models" in d: warns.append("legacy 'models' key present - ignored")

    # --- diff vs previous (informational) ---
    if a.prev:
        try:
            p = json.load(open(a.prev, encoding="utf-8"))
            pm = {x["name"]: x for x in p.get("strategies",[]) + p.get("sleeves",[])}
            for x in (m or []):
                old = pm.get(x["name"])
                if not old: continue
                ow = {h["ticker"]: h["weight"] for h in old.get("holdings",[])}
                nw = {h["ticker"]: h["weight"] for h in x.get("holdings",[])}
                add = sorted(set(nw)-set(ow)); rem = sorted(set(ow)-set(nw))
                mov = [f"{t} {ow[t]*100:.1f}%->{nw[t]*100:.1f}%" for t in sorted(set(ow)&set(nw)) if abs(ow[t]-nw[t])>0.005]
                if add or rem or mov:
                    print(f"CHANGED {x['name']}: +{add} -{rem} moved {mov}")
            print(f"as_of {p.get('ytd_as_of')} -> {as_of}")
        except Exception as e:
            warns.append(f"could not diff against --prev: {e}")

    for w in warns: print("WARN:", w)
    if errs: return fail(errs)
    print(f"OK: {len(b)} benchmarks, {len(strategies)} strategies, {len(sleeves)} sleeves, as of {as_of}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
