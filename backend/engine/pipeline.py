"""Layers 2-4 - Context builder, Activity construction, Graph builder."""
from data import EMPLOYEES, TXNS, ACTIONS
from datetime import datetime
P = datetime.fromisoformat

def build_context(emps):
    """Focused dataset: only events of the subject employee(s), as unified events."""
    ev = [dict(id=t["id"], kind="TXN", emp=t["emp"], ts=t["ts"], accs=[a for a in (t["src"], t["dst"]) if a != "EXT"], raw=t) for t in TXNS if t["emp"] in emps]
    ev += [dict(id=a["id"], kind="ACTION", emp=a["emp"], ts=a["ts"], accs=[a["acc"]], raw=a) for a in ACTIONS if a["emp"] in emps]
    return sorted(ev, key=lambda e: e["ts"])

def build_activities(events, gap_hours=72):
    """Group by entity continuity (shared account) + temporal proximity + same employee. Never invents events."""
    par = list(range(len(events)))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i, a in enumerate(events):
        for j in range(i):
            b = events[j]
            if a["emp"] == b["emp"] and set(a["accs"]) & set(b["accs"]) and abs((P(a["ts"]) - P(b["ts"])).total_seconds()) <= gap_hours * 3600:
                par[f(i)] = f(j)
    groups = {}
    for i, e in enumerate(events): groups.setdefault(f(i), []).append(e)
    return list(groups.values())

def build_graph(events):
    nodes, edges = {}, {}
    for e in events:
        emp = e["emp"]; nodes.setdefault(emp, dict(id=emp, type="employee", label=EMPLOYEES[emp]["name"]))
        if e["kind"] == "TXN":
            t = e["raw"]
            for a in (t["src"], t["dst"]): nodes.setdefault(a, dict(id=a, type="account", label=a))
            edges[(t["src"], t["dst"], t["id"])] = dict(id=t["id"], s=t["src"], d=t["dst"], label=f"Rs {t['amt']:,}", kind="txn")
            edges[(emp, t["dst"], "init")] = dict(s=emp, d=t["dst"] if t["dst"] != "EXT" else t["src"], label="initiates", kind="link")
        else:
            a = e["raw"]; nodes.setdefault(a["acc"], dict(id=a["acc"], type="account", label=a["acc"]))
            edges[(emp, a["acc"], a["action"])] = dict(s=emp, d=a["acc"], label=a["action"], kind="link")
    return list(nodes.values()), list(edges.values())
