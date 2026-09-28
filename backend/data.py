"""Layer 0 - synthetic source data (stand-in for core banking / IAM / audit-log systems)."""
from datetime import datetime, timedelta as td
T0 = datetime(2026, 9, 1, 10, 0)
def ts(d=0, h=0, m=0): return (T0 + td(days=d, hours=h, minutes=m)).isoformat(timespec="minutes")

EMPLOYEES = {
 "E101": dict(name="Ravi Nair", role="Teller", dept="Retail", scope=["A6"], phone="9000000001", addr="12 MG Rd",
              restrictions=["Cash deposits must not be split to avoid limits"]),
 "E102": dict(name="Anita Rao", role="Loan Officer", dept="Lending", scope=["A1", "A2"], phone="9000000002", addr="44 Hill View",
              restrictions=["No access to accounts outside assigned portfolio", "No changes on dormant accounts"]),
 "E103": dict(name="Kunal Shah", role="Ops Approver", dept="Operations", scope=["A3", "A4", "A5"], phone="9000000003", addr="7 Lake St",
              restrictions=["Cannot approve transfers between related parties"]),
 "E105": dict(name="Sanjay Iyer", role="Branch Manager", dept="Retail", scope=["A10"], phone="9000000005", addr="90 Park Ave",
              restrictions=[]),
}
ACCOUNTS = {
 "A1": dict(owner="Vikram Sethi"), "A2": dict(owner="Neha Kapoor"), "A3": dict(owner="Alpha Traders"),
 "A4": dict(owner="Beta Exports"), "A5": dict(owner="Gamma Holdings"), "A6": dict(owner="Dev Malhotra"),
 "A8": dict(owner="Farida Khan", status="dormant"),
 "A9": dict(owner="Pooja Rao", phone="9000000002", addr="44 Hill View"),   # same contact details as E102
 "A10": dict(owner="Acme Corp Payroll"), "A11": dict(owner="Sunil Joshi"), "A12": dict(owner="Rekha Joshi"), "A13": dict(owner="Kiran Patil"),
}
TXNS = []
def tx(a, b, amt, t, emp, scenario, tag=""):
    TXNS.append(dict(id=f"T{len(TXNS)+1:03d}", src=a, dst=b, amt=amt, ts=t, emp=emp, scenario=scenario, tag=tag))
tx("A3", "A4", 480000, ts(2, 1), "E103", "S1"); tx("A4", "A5", 470000, ts(2, 5), "E103", "S1"); tx("A5", "A3", 465000, ts(3, 2), "E103", "S1")   # circular
for i, a in enumerate([9500, 9200, 9800, 9400, 9600]): tx("EXT", "A6", a, ts(5 + i // 3, i * 3), "E101", "S2")                                   # splitting
tx("A8", "A9", 275000, ts(8, 0, 20), "E102", "S3")                                                                                                # insider abuse
for i, a in enumerate([9100, 9400, 8800, 9700]): tx("A10", f"A{11 + i % 3}", a, ts(10, 0, i), "E105", "L1", "payroll")                             # legit payroll
for i in range(6): tx("A1", "A2", 1500 + 200 * i, ts(i, 3), "E102", "N")                                                                          # normal work

ACTIONS = [  # employee action log (view / modify / approve / export)
 dict(id="L01", emp="E102", action="VIEW", acc="A8", ts=ts(7, 12, 30), session="S-771", device=None),
 dict(id="L02", emp="E102", action="MODIFY_LIMIT", acc="A8", ts=ts(7, 12, 45), session="S-771", device=None),
 dict(id="L03", emp="E102", action="VIEW", acc="A1", ts=ts(1, 2), session="S-120", device="WS-22"),
 dict(id="L04", emp="E101", action="VIEW", acc="A6", ts=ts(5, 1), session="S-301", device="WS-05"),
]
SUSPICIOUS, LEGIT = {"S1", "S2", "S3"}, {"L1"}
