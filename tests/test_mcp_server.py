import json, os, subprocess, sys, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def run(msgs):
    inp = "".join(json.dumps(m) + "\n" for m in msgs)
    r = subprocess.run([sys.executable, "mcp_server.py"], input=inp, capture_output=True, text=True, cwd=ROOT, timeout=20)
    return [json.loads(l) for l in r.stdout.splitlines() if l.strip()]

class T(unittest.TestCase):
    def test_handshake_and_score(self):
        out = run([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "fba_score", "arguments": {"items": [
                {"title": "Baking mat", "sale_price": 19.99, "unit_cost": 4.10, "weight_lb": 0.6, "length_in": 16.5, "width_in": 3, "height_in": 3, "category": "kitchen", "competitors": 8}]}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "fba_score", "arguments": {"items": []}}},
        ])
        self.assertEqual([o["id"] for o in out], [1, 2, 3, 4])
        self.assertEqual(out[0]["result"]["serverInfo"]["name"], "fba-triage")
        self.assertEqual({t["name"] for t in out[1]["result"]["tools"]}, {"fba_score", "fba_fee_table"})
        self.assertEqual(out[2]["result"]["structuredContent"]["results"][0]["verdict"], "BUY")
        self.assertTrue(out[3]["result"]["isError"])

if __name__ == "__main__":
    unittest.main()
