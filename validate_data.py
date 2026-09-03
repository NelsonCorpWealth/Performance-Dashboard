#!/usr/bin/env python3
"""
validate_data.py - gate before commit.

The routine (Claude) pulls from YCharts and writes data.json. Claude is
flexible; this script is strict. Nothing reaches the live dashboard unless
it passes.

    python validate_data.py data.json          -> exit 0 = safe to commit
    python validate_data.py data.json --prev old.json   (also diff)

Exit codes: 0 ok, 1 invalid, 2 file/parse error.
"""
import sys, json, datetime, argparse

EXPECTED_BENCHMARKS = ["SPYM", "DIA", "QQQ", "AGG", "UUP", "PDBC"]
EXPECTED_MODELS = {
    "Moderate": 552644, "Abs Rtn Moderate": 555767, "Tax Moderate": 1146880,
    "Aggressive": 597223, "All Tactical": 1297251, "Macro": 1729042,
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

    # --- models ---
    m = d.get("models")
    if not isinstance(m, list): errs.append("models missing")
    else:
        names = [x.get("name") for x in m]
        if names != list(EXPECTED_MODELS):
            errs.append(f"model names/order {names} != expected {list(EXPECTED_MODELS)}")
        for x in m:
            n = x.get("name")
            if x.get("portfolio_id") != EXPECTED_MODELS.get(n):
                errs.append(f"{n}: portfolio_id {x.get('portfolio_id')} != {EXPECTED_MODELS.get(n)}")
            y = x.get("ytd")
            if y is None: errs.append(f"{n}: no ytd")
            elif not isinstance(y,(int,float)): errs.append(f"{n}: ytd not numeric")
            elif abs(y) > PCT_LEAK: errs.append(f"{n}: ytd={y} looks like percent, not decimal")
            elif not (YTD_SANE[0] <= y <= YTD_SANE[1]): warns.append(f"{n}: ytd={y:.4f} unusual")
            h = x.get("holdings")
            if not isinstance(h, list) or not h:
                errs.append(f"{n}: no holdings"); continue
            tot = 0.0
            for hh in h:
                t = str(hh.get("ticker","")).upper(); w = hh.get("weight")
                if not t: errs.append(f"{n}: holding with empty ticker")
                if t.startswith("P:"): errs.append(f"{n}: unflattened sleeve {t}")
                if t in ("$:CASH","M:FZFXX","M:FDRXX"): errs.append(f"{n}: cash not mapped to CASH ({t})")
                if not isinstance(w,(int,float)) or w <= 0: errs.append(f"{n}: bad weight for {t}: {w}")
                elif w > 1.0: errs.append(f"{n}: weight {w} for {t} > 1.0 (percent not converted?)")
                else: tot += w
            if abs(tot - 1.0) > WEIGHT_TOL:
                errs.append(f"{n}: weights sum to {tot:.4f}, not 1.0 (a sleeve failed to expand?)")

    # --- diff vs previous (informational) ---
    if a.prev:
        try:
            p = json.load(open(a.prev, encoding="utf-8"))
            pm = {x["name"]: x for x in p.get("models",[])}
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
    print(f"OK: {len(b)} benchmarks, {len(m)} models, as of {as_of}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
