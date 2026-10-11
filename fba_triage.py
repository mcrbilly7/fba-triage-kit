#!/usr/bin/env python3
"""fba_triage.py - Batch profit/ROI triage for Amazon FBA sourcing lists (stdlib only).

Usage:
  python fba_triage.py candidates.csv -o scored.csv [--fees fees.json] [--min-roi 30] [--min-profit 3]

Input CSV columns (header names, case-insensitive):
  asin, title, sale_price, unit_cost, weight_lb, length_in, width_in, height_in, category
  optional: inbound_per_unit, prep_per_unit, monthly_sales_est, competitors

Output: the same rows plus size_tier, referral_fee, fba_fee, storage_est, total_fees,
net_profit, roi_pct, margin_pct, breakeven_price, verdict (BUY / MAYBE / PASS) and reasons.
Rows are sorted by net profit x monthly_sales_est (or net profit if no sales estimate).

Fees are ESTIMATES from an editable table (DEFAULT_FEES or --fees JSON). Amazon changes
fees yearly, so check against Seller Central's Revenue Calculator before buying inventory.
Run `python fba_triage.py --dump-fees > fees.json` to get the table and edit it.
"""
import argparse, csv, json, math, sys

DEFAULT_FEES = {
  "_note": "Approximate US FBA fees; edit to match current Amazon fee schedule.",
  "referral_pct": {"default": 15, "electronics": 8, "camera": 8, "computers": 8,
                   "grocery": 8, "health": 8, "beauty": 8, "baby": 8, "toys": 15,
                   "home": 15, "kitchen": 15, "sports": 15, "clothing": 17,
                   "jewelry": 20, "furniture": 15},
  "referral_min": 0.30,
  "low_price_threshold": 15.00, "low_price_referral_pct": 8,
  "size_tiers": [
    {"name": "small_standard", "max_weight_lb": 1.0, "max_dims_in": [15, 12, 0.75],
     "fee_by_weight": [[0.25, 3.06], [0.5, 3.15], [0.75, 3.24], [1.0, 3.33]]},
    {"name": "large_standard", "max_weight_lb": 20.0, "max_dims_in": [18, 14, 8],
     "fee_by_weight": [[0.25, 3.68], [0.5, 3.90], [0.75, 4.15], [1.0, 4.55],
                       [1.5, 5.19], [2.0, 5.57], [2.5, 5.94], [3.0, 6.32]],
     "over_3lb_base": 6.32, "per_half_lb_over_3": 0.16},
    {"name": "large_bulky", "max_weight_lb": 50.0, "max_dims_in": [59, 33, 33],
     "base": 9.61, "per_lb_over_1": 0.38}
  ],
  "oversize_fallback": {"base": 26.33, "per_lb_over_1": 0.38},
  "storage_per_cuft_month": 0.78,
  "storage_months": 2
}

def f(v, default=0.0):
    try:
        return float(str(v).replace("$", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return default

def size_tier(fees, w, dims):
    d = sorted(dims, reverse=True)
    for t in fees["size_tiers"]:
        lim = sorted(t["max_dims_in"], reverse=True)
        if w <= t["max_weight_lb"] and all(a <= b for a, b in zip(d, lim)):
            return t
    return None

def fba_fee(fees, w, dims, unit_wt=None):
    # dimensional weight for non-small items
    dimw = (dims[0] * dims[1] * dims[2]) / 139.0
    t = size_tier(fees, w, dims)
    if t is None:
        o = fees["oversize_fallback"]; bw = max(w, dimw)
        return "oversize", o["base"] + o["per_lb_over_1"] * max(0, bw - 1)
    bw = w if t["name"] == "small_standard" else max(w, dimw)
    if "fee_by_weight" in t:
        for lim, fee in t["fee_by_weight"]:
            if bw <= lim:
                return t["name"], fee
        steps = math.ceil((bw - 3.0) / 0.5)
        return t["name"], t["over_3lb_base"] + steps * t["per_half_lb_over_3"]
    return t["name"], t["base"] + t["per_lb_over_1"] * max(0, bw - 1)

def referral(fees, price, cat):
    pct = fees["referral_pct"].get((cat or "").strip().lower(), fees["referral_pct"]["default"])
    if price < fees["low_price_threshold"] and cat and cat.lower() in ("beauty", "health", "grocery", "baby"):
        pct = min(pct, fees["low_price_referral_pct"])
    return max(fees["referral_min"], price * pct / 100.0)

def score(row, fees, min_roi, min_profit):
    p, c = f(row.get("sale_price")), f(row.get("unit_cost"))
    w = f(row.get("weight_lb"))
    dims = [f(row.get("length_in")), f(row.get("width_in")), f(row.get("height_in"))]
    tier, fee = fba_fee(fees, w, dims)
    ref = referral(fees, p, row.get("category"))
    cuft = dims[0] * dims[1] * dims[2] / 1728.0
    storage = cuft * fees["storage_per_cuft_month"] * fees["storage_months"]
    extra = f(row.get("inbound_per_unit")) + f(row.get("prep_per_unit"))
    total = ref + fee + storage + extra
    net = p - c - total
    roi = (net / c * 100) if c else 0.0
    margin = (net / p * 100) if p else 0.0
    pct = fees["referral_pct"].get((row.get("category") or "").strip().lower(), fees["referral_pct"]["default"]) / 100.0
    breakeven = (c + fee + storage + extra) / (1 - pct) if pct < 1 else 0
    reasons = []
    if p <= 0 or c <= 0: reasons.append("missing price/cost")
    if not all(dims) or w <= 0: reasons.append("missing weight/dims (fee guessed)")
    if roi < min_roi: reasons.append(f"ROI {roi:.0f}% < {min_roi}%")
    if net < min_profit: reasons.append(f"profit ${net:.2f} < ${min_profit}")
    if tier in ("large_bulky", "oversize"): reasons.append(f"{tier} fees/storage risk")
    comp = f(row.get("competitors"), -1)
    if comp >= 20: reasons.append(f"{int(comp)} competing sellers")
    if not reasons: verdict = "BUY"
    elif net > 0 and roi >= min_roi * 0.6 and len(reasons) <= 1: verdict = "MAYBE"
    else: verdict = "PASS"
    out = dict(row)
    out.update(size_tier=tier, referral_fee=f"{ref:.2f}", fba_fee=f"{fee:.2f}", storage_est=f"{storage:.2f}",
               total_fees=f"{total:.2f}", net_profit=f"{net:.2f}", roi_pct=f"{roi:.1f}",
               margin_pct=f"{margin:.1f}", breakeven_price=f"{breakeven:.2f}", verdict=verdict,
               reasons="; ".join(reasons))
    sales = f(row.get("monthly_sales_est"), 0)
    out["_rank"] = net * sales if sales else net
    return out

def main(argv=None):
    ap = argparse.ArgumentParser(description="Score an FBA sourcing CSV for profit and ROI.")
    ap.add_argument("input", nargs="?")
    ap.add_argument("-o", "--output", default="-")
    ap.add_argument("--fees", help="JSON fee table (see --dump-fees)")
    ap.add_argument("--min-roi", type=float, default=30.0)
    ap.add_argument("--min-profit", type=float, default=3.0)
    ap.add_argument("--dump-fees", action="store_true")
    a = ap.parse_args(argv)
    if a.dump_fees:
        json.dump(DEFAULT_FEES, sys.stdout, indent=2); print(); return 0
    if not a.input:
        ap.error("input CSV required")
    fees = DEFAULT_FEES
    if a.fees:
        with open(a.fees) as fh: fees = json.load(fh)
    try:
        with open(a.input, newline="", encoding="utf-8-sig") as fh:
            r = csv.DictReader(fh)
            r.fieldnames = [h.strip().lower() for h in r.fieldnames or []]
            rows = list(r)
    except FileNotFoundError:
        print(f"Error: file '{a.input}' not found.", file=sys.stderr); return 1
    if not rows:
        print("Error: no rows in input.", file=sys.stderr); return 1
    scored = sorted((score(x, fees, a.min_roi, a.min_profit) for x in rows), key=lambda x: -x["_rank"])
    cols = [c for c in scored[0] if c != "_rank"]
    fh = sys.stdout if a.output == "-" else open(a.output, "w", newline="", encoding="utf-8")
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
    w.writeheader(); w.writerows(scored)
    if fh is not sys.stdout: fh.close()
    n = {v: sum(1 for s in scored if s["verdict"] == v) for v in ("BUY", "MAYBE", "PASS")}
    print(f"Scored {len(scored)} items: {n['BUY']} BUY, {n['MAYBE']} MAYBE, {n['PASS']} PASS", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())
