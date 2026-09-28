"""Layer 6/7 - Investigation service + REST API (Flask). Run: python app.py  (port 5000)"""
from flask import Flask, jsonify, request, send_file
import secrets
from data import EMPLOYEES, ACCOUNTS, TXNS, ACTIONS, SUSPICIOUS, LEGIT
from engine import observer
from engine.pipeline import build_context, build_activities, build_graph
from engine.rules import evaluate

app = Flask(__name__)
INVS, SEED_DECISIONS = {}, {}

@app.after_request
def cors(r):
    r.headers.update({"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Content-Type, Authorization", "Access-Control-Allow-Methods": "GET,POST,OPTIONS"}); return r

USERS = {"investigator": dict(password="finsight123", name="Priya Deshmukh", title="Lead Investigator")}   # demo credentials
TOKENS = {}

@app.before_request
def guard():
    if request.method == "OPTIONS" or request.path == "/api/login": return None
    if (request.headers.get("Authorization", "")[7:] or request.args.get("token", "")) not in TOKENS: return jsonify(error="unauthorized"), 401

@app.post("/api/login")
def login():
    b = request.json or {}; u = USERS.get(b.get("username"))
    if not u or u["password"] != b.get("password"): return jsonify(error="Invalid username or password"), 401
    t = secrets.token_hex(16); TOKENS[t] = u["name"]; return jsonify(token=t, name=u["name"], title=u["title"])

level = lambda s: "HIGH" if s >= 60 else "MEDIUM" if s >= 30 else "LOW" if s > 0 else "CLEAR"
TITLE = {"Circular flow": "Circular fund movement", "Transaction splitting": "Transaction splitting / structuring", "Permission / scope violation": "Out-of-role account activity", "Dormant account misuse": "Out-of-role account activity", "Insider relationship": "Out-of-role account activity"}

def investigate(emps, subject, entry):
    events = build_context(emps); acts = []
    for i, grp in enumerate(build_activities(events), 1):
        f = evaluate(grp); score = min(100, sum(x["points"] for x in f)); nodes, edges = build_graph(grp)
        top = max(f, key=lambda x: x["points"])["category"] if f else None
        gaps = [f"No device/IP record for {e['id']} ({e['raw']['action']} on {e['raw']['acc']})" for e in grp if e["kind"] == "ACTION" and not e["raw"].get("device")]
        acts.append(dict(id=f"ACT-{i}", title=TITLE.get(top, "Routine activity - no rules triggered"), score=score, level=level(score), findings=sorted(f, key=lambda x: -x["points"]),
            counts=dict(events=len(grp), transactions=sum(e["kind"] == "TXN" for e in grp), actions=sum(e["kind"] == "ACTION" for e in grp), rules=len(f)),
            timeline=[dict(ts=e["ts"], id=e["id"], amt=e["raw"].get("amt"), kind=e["kind"], text=(f"{e['raw']['src']} -> {e['raw']['dst']}  Rs {e['raw']['amt']:,}" if e["kind"] == "TXN" else f"{e['raw']['action']} on {e['raw']['acc']}") + f"  [{EMPLOYEES[e['emp']]['name']}]") for e in grp],
            graph=dict(nodes=nodes, edges=edges), evidence_gaps=gaps, txn_ids=[e["id"] for e in grp if e["kind"] == "TXN"]))
    acts.sort(key=lambda a: -a["score"]); top = acts[0]["score"] if acts else 0
    n = len(INVS) + 1024; iid = f"INV-{n}"
    INVS[iid] = dict(id=iid, subject=subject, entry=entry, employees=[dict(id=e, **{k: EMPLOYEES[e][k] for k in ("name", "role", "dept", "restrictions")}) for e in emps],
        overall_score=top, overall_level=level(top), activities=acts, case=dict(status="OPEN", assignee=None, note=""),
        summary=f"{len(acts)} activit{'y' if len(acts) == 1 else 'ies'} reconstructed; {sum(a['counts']['rules'] for a in acts)} rule finding(s). " + (f"Highest risk: {acts[0]['title']} ({acts[0]['level']})." if top else "No suspicious patterns found."))
    return INVS[iid]

@app.get("/api/seeds")
def seeds(): return jsonify([dict(s, decision=SEED_DECISIONS.get(s["id"], "PENDING")) for s in observer.seeds()])

@app.post("/api/seeds/<sid>/decision")
def decide(sid): SEED_DECISIONS[sid] = request.json["decision"]; return jsonify(ok=True)

@app.get("/api/entities")
def entities(): return jsonify(employees=[dict(id=k, name=v["name"], role=v["role"]) for k, v in EMPLOYEES.items()], accounts=[dict(id=k, owner=v["owner"]) for k, v in ACCOUNTS.items()])

@app.post("/api/investigations")
def start():
    en = request.json; t, i = en["type"], en["id"]
    if t == "seed": emps, subj = [i.replace("IS-", "")], f"Employee {i.replace('IS-', '')}"
    elif t == "employee": emps, subj = [i], f"Employee {i}"
    else:
        emps = sorted({x["emp"] for x in TXNS if i in (x["src"], x["dst"]) and x["emp"]} | {a["emp"] for a in ACTIONS if a["acc"] == i}); subj = f"Account {i}"
        if not emps: return jsonify(error="No employee activity on this account"), 404
    return jsonify(investigate(emps, subj, en))

@app.get("/api/investigations/<iid>")
def get_inv(iid): return jsonify(INVS[iid])

@app.post("/api/investigations/<iid>/case")
def case(iid): INVS[iid]["case"].update(request.json); return jsonify(INVS[iid]["case"])

@app.get("/api/investigations/<iid>/report.docx")
def report(iid):
    from report import build_docx
    return send_file(build_docx(INVS[iid], TOKENS[request.args.get("token") or request.headers["Authorization"][7:]]), as_attachment=True, download_name=f"{iid}_FinSight_Report.docx",
                     mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

@app.get("/api/metrics")
def metrics():
    saved = dict(INVS); det, fp = set(), set(); scen = {t["id"]: t["scenario"] for t in TXNS}
    for e in EMPLOYEES:
        for a in investigate([e], "metrics", {})["activities"]:
            s = {scen[x] for x in a["txn_ids"]} & (SUSPICIOUS | LEGIT)
            (det if a["findings"] else set()).update(s & SUSPICIOUS); (fp if a["findings"] else set()).update(s & LEGIT)
    INVS.clear(); INVS.update(saved)
    return jsonify(suspicious=len(SUSPICIOUS), detected=len(det), legit=len(LEGIT), false_positives=len(fp), detection_rate=len(det) / len(SUSPICIOUS), false_positive_rate=len(fp) / len(LEGIT))

if __name__ == "__main__": app.run(port=5000)
