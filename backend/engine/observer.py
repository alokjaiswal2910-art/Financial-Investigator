"""Layer 1 - Observer: screening -> Investigation Seeds (a LEAD, never a verdict).
Heuristic stand-in; swap `score_employee` for the ML model later without touching other layers."""
from datetime import datetime
from data import EMPLOYEES, TXNS, ACTIONS
P = datetime.fromisoformat

def score_employee(eid):
    e, sig = EMPLOYEES[eid], []
    tx = [t for t in TXNS if t["emp"] == eid and t["tag"] != "payroll"]
    act = [a for a in ACTIONS if a["emp"] == eid]
    touched = {a for t in tx for a in (t["src"], t["dst"]) if a != "EXT"} | {a["acc"] for a in act}
    if touched - set(e["scope"]): sig.append((.35, "Touched accounts outside assigned scope"))
    if any(P(x["ts"]).hour < 8 or P(x["ts"]).hour >= 19 for x in act): sig.append((.15, "Activity outside business hours"))
    if any(t["amt"] >= 200000 for t in tx): sig.append((.25, "Unusually high-value transfers for role"))
    if sum(8000 <= t["amt"] < 10000 for t in tx) >= 3: sig.append((.25, "Repeated amounts just under the reporting limit"))
    xs = sorted(P(t["ts"]) for t in tx)
    if any((xs[i + 2] - xs[i]).days <= 3 for i in range(len(xs) - 2)) and any(t["amt"] >= 8000 for t in tx): sig.append((.3, "Burst of large transactions in a short window"))
    return min(1, sum(s[0] for s in sig) + .05), sig, tx + act

def seeds():
    out = []
    for eid in EMPLOYEES:
        sc, sig, ev = score_employee(eid)
        if sc < .3: continue
        out.append(dict(id=f"IS-{eid}", employee=eid, name=EMPLOYEES[eid]["name"], role=EMPLOYEES[eid]["role"], score=round(sc, 2),
                        signals=[s[1] for s in sig], reason="Behavioural deviation: " + "; ".join(s[1] for s in sig),
                        window=[min(x["ts"] for x in ev), max(x["ts"] for x in ev)]))
    return sorted(out, key=lambda s: -s["score"])
