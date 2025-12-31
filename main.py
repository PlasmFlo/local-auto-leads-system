# Main entry point for autoshop leads system

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from datetime import datetime

app = FastAPI()

# Allow simple local testing (optional but helpful)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "leads.db"

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                email TEXT,
                vehicle TEXT NOT NULL,
                urgency TEXT NOT NULL,
                issues TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            );
        """)
init_db()

FORM_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Auto Shop Service Request</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 18px; max-width: 720px; margin: 0 auto; }
    label { display:block; margin-top: 14px; font-weight: 600; }
    input, textarea, select { width: 100%; padding: 10px; margin-top: 6px; border: 1px solid #ccc; border-radius: 10px; }
    button { margin-top: 16px; padding: 12px 14px; border: 0; border-radius: 12px; cursor: pointer; font-weight: 700; }
    .ok { margin-top: 14px; padding: 12px; border-radius: 12px; background: #eef9ee; display:none; }
    .err { margin-top: 14px; padding: 12px; border-radius: 12px; background: #ffecec; display:none; }
  </style>
</head>
<body>
  <h1>Service Request</h1>
  <p>Fill this out and we’ll contact you.</p>

  <form id="leadForm">
    <label>Full Name *</label>
    <input name="name" required />

    <label>Phone *</label>
    <input name="phone" required />

    <label>Email</label>
    <input name="email" type="email" />

    <label>Vehicle (Year / Make / Model) *</label>
    <input name="vehicle" placeholder="2016 Toyota Camry" required />

    <label>Urgency *</label>
    <select name="urgency" required>
      <option value="Emergency">Emergency</option>
      <option value="Soon" selected>Soon</option>
      <option value="Routine">Routine</option>
    </select>

    <label>Issue / Repairs Needed *</label>
    <textarea name="issues" rows="5" placeholder="Describe the problem..." required></textarea>

    <button type="submit">Submit</button>
  </form>

  <div class="ok" id="okBox">✅ Submitted. We’ll contact you shortly.</div>
  <div class="err" id="errBox">❌ Something went wrong. Please try again.</div>

<script>
const form = document.getElementById("leadForm");
const okBox = document.getElementById("okBox");
const errBox = document.getElementById("errBox");

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  okBox.style.display = "none";
  errBox.style.display = "none";

  const data = Object.fromEntries(new FormData(form).entries());

  try {
    const res = await fetch("/api/leads", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error("bad response");
    form.reset();
    okBox.style.display = "block";
  } catch (err) {
    errBox.style.display = "block";
  }
});
</script>
</body>
</html>
"""

OWNER_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Owner Live Leads</title>
  <style>
    body { font-family: Arial, sans-serif; padding: 18px; max-width: 980px; margin: 0 auto; }
    .bar { display:flex; justify-content: space-between; align-items:center; gap:12px; flex-wrap:wrap; }
    .pill { padding: 6px 10px; border-radius: 999px; background:#eee; font-weight:700; }
    .grid { display:grid; gap: 12px; margin-top: 14px; }
    .card { border: 1px solid #ddd; border-radius: 14px; padding: 12px; }
    .meta { display:flex; gap:10px; flex-wrap:wrap; color:#444; }
    .urg { font-weight: 800; }
    .Emergency { color:#b00020; }
    .Soon { color:#b05a00; }
    .Routine { color:#1a7f37; }
    pre { white-space: pre-wrap; margin: 8px 0 0; }
  </style>
</head>
<body>
  <div class="bar">
    <h1>Live Leads</h1>
    <div class="pill">Auto-refresh: 3s</div>
  </div>
  <div id="stats" class="meta"></div>
  <div id="list" class="grid"></div>

<script>
async function loadLeads(){
  const res = await fetch("/api/leads?limit=50");
  const data = await res.json();

  document.getElementById("stats").innerHTML =
    `<div class="pill">Total shown: ${data.length}</div>`;

  const list = document.getElementById("list");
  list.innerHTML = "";

  data.forEach(l => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `
      <div class="meta">
        <div><b>#${l.id}</b></div>
        <div>${l.created_at}</div>
        <div class="urg ${l.urgency}">${l.urgency}</div>
        <div><b>${l.name}</b> — ${l.phone}</div>
        <div>${l.email ?? ""}</div>
      </div>
      <div><b>Vehicle:</b> ${l.vehicle}</div>
      <pre><b>Issue:</b> ${l.issues}</pre>
    `;
    list.appendChild(card);
  });
}

loadLeads();
setInterval(loadLeads, 3000);
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def form_page():
    return HTMLResponse(FORM_HTML)

@app.get("/owner", response_class=HTMLResponse)
def owner_page():
    return HTMLResponse(OWNER_HTML)

@app.post("/api/leads")
async def create_lead(request: Request):
    data = await request.json()
    name = (data.get("name") or "").strip()
    phone = (data.get("phone") or "").strip()
    email = (data.get("email") or "").strip() or None
    vehicle = (data.get("vehicle") or "").strip()
    urgency = (data.get("urgency") or "").strip()
    issues = (data.get("issues") or "").strip()

    # Basic validation
    if not name or not phone or not vehicle or not urgency or not issues:
        return JSONResponse({"ok": False, "error": "Missing required fields"}, status_code=400)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (created_at, name, phone, email, vehicle, urgency, issues)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (created_at, name, phone, email, vehicle, urgency, issues))
        conn.commit()
        lead_id = cur.lastrowid

    return {"ok": True, "lead_id": lead_id}

@app.get("/api/leads")
def list_leads(limit: int = 50):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, created_at, name, phone, email, vehicle, urgency, issues, status
            FROM leads
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


