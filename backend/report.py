"""Report layer - builds the investigation report as a Word (.docx) file."""
import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
try:
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
except Exception: plt = None
BROWN, PAL = RGBColor(0x5C, 0x3D, 0x2E), ["#5c3d2e", "#a86f44", "#d9a066", "#8a9a5b", "#c9694a", "#b8a38a"]
LV = {"HIGH": "#b3402a", "MEDIUM": "#d08a2e", "LOW": "#6b8f4e", "CLEAR": "#9c8b7a"}

def shade(cell, hexcol):
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:fill"), hexcol); cell._tc.get_or_add_tcPr().append(s)
def table(doc, head, rows, widths):
    t = doc.add_table(rows=1, cols=len(head)); t.style = "Table Grid"
    for i, h in enumerate(head):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(9); r.font.color.rgb = RGBColor(255, 255, 255); shade(c, "5C3D2E")
    for k, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; cells[i].paragraphs[0].add_run(str(v)).font.size = Pt(9)
            if k % 2: shade(cells[i], "F6EEDD")
    for row in t.rows:
        for i, w in enumerate(widths): row.cells[i].width = Inches(w)
    return t
def img(fig):
    b = io.BytesIO(); fig.savefig(b, format="png", dpi=150, bbox_inches="tight", facecolor="#fffaf0"); plt.close(fig); b.seek(0); return b
def charts(inv):
    if not plt: return []
    out, acts = [], inv["activities"]
    f, ax = plt.subplots(figsize=(4.2, 2.6)); ax.bar([a["id"] for a in acts], [a["score"] for a in acts], color=[LV[a["level"]] for a in acts])
    ax.set_title("Risk score by activity", fontsize=10); ax.set_ylim(0, 100); out.append(img(f))
    cat = {}
    for a in acts:
        for x in a["findings"]: cat[x["category"]] = cat.get(x["category"], 0) + x["points"]
    if cat:
        f, ax = plt.subplots(figsize=(4.2, 2.6)); ax.pie(cat.values(), labels=cat.keys(), colors=PAL, autopct="%1.0f%%", textprops={"fontsize": 7}); ax.set_title("Findings by category (risk points)", fontsize=10); out.append(img(f))
    return out

def build_docx(inv, analyst):
    d = Document(); st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(10.5)
    for s in d.sections: s.left_margin = s.right_margin = Inches(0.8); s.footer.paragraphs[0].text = f"FinSight - Confidential investigation report {inv['id']}"
    h = d.add_heading("FinSight Investigation Report", 0)
    for r in h.runs: r.font.color.rgb = BROWN
    d.add_paragraph("Financial Crime & Insider Risk Intelligence Platform (FIN-04)")
    c = inv["case"]
    table(d, ["Field", "Value"], [["Investigation ID", inv["id"]], ["Subject", inv["subject"]], ["Overall risk", f"{inv['overall_level']} ({inv['overall_score']}/100)"],
        ["Case status", c["status"]], ["Assigned to", c.get("assignee") or "Unassigned"], ["Prepared by", analyst], ["Generated", datetime.now().strftime("%d %b %Y, %H:%M")]], [1.8, 5])
    d.add_heading("1. Executive summary", 1); d.add_paragraph(inv["summary"])
    d.add_paragraph("Findings are produced by deterministic, versioned rules. Each finding lists the condition tested, the values observed and the source event IDs so a reviewer can verify it independently. Risk levels are indicators for human review, not verdicts.")
    d.add_heading("2. Subject profile", 1)
    table(d, ["Employee", "Role / Dept", "Policy restrictions"], [[e["name"], f"{e['role']} / {e['dept']}", "; ".join(e["restrictions"]) or "None on record"] for e in inv["employees"]], [1.6, 1.8, 3.4])
    d.add_heading("3. Risk analytics", 1)
    imgs = charts(inv)
    if imgs:
        t = d.add_table(rows=1, cols=len(imgs))
        for i, b in enumerate(imgs): t.rows[0].cells[i].paragraphs[0].add_run().add_picture(b, width=Inches(3.2))
    d.add_heading("4. Activities, findings and evidence", 1)
    for a in inv["activities"]:
        d.add_heading(f"{a['id']}: {a['title']}  [{a['level']} - {a['score']}/100]", 2)
        k = a["counts"]; d.add_paragraph(f"{k['events']} events | {k['transactions']} transactions | {k['actions']} employee actions | {k['rules']} rules triggered")
        if a["findings"]:
            table(d, ["Rule", "Pts", "Explanation", "Condition / observed / policy"], [[f"{f['rule_id']} v{f['version']}\n{f['category']}", f"+{f['points']}", f["explanation"], f"Condition: {f['condition']}\nObserved: {f['observed']}" + (f"\nPolicy: {f['policy_context']}" if f["policy_context"] else "") + f"\nEvidence: {', '.join(f['event_ids'])}"] for f in a["findings"]], [1.3, 0.5, 2.5, 2.5])
        else: d.add_paragraph("No rules triggered - activity appears consistent with role and policy.")
        d.add_paragraph().add_run("Timeline").bold = True
        table(d, ["Time", "Event ID", "Description"], [[e["ts"].replace("T", " "), e["id"], e["text"]] for e in a["timeline"]], [1.4, 0.8, 4.6])
        if a["evidence_gaps"]:
            d.add_paragraph().add_run("Evidence gaps").bold = True
            for g in a["evidence_gaps"]: d.add_paragraph(g, style="List Bullet")
    d.add_heading("5. Reviewer notes and sign-off", 1); d.add_paragraph(c.get("note") or "______________________________________________")
    d.add_paragraph("Investigator signature: ____________________     Date: ______________")
    b = io.BytesIO(); d.save(b); b.seek(0); return b
