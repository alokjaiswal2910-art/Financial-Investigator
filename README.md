# FinSight FIN-04 MVP (layered, rule-based)
```
frontend/  index.html (landing + investigator login) | dashboard.html + app.js (workspace) | style.css (cream/brown) | config.js (API url)
backend/   app.py (REST API, auth, investigation service) | report.py (Word report) | data.py (synthetic data)
           engine/observer.py (seeds) | engine/pipeline.py (context, activities, graph) | engine/rules.py (rule & policy engine)
```
Run: 1) `cd backend && pip install -r requirements.txt && python app.py`  2) `cd frontend && python -m http.server 3000` -> http://localhost:3000
Login: investigator / finsight123 (demo, in backend/app.py USERS)
Flow: login -> seeds/filters at top -> investigation -> charts, findings, money-flow graph, per-account in/out, timeline -> assign case -> download .docx
Add a rule: decorate a function in engine/rules.py with @rule("R-XXX-01", "Category").
Ideas next: DB instead of data.py, hop-depth control on graph, ML observer, real user store.
