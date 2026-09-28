"""Layer 5 - Rule & Policy Engine. Rules run over ACTIVITIES and emit structured, explainable findings.
Add a rule = write one function + decorate with @rule(id, category)."""
from datetime import datetime, timedelta as td
from data import EMPLOYEES, ACCOUNTS
P = datetime.fromisoformat
RULES = []
def rule(rid, cat, ver="1.0"):
    def deco(fn): RULES.append((rid, ver, cat, fn)); return fn
    return deco
txs = lambda act: [e["raw"] for e in act if e["kind"] == "TXN"]
offh = lambda e: P(e["ts"]).hour < 8 or P(e["ts"]).hour >= 19

@rule("R-CIRC-01", "Circular flow")
def circular(act):
    T, out, seen = txs(act), [], set()
    for a in T:
        for b in T:
            for c in T:
                if a["dst"] == b["src"] and b["dst"] == c["src"] and c["dst"] == a["src"] and len({a["id"], b["id"], c["id"]}) == 3:
                    k = frozenset([a["id"], b["id"], c["id"]]); tot = a["amt"] + b["amt"] + c["amt"]
                    if k in seen or tot < 100000: continue
                    seen.add(k)
                    out.append((60, f"Funds left {a['src']} and returned to it via {b['src']} and {c['src']} (Rs {tot:,} moved in a loop)", sorted(k), "3-transfer loop returning to origin, total >= Rs 100,000", f"total=Rs {tot:,}", ""))
    return out

@rule("R-SPLIT-01", "Transaction splitting")
def splitting(act):
    by, out = {}, []
    for t in txs(act):
        if 8000 <= t["amt"] < 10000 and t["tag"] != "payroll": by.setdefault(t["dst"], []).append(t)
    for acc, L in by.items():
        L.sort(key=lambda t: t["ts"])
        if len(L) >= 3 and P(L[-1]["ts"]) - P(L[0]["ts"]) <= td(hours=72):
            s = sum(t["amt"] for t in L)
            out.append((50, f"{len(L)} deposits of Rs 8,000-9,999 into {acc} within 72h; total Rs {s:,} would exceed the Rs 10,000 limit if made at once", [t["id"] for t in L], ">= 3 deposits in [8000, 10000) to one account within 72h", f"count={len(L)}, total=Rs {s:,}", "Cash deposits must not be split"))
    return out

@rule("R-SCOPE-01", "Permission / scope violation")
def scope(act):
    out, seen = [], set()
    for e in act:
        emp = EMPLOYEES[e["emp"]]
        for a in e["accs"]:
            if a in emp["scope"] or a in seen: continue
            if e["kind"] == "TXN" and e["raw"]["tag"] == "payroll": continue   # policy exemption: scheduled payroll batch
            seen.add(a)
            out.append((30, f"{emp['role']} {emp['name']} touched account {a} ({ACCOUNTS[a]['owner']}), outside assigned scope {emp['scope']}", [x["id"] for x in act if a in x["accs"]], "Account touched is not in employee's assigned scope", f"account={a}", "; ".join(emp["restrictions"])))
    return out

@rule("R-DORM-01", "Dormant account misuse")
def dormant(act):
    return [(20, f"Account {e['raw']['acc']} is dormant but '{e['raw']['action']}' was performed on it", [e["id"]], "MODIFY_* action on a dormant account", f"account={e['raw']['acc']}", "No changes on dormant accounts") for e in act if e["kind"] == "ACTION" and e["raw"]["action"].startswith("MODIFY") and ACCOUNTS[e["raw"]["acc"]].get("status") == "dormant"]

@rule("R-SEQ-01", "Suspicious sequence")
def sequence(act):
    out = []
    for a in [e for e in act if e["kind"] == "ACTION"]:
        for t in [e for e in act if e["kind"] == "TXN" and a["raw"]["acc"] in e["accs"]]:
            if td(0) <= P(t["ts"]) - P(a["ts"]) <= td(hours=24) and ACCOUNTS[a["raw"]["acc"]].get("status") == "dormant":
                out.append((20, f"{a['raw']['action']} on {a['raw']['acc']} followed by transfer {t['id']} (Rs {t['raw']['amt']:,}) within 24h by the same employee", [a["id"], t["id"]], "access/modify then transfer on a dormant account within 24h", "gap < 24h", ""))
                break
    return out

@rule("R-LINK-01", "Insider relationship")
def link(act):
    out = []
    for t in txs(act):
        e = EMPLOYEES[t["emp"]]
        for a in (t["src"], t["dst"]):
            if ACCOUNTS.get(a, {}).get("phone") == e["phone"] and ACCOUNTS[a].get("addr") == e["addr"]:
                out.append((30, f"Beneficiary {ACCOUNTS[a]['owner']} ({a}) shares phone and address with employee {e['name']}", [t["id"]], "Counterparty contact details match employee profile", f"account={a}", ""))
    return out

@rule("R-HOURS-01", "After-hours activity")
def hours(act):
    ev = [e for e in act if e["kind"] == "ACTION" and offh(e)]
    return [(5, f"{len(ev)} action(s) performed outside business hours", [e["id"] for e in ev], "Timestamp outside 08:00-19:00", f"count={len(ev)}", "")] if ev else []

def evaluate(activity):
    return [dict(rule_id=rid, version=ver, category=cat, points=p, explanation=why, event_ids=ids, condition=cond, observed=obs, policy_context=pol)
            for rid, ver, cat, fn in RULES for p, why, ids, cond, obs, pol in fn(activity)]
