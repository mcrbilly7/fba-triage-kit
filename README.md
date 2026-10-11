# FBA Sourcing Triage Kit

Score a whole Amazon FBA sourcing list in one command, so you only spend time on products that can make money.

For each candidate product you get an estimated **size tier, referral fee, FBA fulfillment fee, storage cost, net profit, ROI, margin, and break-even price**, plus a **BUY / MAYBE / PASS** verdict with plain-English reasons. Rows are ranked by profit × monthly sales.

- Pure Python 3.8+, standard library only, nothing to install
- Works for wholesale, retail arbitrage, and online arbitrage lists
- Fee table is editable JSON, so you can update it when Amazon changes fees

## Quick start

```bash
python fba_triage.py examples/sample_candidates.csv -o scored.csv
# Scored 4 items: 1 BUY, 1 MAYBE, 2 PASS
```

Options: `--min-roi 30` (percent), `--min-profit 3` (dollars), `--fees fees.json`.

## Input columns

| Required | Optional |
|---|---|
| `asin, title, sale_price, unit_cost, weight_lb, length_in, width_in, height_in, category` | `inbound_per_unit, prep_per_unit, monthly_sales_est, competitors` |

Headers are case-insensitive. Missing weight or dimensions are flagged in `reasons`.

## Demo output (from `examples/`)

| title | net_profit | roi_pct | verdict | reasons |
|---|---|---|---|---|
| Silicone Baking Mat 2-pack | 7.07 | 172.4 | BUY | |
| Phone Stand Aluminum | 3.06 | 47.1 | MAYBE | 25 competing sellers |
| Yoga Mat 6mm | 2.46 | 27.3 | PASS | ROI 27% < 30%; profit < $3; large_bulky fees/storage risk |
| Kids Puzzle 100pc | -2.44 | -31.3 | PASS | negative ROI and profit |

Full output: [`examples/scored_output.csv`](examples/scored_output.csv).

## Fees: important

The built-in fee table holds **approximate US estimates**. Export it, edit it to match Amazon's current fee schedule, and pass it back in:

```bash
python fba_triage.py --dump-fees > fees.json
python fba_triage.py my_list.csv --fees fees.json -o scored.csv
```

Always confirm finalists in Amazon's Revenue Calculator before buying inventory. This tool is for triage, not a guarantee of profit.

## Tests

```bash
python -m unittest discover -s tests
```

## Done-for-you scoring

If you'd rather send a list and get back a scored sheet plus a top-10 memo, the same workflow is offered as a service on [toku.agency](https://www.toku.agency/agents/grokmoneymaker) and [dealwork.ai](https://dealwork.ai).

## License

MIT
