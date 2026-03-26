import google.generativeai as generativeai
import gradio as gr
from pathlib import Path
from dotenv import load_dotenv
import os
import mimetypes
import json
from datetime import datetime

load_dotenv()
generativeai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

model = generativeai.GenerativeModel(
    model_name="gemini-2.5-flash",
    safety_settings=safety_settings,
    generation_config={
        "temperature": 0.4,
        "top_p": 1,
        "top_k": 32,
        "max_output_tokens": 4096,
    }
)

scan_history = []

def read_image_data(file_path):
    image_path = Path(file_path)
    if not image_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "image/jpeg"
    return {"mime_type": mime_type, "data": image_path.read_bytes()}

input_prompt = """
You are an expert plant pathologist. Analyze the plant image and respond ONLY with a valid JSON object (no markdown, no extra text) in this exact format:
{
  "disease_name": "Name of disease or Healthy",
  "severity": "Low / Medium / High / None",
  "affected_parts": "leaves / stems / roots / fruits / etc",
  "confidence": 85,
  "symptoms": "Brief description of visible symptoms",
  "cause": "Fungal / Bacterial / Viral / Environmental / None",
  "recommendations": "Specific treatment recommendations",
  "prevention": "Prevention tips",
  "urgency": "Immediate / Soon / Routine / None"
}
"""

def analyze_plant(image_file):
    if image_file is None:
        return None, build_empty_result(), build_history_html()

    try:
        file_path = image_file if isinstance(image_file, str) else image_file.name
        image_data = read_image_data(file_path)
        response = model.generate_content([input_prompt, image_data])
        raw = response.text.strip()

        # Clean possible markdown code fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        data = json.loads(raw)

        # Store in scan history
        scan_history.insert(0, {
            "image": file_path,
            "disease": data.get("disease_name", "Unknown"),
            "severity": data.get("severity", "Unknown"),
            "date": datetime.now().strftime("%b %d, %Y %H:%M"),
            "cause": data.get("cause", "Unknown"),
        })

        return file_path, build_result_html(data), build_history_html()

    except json.JSONDecodeError:
        # Fallback: show raw text
        return image_file, f"""
        <div style="padding:20px;color:#c0392b;background:#fdf2f2;border-radius:12px;border-left:4px solid #e74c3c;">
            <b>⚠️ Could not parse structured response.</b><br><br>{response.text}
        </div>""", build_history_html()
    except Exception as e:
        return None, f"""
        <div style="padding:20px;color:#c0392b;background:#fdf2f2;border-radius:12px;border-left:4px solid #e74c3c;">
            <b>❌ Error:</b> {str(e)}
        </div>""", build_history_html()


def build_empty_result():
    return """
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                height:280px;color:#aaa;font-family:'Segoe UI',sans-serif;">
        <div style="font-size:64px;margin-bottom:16px;">🌿</div>
        <div style="font-size:18px;font-weight:600;color:#888;">Upload a plant image to begin</div>
        <div style="font-size:13px;color:#bbb;margin-top:8px;">AI-powered disease detection & recommendations</div>
    </div>"""


def severity_color(severity):
    return {"High": "#e74c3c", "Medium": "#f39c12", "Low": "#27ae60", "None": "#3498db"}.get(severity, "#95a5a6")

def urgency_badge(urgency):
    colors = {"Immediate": "#e74c3c", "Soon": "#f39c12", "Routine": "#27ae60", "None": "#3498db"}
    return colors.get(urgency, "#95a5a6")

def build_result_html(data):
    sev_color = severity_color(data.get("severity", "None"))
    urg_color = urgency_badge(data.get("urgency", "None"))
    conf = data.get("confidence", 0)
    is_healthy = "healthy" in data.get("disease_name", "").lower()
    card_accent = "#27ae60" if is_healthy else "#e74c3c"

    return f"""
    <div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;max-width:100%;padding:4px;">

      <!-- Header Card -->
      <div style="background:linear-gradient(135deg,{card_accent}22,{card_accent}08);
                  border:2px solid {card_accent}44;border-radius:16px;padding:20px 24px;margin-bottom:16px;">
        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;">
          <div>
            <div style="font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#888;margin-bottom:4px;">Diagnosis</div>
            <div style="font-size:24px;font-weight:800;color:#1a1a2e;">{'✅' if is_healthy else '🦠'} {data.get('disease_name','Unknown')}</div>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap;">
            <div style="background:{sev_color};color:white;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">
              ⚡ {data.get('severity','?')} Severity
            </div>
            <div style="background:{urg_color};color:white;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;">
              🕐 {data.get('urgency','?')} Action
            </div>
          </div>
        </div>

        <!-- Confidence Bar -->
        <div style="margin-top:16px;">
          <div style="display:flex;justify-content:space-between;font-size:12px;color:#666;margin-bottom:6px;">
            <span>AI Confidence</span><span style="font-weight:700;color:{card_accent};">{conf}%</span>
          </div>
          <div style="background:#e8e8e8;border-radius:8px;height:8px;overflow:hidden;">
            <div style="background:linear-gradient(90deg,{card_accent},{card_accent}88);
                        width:{conf}%;height:100%;border-radius:8px;transition:width 0.6s ease;"></div>
          </div>
        </div>
      </div>

      <!-- Stats Row -->
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px;">
        <div style="background:#f8f9ff;border-radius:12px;padding:14px;text-align:center;border:1px solid #e8eaf6;">
          <div style="font-size:24px;">🍃</div>
          <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Affected</div>
          <div style="font-size:13px;font-weight:700;color:#333;margin-top:2px;">{data.get('affected_parts','N/A')}</div>
        </div>
        <div style="background:#f8fff8;border-radius:12px;padding:14px;text-align:center;border:1px solid #e8f5e9;">
          <div style="font-size:24px;">🔬</div>
          <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Cause</div>
          <div style="font-size:13px;font-weight:700;color:#333;margin-top:2px;">{data.get('cause','N/A')}</div>
        </div>
        <div style="background:#fff8f8;border-radius:12px;padding:14px;text-align:center;border:1px solid #fce4ec;">
          <div style="font-size:24px;">📊</div>
          <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:1px;margin-top:4px;">Confidence</div>
          <div style="font-size:13px;font-weight:700;color:#333;margin-top:2px;">{conf}%</div>
        </div>
      </div>

      <!-- Symptoms -->
      <div style="background:#fffbf0;border-left:4px solid #f39c12;border-radius:0 12px 12px 0;
                  padding:14px 18px;margin-bottom:12px;">
        <div style="font-size:12px;font-weight:700;color:#f39c12;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
          🔍 Observed Symptoms
        </div>
        <div style="font-size:14px;color:#555;line-height:1.6;">{data.get('symptoms','No data')}</div>
      </div>

      <!-- Recommendations -->
      <div style="background:#f0fff4;border-left:4px solid #27ae60;border-radius:0 12px 12px 0;
                  padding:14px 18px;margin-bottom:12px;">
        <div style="font-size:12px;font-weight:700;color:#27ae60;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
          💊 Treatment Recommendations
        </div>
        <div style="font-size:14px;color:#555;line-height:1.6;">{data.get('recommendations','No data')}</div>
      </div>

      <!-- Prevention -->
      <div style="background:#f0f4ff;border-left:4px solid #3498db;border-radius:0 12px 12px 0;
                  padding:14px 18px;">
        <div style="font-size:12px;font-weight:700;color:#3498db;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;">
          🛡️ Prevention Tips
        </div>
        <div style="font-size:14px;color:#555;line-height:1.6;">{data.get('prevention','No data')}</div>
      </div>

      <div style="text-align:center;margin-top:16px;font-size:11px;color:#bbb;">
        ⚕️ Consult a qualified agronomist before applying any treatments
      </div>
    </div>
    """

def build_history_html():
    if not scan_history:
        return """
        <div style="text-align:center;padding:30px;color:#ccc;font-family:'Segoe UI',sans-serif;">
            <div style="font-size:36px;">📋</div>
            <div style="margin-top:8px;font-size:14px;">No scans yet. Analyze a plant to see history.</div>
        </div>"""

    items = ""
    for i, scan in enumerate(scan_history[:8]):
        sev = scan.get("severity", "Unknown")
        dot_color = severity_color(sev)
        is_healthy = "healthy" in scan.get("disease", "").lower()
        icon = "✅" if is_healthy else "🦠"
        items += f"""
        <div style="display:flex;align-items:center;gap:14px;padding:12px 16px;
                    background:{'#f8fff8' if is_healthy else '#fff8f8'};border-radius:10px;margin-bottom:8px;
                    border:1px solid {'#e8f5e9' if is_healthy else '#fce4ec'};">
          <div style="width:40px;height:40px;border-radius:10px;background:{dot_color}22;
                      display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">
            {icon}
          </div>
          <div style="flex:1;min-width:0;">
            <div style="font-size:14px;font-weight:700;color:#1a1a2e;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
              {scan.get('disease','Unknown')}
            </div>
            <div style="font-size:11px;color:#999;margin-top:2px;">{scan.get('date','')}</div>
          </div>
          <div style="background:{dot_color};color:white;padding:3px 10px;border-radius:12px;
                      font-size:10px;font-weight:700;flex-shrink:0;">
            {sev}
          </div>
        </div>"""

    return f"""
    <div style="font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;padding:4px;">
      <div style="font-size:13px;font-weight:700;color:#888;text-transform:uppercase;
                  letter-spacing:1px;margin-bottom:12px;">Recent Scans ({len(scan_history)})</div>
      {items}
    </div>"""


# ─── Custom CSS ────────────────────────────────────────────────────────────────
custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Space+Grotesk:wght@400;500;700&display=swap');

* { box-sizing: border-box; }

body, .gradio-container {
    font-family: 'Nunito', sans-serif !important;
    background: #f0f4f0 !important;
    margin: 0 !important;
}

/* ── Navbar ── */
#navbar {
    background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 50%, #40916c 100%);
    padding: 0 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 64px;
    box-shadow: 0 4px 20px rgba(27,67,50,0.3);
    position: sticky;
    top: 0;
    z-index: 1000;
    flex-wrap: wrap;
    gap: 10px;
}

#nav-brand {
    display: flex;
    align-items: center;
    gap: 12px;
}

#nav-brand-icon {
    width: 40px; height: 40px;
    background: rgba(255,255,255,0.2);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
}

#nav-brand-text {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: white;
    letter-spacing: -0.5px;
}

#nav-brand-sub {
    font-size: 10px;
    color: rgba(255,255,255,0.6);
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-top: -4px;
}

#nav-links {
    display: flex;
    gap: 6px;
}

.nav-btn {
    color: rgba(255,255,255,0.85) !important;
    background: transparent !important;
    border: none !important;
    padding: 8px 16px !important;
    border-radius: 8px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    cursor: pointer !important;
    transition: all 0.2s !important;
    font-family: 'Nunito', sans-serif !important;
}

.nav-btn:hover, .nav-btn.active {
    background: rgba(255,255,255,0.15) !important;
    color: white !important;
}

/* ── Hero Banner ── */
#hero {
    background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 60%, #52b788 100%);
    padding: 48px 32px;
    text-align: center;
    position: relative;
    overflow: hidden;
}

#hero::before {
    content: '';
    position: absolute; inset: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}

#hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(28px, 5vw, 48px);
    font-weight: 700;
    color: white;
    margin-bottom: 12px;
    position: relative;
}

#hero-sub {
    font-size: clamp(13px, 2vw, 16px);
    color: rgba(255,255,255,0.75);
    max-width: 560px;
    margin: 0 auto 28px;
    line-height: 1.6;
    position: relative;
}

.hero-stats {
    display: flex;
    justify-content: center;
    gap: 32px;
    flex-wrap: wrap;
    position: relative;
}

.hero-stat {
    text-align: center;
    color: white;
}

.hero-stat-num {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    font-weight: 700;
    line-height: 1;
}

.hero-stat-label {
    font-size: 11px;
    color: rgba(255,255,255,0.6);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-top: 4px;
}

/* ── Main Content ── */
#main-content {
    max-width: 1200px;
    margin: 0 auto;
    padding: 32px 20px;
}

/* ── Section Title ── */
.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 22px;
    font-weight: 700;
    color: #1b4332;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.section-sub {
    font-size: 13px;
    color: #888;
    margin-bottom: 20px;
}

/* ── Cards ── */
.card {
    background: white;
    border-radius: 20px;
    padding: 24px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06);
    border: 1px solid rgba(0,0,0,0.04);
    height: 100%;
}

/* ── Upload Area ── */
.upload-area .gradio-image {
    border-radius: 16px !important;
    border: 2px dashed #b7e4c7 !important;
    background: #f8fff8 !important;
    min-height: 260px !important;
    transition: border-color 0.3s !important;
}

.upload-area .gradio-image:hover {
    border-color: #40916c !important;
}

/* ── Analyze Button ── */
#analyze-btn {
    background: linear-gradient(135deg, #2d6a4f, #40916c) !important;
    border: none !important;
    border-radius: 14px !important;
    color: white !important;
    font-size: 16px !important;
    font-weight: 800 !important;
    padding: 14px 28px !important;
    width: 100% !important;
    cursor: pointer !important;
    font-family: 'Nunito', sans-serif !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 4px 15px rgba(45,106,79,0.35) !important;
}

#analyze-btn:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 25px rgba(45,106,79,0.45) !important;
}

/* ── How it works ── */
#how-section {
    background: linear-gradient(135deg, #f8fff8, #f0f9f4);
    border-radius: 24px;
    padding: 32px;
    margin: 0 20px 32px;
    border: 1px solid #d8f0e0;
}

.how-steps {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 24px;
}

.how-step {
    text-align: center;
    padding: 20px 16px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    border: 1px solid #e8f5e9;
    position: relative;
}

.step-icon {
    font-size: 36px;
    margin-bottom: 12px;
}

.step-num {
    position: absolute;
    top: -10px; left: -10px;
    width: 28px; height: 28px;
    background: linear-gradient(135deg, #2d6a4f, #40916c);
    color: white;
    border-radius: 50%;
    font-size: 12px;
    font-weight: 800;
    display: flex; align-items: center; justify-content: center;
}

.step-title {
    font-weight: 800;
    color: #1b4332;
    font-size: 14px;
    margin-bottom: 6px;
}

.step-desc {
    font-size: 12px;
    color: #888;
    line-height: 1.5;
}

/* ── Disease Stats Section ── */
#stats-section {
    background: white;
    border-radius: 24px;
    padding: 32px;
    margin: 0 20px 32px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06);
    border: 1px solid rgba(0,0,0,0.04);
}

.disease-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 16px;
}

.disease-pill {
    padding: 8px 18px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: 700;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* ── Footer ── */
#footer {
    background: linear-gradient(135deg, #0d2818 0%, #1b4332 100%);
    color: rgba(255,255,255,0.8);
    padding: 48px 32px 24px;
    margin-top: 32px;
}

.footer-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 32px;
    max-width: 1200px;
    margin: 0 auto 32px;
}

.footer-brand h3 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    font-weight: 700;
    color: white;
    margin: 0 0 8px;
}

.footer-brand p {
    font-size: 13px;
    line-height: 1.6;
    color: rgba(255,255,255,0.5);
    margin: 0;
}

.footer-col h4 {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #52b788;
    margin: 0 0 14px;
    font-weight: 700;
}

.footer-col ul {
    list-style: none;
    padding: 0; margin: 0;
}

.footer-col ul li {
    font-size: 13px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 8px;
    cursor: pointer;
    transition: color 0.2s;
}

.footer-col ul li:hover { color: #52b788; }

.footer-bottom {
    border-top: 1px solid rgba(255,255,255,0.1);
    padding-top: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px;
    max-width: 1200px;
    margin: 0 auto;
    font-size: 12px;
    color: rgba(255,255,255,0.35);
}

.footer-badges {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.footer-badge {
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    color: rgba(255,255,255,0.5);
}

/* ── Responsive ── */
@media (max-width: 768px) {
    #navbar { padding: 0 16px; height: auto; padding: 12px 16px; }
    #hero { padding: 32px 16px; }
    #main-content { padding: 20px 12px; }
    .hero-stats { gap: 20px; }
    #how-section, #stats-section { margin: 0 12px 24px; padding: 20px; }
    #footer { padding: 32px 16px 20px; }
}

/* Hide gradio default elements */
.gradio-container > .main > .wrap > .panel { border: none !important; background: transparent !important; }
footer.svelte-1rjryqp { display: none !important; }
"""

# ─── HTML Sections ─────────────────────────────────────────────────────────────

NAVBAR_HTML = """
<div id="navbar">
  <div id="nav-brand">
    <div id="nav-brand-icon">🌿</div>
    <div>
      <div id="nav-brand-text">PhytoScan AI</div>
      <div id="nav-brand-sub">Plant Health Intelligence</div>
    </div>
  </div>
  <div id="nav-links">
    <button class="nav-btn active">🏠 Home</button>
    <button class="nav-btn">🔬 Analyze</button>
    <button class="nav-btn">📊 Dashboard</button>
    <button class="nav-btn">ℹ️ About</button>
  </div>
</div>
"""

HERO_HTML = """
<div id="hero">
  <div id="hero-title">🌱 AI-Powered Plant Disease Detection</div>
  <div id="hero-sub">Upload a photo of your crop and get instant diagnosis, treatment recommendations, and prevention strategies powered by Gemini AI.</div>
  <div class="hero-stats">
    <div class="hero-stat"><div class="hero-stat-num">50+</div><div class="hero-stat-label">Diseases Detected</div></div>
    <div class="hero-stat"><div class="hero-stat-num">95%</div><div class="hero-stat-label">Accuracy Rate</div></div>
    <div class="hero-stat"><div class="hero-stat-num">&lt;3s</div><div class="hero-stat-label">Analysis Time</div></div>
    <div class="hero-stat"><div class="hero-stat-num">Free</div><div class="hero-stat-label">To Use</div></div>
  </div>
</div>
"""

HOW_IT_WORKS_HTML = """
<div id="how-section">
  <div class="section-title">⚙️ How It Works</div>
  <div class="section-sub">Three simple steps to diagnose and treat your plant</div>
  <div class="how-steps">
    <div class="how-step">
      <div class="step-num">1</div>
      <div class="step-icon">📸</div>
      <div class="step-title">Upload Image</div>
      <div class="step-desc">Take a clear photo of the affected plant part — leaves, stems, or fruits.</div>
    </div>
    <div class="how-step">
      <div class="step-num">2</div>
      <div class="step-icon">🤖</div>
      <div class="step-title">AI Analysis</div>
      <div class="step-desc">Gemini AI scans for disease patterns, symptoms, and severity indicators.</div>
    </div>
    <div class="how-step">
      <div class="step-num">3</div>
      <div class="step-icon">💊</div>
      <div class="step-title">Get Report</div>
      <div class="step-desc">Receive diagnosis, treatment plan, and prevention tips in seconds.</div>
    </div>
    <div class="how-step">
      <div class="step-num">4</div>
      <div class="step-icon">🌾</div>
      <div class="step-title">Protect Crops</div>
      <div class="step-desc">Apply recommendations and track plant health over time.</div>
    </div>
  </div>
</div>
"""

DISEASE_INFO_HTML = """
<div id="stats-section">
  <div class="section-title">🦠 Detectable Conditions</div>
  <div class="section-sub">Our AI can identify these common crop diseases and conditions</div>
  <div class="disease-pills">
    <div class="disease-pill" style="background:#fde8e8;color:#c0392b;">🍅 Tomato Blight</div>
    <div class="disease-pill" style="background:#fef3cd;color:#856404;">🌽 Corn Rust</div>
    <div class="disease-pill" style="background:#d4edda;color:#155724;">🥦 Downy Mildew</div>
    <div class="disease-pill" style="background:#cce5ff;color:#004085;">🍇 Powdery Mildew</div>
    <div class="disease-pill" style="background:#f8d7da;color:#721c24;">🥔 Potato Scab</div>
    <div class="disease-pill" style="background:#d1ecf1;color:#0c5460;">🌿 Leaf Spot</div>
    <div class="disease-pill" style="background:#fff3cd;color:#856404;">🌾 Wheat Smut</div>
    <div class="disease-pill" style="background:#e2d9f3;color:#6f42c1;">🍓 Gray Mold</div>
    <div class="disease-pill" style="background:#fde8e8;color:#c0392b;">🫑 Bacterial Wilt</div>
    <div class="disease-pill" style="background:#d4edda;color:#155724;">✅ Healthy Plant</div>
    <div class="disease-pill" style="background:#fef3cd;color:#856404;">🌱 Nutrient Deficiency</div>
    <div class="disease-pill" style="background:#cce5ff;color:#004085;">💧 Root Rot</div>
  </div>
</div>
"""

FOOTER_HTML = """
<div id="footer">
  <div class="footer-grid">
    <div class="footer-brand">
      <h3>🌿 PhytoScan AI</h3>
      <p>AI-powered plant disease detection for farmers, gardeners, and agronomists. Protecting crops through intelligent technology.</p>
    </div>
    <div class="footer-col">
      <h4>Features</h4>
      <ul>
        <li>🔬 Disease Detection</li>
        <li>💊 Treatment Guide</li>
        <li>🛡️ Prevention Tips</li>
        <li>📊 Scan History</li>
        <li>📱 Mobile Friendly</li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>Crops Supported</h4>
      <ul>
        <li>🍅 Tomato</li>
        <li>🌽 Corn / Maize</li>
        <li>🥔 Potato</li>
        <li>🌾 Wheat & Rice</li>
        <li>🫑 Pepper & more</li>
      </ul>
    </div>
    <div class="footer-col">
      <h4>Powered By</h4>
      <ul>
        <li>🤖 Google Gemini 2.5 Flash</li>
        <li>🎨 Gradio UI</li>
        <li>🐍 Python</li>
        <li>🔑 Google AI Studio</li>
      </ul>
    </div>
  </div>
  <div class="footer-bottom">
    <div>© 2026 PhytoScan AI · Built for smarter farming 🌾</div>
    <div class="footer-badges">
      <div class="footer-badge">🆓 Free Tier</div>
      <div class="footer-badge">🔒 Privacy First</div>
      <div class="footer-badge">⚡ Gemini Powered</div>
    </div>
  </div>
</div>
"""

# ─── Gradio Layout ─────────────────────────────────────────────────────────────
with gr.Blocks(css=custom_css, title="PhytoScan AI – Plant Disease Analyzer") as demo:

    # Navbar
    gr.HTML(NAVBAR_HTML)

    # Hero
    gr.HTML(HERO_HTML)

    # ── Analyzer Section ──
    with gr.Column(elem_id="main-content"):
        gr.HTML('<div class="section-title">🔬 Analyze Your Crop</div><div class="section-sub">Upload a clear image of your plant for instant AI diagnosis</div>')

        with gr.Row(equal_height=True):
            # Left: Upload
            with gr.Column(scale=1):
                with gr.Column(elem_classes=["card"]):
                    gr.HTML('<div style="font-size:13px;font-weight:700;color:#2d6a4f;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">📷 Plant Image</div>')
                    image_input = gr.Image(
                        type="filepath",
                        label="",
                        elem_classes=["upload-area"],
                        height=280,
                    )
                    analyze_btn = gr.Button(
                        "🔍 Analyze Now",
                        elem_id="analyze-btn",
                        variant="primary"
                    )
                    gr.HTML("""
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px;">
                      <div style="background:#f8fff8;border:1px solid #d4edda;border-radius:10px;padding:10px;text-align:center;">
                        <div style="font-size:18px;">📸</div>
                        <div style="font-size:11px;color:#555;font-weight:600;margin-top:4px;">JPG / PNG / WEBP</div>
                      </div>
                      <div style="background:#f8f9ff;border:1px solid #d6d9f7;border-radius:10px;padding:10px;text-align:center;">
                        <div style="font-size:18px;">⚡</div>
                        <div style="font-size:11px;color:#555;font-weight:600;margin-top:4px;">Results in &lt;5s</div>
                      </div>
                    </div>
                    """)

            # Right: Results
            with gr.Column(scale=1):
                with gr.Column(elem_classes=["card"]):
                    gr.HTML('<div style="font-size:13px;font-weight:700;color:#2d6a4f;text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">📋 Analysis Results</div>')
                    result_html = gr.HTML(value=build_empty_result())

        # History Section
        gr.HTML('<div style="margin-top:32px;" class="section-title">📅 Scan History</div><div class="section-sub">Your recent plant analyses</div>')
        with gr.Column(elem_classes=["card"]):
            history_html = gr.HTML(value=build_history_html())

    # How it works
    gr.HTML(HOW_IT_WORKS_HTML)

    # Disease info
    gr.HTML(DISEASE_INFO_HTML)

    # Footer
    gr.HTML(FOOTER_HTML)

    # ── Events ──
    analyze_btn.click(
        fn=analyze_plant,
        inputs=[image_input],
        outputs=[image_input, result_html, history_html]
    )

demo.launch(debug=True)
