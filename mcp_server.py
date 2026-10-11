#!/usr/bin/env python3
"""mcp_server.py - Local MCP server (stdio) for FBA profit triage. Standard library only.

Run:  python mcp_server.py
Client config (Claude Desktop, Cursor, etc.):
  {"mcpServers": {"fba-triage": {"command": "python3", "args": ["/path/to/mcp_server.py"]}}}

Tools:
  fba_score      score 1-500 candidate products: fees, net profit, ROI, margin, break-even, BUY/MAYBE/PASS
  fba_fee_table  return the editable fee table used for estimates
Fees are estimates; confirm with Amazon's Revenue Calculator before buying inventory.
"""
import json, sys
import fba_triage as ft

PROTOCOL = "2025-06-18"
ITEM_PROPS = {
    "asin": {"type": "string"}, "title": {"type": "string"},
    "sale_price": {"type": "number", "description": "Expected Amazon sale price, USD"},
    "unit_cost": {"type": "number", "description": "Your landed cost per unit, USD"},
    "weight_lb": {"type": "number"}, "length_in": {"type": "number"},
    "width_in": {"type": "number"}, "height_in": {"type": "number"},
    "category": {"type": "string", "description": "e.g. kitchen, toys, beauty, electronics"},
    "inbound_per_unit": {"type": "number"}, "prep_per_unit": {"type": "number"},
    "monthly_sales_est": {"type": "number"}, "competitors": {"type": "number"},
}
TOOLS = [
    {"name": "fba_score",
     "description": "Estimate Amazon FBA fees, net profit, ROI, margin and break-even price for candidate "
                    "products, with a BUY/MAYBE/PASS verdict and reasons. Results are ranked by profit x monthly sales.",
     "inputSchema": {"type": "object", "required": ["items"], "properties": {
         "items": {"type": "array", "minItems": 1, "maxItems": 500, "items": {
             "type": "object", "required": ["sale_price", "unit_cost"], "properties": ITEM_PROPS}},
         "min_roi": {"type": "number", "default": 30, "description": "Minimum ROI percent for BUY"},
         "min_profit": {"type": "number", "default": 3, "description": "Minimum net profit per unit, USD"}}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
    {"name": "fba_fee_table",
     "description": "Return the fee table (referral %, size tiers, fulfillment and storage rates) used for estimates.",
     "inputSchema": {"type": "object", "properties": {}},
     "annotations": {"readOnlyHint": True, "openWorldHint": False}},
]

def call_tool(name, args):
    if name == "fba_fee_table":
        return ft.DEFAULT_FEES
    if name == "fba_score":
        items = args.get("items")
        if not isinstance(items, list) or not items:
            raise ValueError("items must be a non-empty array")
        if len(items) > 500:
            raise ValueError("at most 500 items per call")
        roi, prof = float(args.get("min_roi", 30)), float(args.get("min_profit", 3))
        rows = [{k.lower(): v for k, v in (it or {}).items()} for it in items]
        scored = sorted((ft.score(r, ft.DEFAULT_FEES, roi, prof) for r in rows), key=lambda x: -x["_rank"])
        for s in scored: s.pop("_rank", None)
        counts = {v: sum(1 for s in scored if s["verdict"] == v) for v in ("BUY", "MAYBE", "PASS")}
        return {"summary": counts, "results": scored,
                "note": "Fee estimates; confirm with Amazon's Revenue Calculator before buying."}
    raise KeyError(name)

def handle(msg):
    mid, method = msg.get("id"), msg.get("method")
    if mid is None:  # notification
        return None
    def ok(result): return {"jsonrpc": "2.0", "id": mid, "result": result}
    def err(code, text): return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": text}}
    if method == "initialize":
        ver = (msg.get("params") or {}).get("protocolVersion") or PROTOCOL
        return ok({"protocolVersion": ver, "capabilities": {"tools": {}},
                   "serverInfo": {"name": "fba-triage", "version": "1.1.0"}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        p = msg.get("params") or {}
        try:
            data = call_tool(p.get("name"), p.get("arguments") or {})
        except KeyError:
            return err(-32602, f"unknown tool: {p.get('name')}")
        except (ValueError, TypeError) as e:
            return ok({"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True})
        return ok({"content": [{"type": "text", "text": json.dumps(data, indent=1)}], "structuredContent": data})
    return err(-32601, f"method not found: {method}")

def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            out = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            out = handle(msg)
        if out is not None:
            sys.stdout.write(json.dumps(out) + "\n"); sys.stdout.flush()

if __name__ == "__main__":
    main()
