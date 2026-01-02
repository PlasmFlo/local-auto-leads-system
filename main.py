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
                status TEXT NOT NULL DEFAULT 'new',
                contact_method TEXT,
                contact_time TEXT,
                intent TEXT
            );
        """)
        # Add new columns if they don't exist (for existing databases)
        try:
            conn.execute("ALTER TABLE leads ADD COLUMN contact_method TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE leads ADD COLUMN contact_time TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE leads ADD COLUMN intent TEXT")
        except sqlite3.OperationalError:
            pass
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

    <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #e0e0e0;">
      <p style="font-size: 12px; color: #666; margin: 0 0 16px;">Optional — helps us respond more efficiently.</p>
      
      <label>Preferred Contact Method</label>
      <select name="contact_method">
        <option value="">Select...</option>
        <option value="Call">Call</option>
        <option value="Text">Text</option>
        <option value="Email">Email</option>
      </select>

      <label>Best Time to Contact</label>
      <select name="contact_time">
        <option value="">Select...</option>
        <option value="Morning">Morning</option>
        <option value="Afternoon">Afternoon</option>
        <option value="Evening">Evening</option>
      </select>

      <label>How soon are you looking to move forward?</label>
      <select name="intent">
        <option value="">Select...</option>
        <option value="Just looking for an estimate">Just looking for an estimate</option>
        <option value="Ready to schedule">Ready to schedule</option>
        <option value="Not sure yet">Not sure yet</option>
      </select>
    </div>

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
    let qualifiers = "";
    if (l.contact_method || l.contact_time || l.intent) {
      qualifiers = "<div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #666;'>";
      if (l.contact_method) qualifiers += `<div><b>Preferred Contact:</b> ${l.contact_method}</div>`;
      if (l.contact_time) qualifiers += `<div><b>Best Time:</b> ${l.contact_time}</div>`;
      if (l.intent) qualifiers += `<div><b>Intent:</b> ${l.intent}</div>`;
      qualifiers += "</div>";
    }
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
      ${qualifiers}
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

HOME_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AAMCO Tyler — Service & Repairs</title>
  <meta name="description" content="AAMCO Transmissions & Total Car Care in Tyler, TX. Transmission repair, diagnostics, brakes, exhaust, and maintenance. Clear pricing before work starts." />
  <meta name="robots" content="index,follow" />
  <meta property="og:title" content="AAMCO Tyler — Transmission & Total Car Care" />
  <meta property="og:description" content="AAMCO Transmissions & Total Car Care in Tyler, TX. Transmission repair, diagnostics, brakes, exhaust, and maintenance. Clear pricing before work starts." />
  <meta property="og:type" content="website" />
  <style>
    :root{
      --aamco-blue:#0b3d91;
      --aamco-red:#c8102e;
      --bg:#ffffff;
      --text:#111;
      --muted:#444;
      --card:#f6f7fb;
    }
    body { margin:0; font-family: Arial, sans-serif; background:var(--bg); color:var(--text); }
    .topbar{
      background: linear-gradient(90deg, var(--aamco-blue), #123b6b);
      color:white; padding: 8px 18px;
      display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap;
    }
    .brand{ display:flex; align-items:center; gap:10px; }
    .logo{
      width:36px; height:36px; border-radius:8px;
      background:white; display:flex; align-items:center; justify-content:center;
      font-weight:900; color:var(--aamco-blue); font-size: 18px;
    }
    .brand h1{ font-size: 16px; margin:0; line-height:1.2; }
    .brand p{ margin:2px 0 0; color:#dbe7ff; font-size: 12px; }

    .wrap{ max-width: 980px; margin: 0 auto; padding: 18px; }
    .hero{
      background: radial-gradient(1200px 400px at 20% 0%, #eef4ff 0%, #ffffff 60%);
      border:1px solid #e6e9f2;
      border-radius: 18px;
      padding: 40px 32px;
      margin-top: 12px;
      text-align:center;
    }
    .hero h2{ margin:0 0 14px; font-size: 36px; font-weight: 700; line-height: 1.2; color:var(--text); }
    .hero .sub{ color:var(--muted); margin:0 0 20px; font-size: 17px; line-height: 1.5; }
    .hero .trust{ color:var(--muted); font-size: 13px; margin: 16px 0 28px; opacity: 0.8; }
    .hero .trust span{ margin: 0 10px; }

    .trustSignal{ 
      color:var(--muted); font-size: 14px; 
      margin: 24px 0 0; padding-top: 20px; 
      border-top: 1px solid #e6e9f2; 
      text-align:center;
    }

    .visitUs{
      background:var(--card); border:1px solid #e6e9f2; border-radius: 18px;
      padding: 24px; margin-top: 32px; text-align:center;
    }
    .visitUs h3{ margin:0 0 12px; font-size: 20px; font-weight: 600; color:var(--text); }
    .visitUs .address{ color:var(--muted); font-size: 15px; margin: 0 0 12px; line-height: 1.5; }
    .visitUs .hours{ color:var(--muted); font-size: 13px; margin: 0 0 8px; line-height: 1.4; }
    .visitUs .hoursDisclaimer{ color:var(--muted); font-size: 11px; margin: 0 0 16px; opacity: 0.7; font-style: italic; }
    .visitUs .directionsBtn{ 
      display:inline-block; padding: 12px 20px; border-radius: 12px;
      border:2px solid var(--aamco-blue); color:var(--aamco-blue); 
      background:white; text-decoration:none; font-weight: 700; font-size: 14px;
      transition: all 0.2s;
    }
    .visitUs .directionsBtn:hover{ background:#f6f7fb; transform: translateY(-1px); }

    .ctaRow{ display:flex; gap:14px; flex-wrap:wrap; align-items:center; justify-content:center; margin-top: 24px; }
    .btn{
      display:inline-block; padding: 12px 14px; border-radius: 14px;
      text-decoration:none; font-weight: 800; transition: all 0.2s;
    }
    .btnPrimary{ background:var(--aamco-red); color:white; font-size: 17px; padding: 18px 32px; box-shadow: 0 2px 8px rgba(200,16,46,0.2); }
    .btnPrimary:hover{ filter: brightness(0.95); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(200,16,46,0.3); }
    .btnSecondary{ border:2px solid var(--aamco-blue); color:var(--aamco-blue); background:white; font-size: 15px; padding: 16px 26px; }
    .btnSecondary:hover{ background:#f6f7fb; }

    .ctaMicro{ color:var(--muted); font-size: 13px; margin-top: 12px; }
    .reassurance{ color:var(--muted); font-size: 14px; margin-top: 16px; font-style: italic; }
    .whatNext{ 
      color:var(--muted); font-size: 13px; margin-top: 24px; 
      padding-top: 20px; border-top: 1px solid #e6e9f2;
    }
    .whatNext h4{ margin:0 0 10px; font-size: 14px; font-weight: 600; color:var(--text); }
    .whatNext ol{ margin:0; padding-left: 20px; line-height: 1.6; }
    .whatNext li{ margin: 4px 0; }

    .services{ margin-top: 48px; }
    .services h3{ font-size: 24px; margin:0 0 20px; text-align:center; font-weight: 600; color:var(--text); }
    .servicesGrid{ display:grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap:14px; }
    .serviceCard{ 
      background:var(--card); border:1px solid #e6e9f2; border-radius: 12px; 
      padding: 18px 16px; text-align:center; 
      display:flex; flex-direction:column; justify-content:space-between;
      min-height: 90px;
    }
    .serviceCard h4{ margin:0 0 8px; font-size: 16px; color:var(--aamco-blue); font-weight: 600; }
    .serviceCard p{ margin:0; color:var(--muted); font-size: 13px; line-height: 1.4; }

    .testimonials{ margin-top: 48px; }
    .testimonials h2{ font-size: 24px; margin:0 0 20px; text-align:center; font-weight: 600; color:var(--text); }
    .tGrid{ display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:16px; max-width: 800px; margin: 0 auto; }
    .tCard{ 
      background:var(--card); border:1px solid #e6e9f2; border-radius: 18px; 
      padding: 24px; text-align:left;
    }
    .tCard .stars{ color:#f4a261; font-size: 18px; margin:0 0 12px; letter-spacing: 2px; }
    .tCard .quote{ color:var(--text); font-size: 16px; line-height: 1.6; margin:0 0 14px; font-style: italic; }
    .tCard .who{ color:var(--muted); font-size: 13px; margin:0; }

    .grid{ display:grid; grid-template-columns: 1fr; gap:14px; margin-top: 40px; }
    @media(min-width: 860px){ .grid{ grid-template-columns: 1fr 1fr; } }

    .card{ background:var(--card); border:1px solid #e6e9f2; border-radius: 18px; padding: 18px; }
    .card h3{ margin:0 0 12px; font-size: 18px; font-weight: 600; }
    .list{ margin:0; padding-left: 18px; color:var(--muted); line-height: 1.6; }
    .line{ color:var(--muted); margin: 8px 0; line-height: 1.5; }
    footer{ color:#666; padding: 20px 18px 28px; text-align:center; font-size: 12px; line-height: 1.6; }
    footer a{ color:#666; text-decoration:none; }
    footer a:hover{ text-decoration:underline; }
  </style>
</head>
<body>
  <div class="topbar">
    <div class="brand">
      <div class="logo">A</div>
      <div>
        <h1>AAMCO Transmissions & Total Car Care</h1>
        <p>Tyler, TX • 2002 Broussard St • (903) 415-5772</p>
      </div>
    </div>
    <div>
      <a class="btn btnPrimary" href="tel:19034155772" style="font-size: 14px; padding: 10px 18px;">Call Now</a>
    </div>
  </div>

  <div class="wrap">
    <div class="hero">
      <h2>Transmission & Total Car Care in Tyler, TX</h2>
      <p class="sub">Diagnostics, repairs, and maintenance — clear pricing before work starts.</p>
      <div class="trust">
        <span>Open</span> • <span>Closes 5 PM</span> • <span>3.9★ • 128 reviews</span>
      </div>
      <div class="ctaRow">
        <a class="btn btnPrimary" href="tel:19034155772">Call Now</a>
        <a class="btn btnSecondary" href="/request-service">Request Service</a>
      </div>
      <div class="ctaMicro">Prefer not to wait on hold? Use Request Service.</div>
      <div class="reassurance">You'll know the cost before any work is done.</div>
      <div class="whatNext">
        <h4>What happens next</h4>
        <ol>
          <li>Call or submit a request</li>
          <li>We review your issue</li>
          <li>We contact you to confirm details and schedule</li>
        </ol>
      </div>
    </div>

    <div class="trustSignal">
      Local Tyler shop • Clear pricing before work starts
    </div>

    <div class="visitUs">
      <h3>Visit Us</h3>
      <div class="address">2002 Broussard St<br>Tyler, TX 75701</div>
      <div class="hours">Open • Closes 5 PM</div>
      <div class="hoursDisclaimer">Hours may vary on holidays.</div>
      <a href="https://www.google.com/maps/search/?api=1&query=2002%20Broussard%20Street%2C%20Tyler%2C%20TX%2075701" target="_blank" class="directionsBtn">Get Directions</a>
    </div>

    <div class="services">
      <h3>Our Services</h3>
      <div class="servicesGrid">
        <div class="serviceCard">
          <h4>Transmission Repair</h4>
          <p>Diagnostics, rebuilds, fluid service</p>
        </div>
        <div class="serviceCard">
          <h4>Engine Repair</h4>
          <p>Diagnostics, tune-ups, repairs</p>
        </div>
        <div class="serviceCard">
          <h4>Brake Repair</h4>
          <p>Pads, rotors, inspections</p>
        </div>
        <div class="serviceCard">
          <h4>Exhaust Repair</h4>
          <p>Mufflers, pipes, catalytic converters</p>
        </div>
        <div class="serviceCard">
          <h4>Maintenance</h4>
          <p>Oil changes, filters, inspections</p>
        </div>
      </div>
    </div>

    <div class="testimonials">
      <h2>Trusted by Tyler Drivers</h2>
      <div class="tGrid">
        <div class="tCard">
          <div class="stars">★★★★★</div>
          <div class="quote">"These guys were awesome. They explained what needed to happen and the best option moving forward. I recommend them any day."</div>
          <div class="who">— Carol T., Google Review</div>
        </div>
      </div>
    </div>

    <div class="grid">
      <div class="card">
        <h3>How it works</h3>
        <p class="line"><b>1)</b> Fill out your vehicle issue and urgency.</p>
        <p class="line"><b>2)</b> Your request is sent instantly to the shop.</p>
        <p class="line"><b>3)</b> A service advisor contacts you to schedule.</p>
      </div>

      <div class="card">
        <h3>Common transmission signs</h3>
        <ul class="list">
          <li>Slipping or delayed shifting</li>
          <li>Grinding noises</li>
          <li>Burning smell</li>
          <li>Warning lights</li>
          <li>Fluid leaks</li>
        </ul>
      </div>
    </div>
  </div>

  <footer>
    Demo intake page for AAMCO Tyler. Not an official AAMCO corporate website.
    <br><a href="/owner">Owner Live Leads</a>
  </footer>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
def home_page():
    return HTMLResponse(HOME_HTML)

@app.get("/request-service", response_class=HTMLResponse)
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
    contact_method = (data.get("contact_method") or "").strip() or None
    contact_time = (data.get("contact_time") or "").strip() or None
    intent = (data.get("intent") or "").strip() or None

    # Basic validation
    if not name or not phone or not vehicle or not urgency or not issues:
        return JSONResponse({"ok": False, "error": "Missing required fields"}, status_code=400)

    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO leads (created_at, name, phone, email, vehicle, urgency, issues, contact_method, contact_time, intent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (created_at, name, phone, email, vehicle, urgency, issues, contact_method, contact_time, intent))
        conn.commit()
        lead_id = cur.lastrowid

    return {"ok": True, "lead_id": lead_id}

@app.get("/api/leads")
def list_leads(limit: int = 50):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT id, created_at, name, phone, email, vehicle, urgency, issues, status, contact_method, contact_time, intent
            FROM leads
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


