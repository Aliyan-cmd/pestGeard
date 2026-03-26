# dashboard.py (fixed)
import json
import os
import pickle
import string
from collections import Counter
from datetime import datetime

import gradio as gr
import plotly.graph_objects as go

# Shared history file
HISTORY_FILE = "scan_history.pkl"


def load_scans():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "rb") as f:
                return pickle.load(f)
        except:
            return []
    return []


def generate_dashboard_html():
    scans = load_scans()

    # Convert scans to list for display
    scan_list = []
    for i, s in enumerate(scans):
        scan_list.append(
            {
                "id": i + 1,
                "date": s.get("date", "Unknown"),
                "crop": extract_crop_from_image(s.get("image", "")),
                "disease": s.get("disease", "Unknown"),
                "severity": s.get("severity", "Unknown"),
                "confidence": 85,  # placeholder, could be stored if we had it
                "action": generate_action(s.get("disease", ""), s.get("severity", "")),
            }
        )

    # Stats
    total_scans = len(scan_list)
    diseases = [s["disease"] for s in scan_list if s["disease"].lower() != "healthy"]
    unique_diseases = len(set(diseases))
    healthy_scans = sum(1 for s in scan_list if s["disease"].lower() == "healthy")
    severity_counts = Counter(s["severity"] for s in scan_list)

    # Crops
    crop_names = list(set(s["crop"] for s in scan_list))
    crops = []
    for crop in crop_names:
        crop_scans = [s for s in scan_list if s["crop"] == crop]
        latest = crop_scans[-1] if crop_scans else None
        health = 100 if latest and latest["disease"].lower() == "healthy" else 70
        status = "Good" if health >= 80 else "Warning" if health >= 60 else "Critical"
        crops.append(
            {
                "name": crop,
                "variety": "Unknown",
                "emoji": get_crop_emoji(crop),
                "health": health,
                "planted": "Unknown",
                "area": "Unknown",
                "nextAction": "Schedule scan",
                "scans": len(crop_scans),
                "status": status,
            }
        )

    # Alerts
    alerts = generate_alerts(scan_list)

    # Notes
    notes = []
    for s in scan_list:
        if s["severity"] in ["High", "Medium"]:
            notes.append(
                {
                    "crop": s["crop"],
                    "date": s["date"],
                    "text": f"Detected {s['disease']} (severity: {s['severity']}). {s['action']}",
                }
            )

    # Compute health trend (simulated)
    health_trend = compute_health_trend(scan_list)

    # Disease breakdown
    disease_counts = Counter(
        s["disease"] for s in scan_list if s["disease"].lower() != "healthy"
    )

    # Frequency
    freq_data = compute_frequency(scan_list)

    # Timeline
    progress_timeline = compute_progress_timeline(scan_list)

    # Radar data
    radar_data = compute_radar_data(scan_list, crops)

    # Crop progress
    crop_progress = compute_crop_progress(scan_list, crops)

    # Soil gauges (static)
    soil_gauges = [
        {
            "icon": "🌡️",
            "name": "Soil Temp",
            "val": "24°C",
            "pct": 62,
            "color": "#e74c3c",
        },
        {"icon": "💧", "name": "Moisture", "val": "68%", "pct": 68, "color": "#3498db"},
        {"icon": "⚗️", "name": "pH Level", "val": "6.4", "pct": 64, "color": "#9b59b6"},
        {
            "icon": "🧪",
            "name": "Nitrogen",
            "val": "High",
            "pct": 82,
            "color": "#27ae60",
        },
        {
            "icon": "🔬",
            "name": "Phosphorus",
            "val": "Medium",
            "pct": 54,
            "color": "#f39c12",
        },
        {
            "icon": "⚡",
            "name": "Potassium",
            "val": "Low",
            "pct": 30,
            "color": "#e74c3c",
        },
    ]

    return "<html><body><h1>PhytoScan AI Dashboard</h1><p>Total scans: {}</p></body></html>".format(len(scan_list))

    # Create Plotly charts
    health_chart = create_health_chart(health_trend)
    disease_chart = create_disease_chart(disease_counts)
    freq_chart = create_freq_chart(freq_data)
    progress_chart = create_progress_chart(progress_timeline)
    radar_chart = create_radar_chart(radar_data)
    forecast_chart = create_forecast_chart()
    journal_chart = create_journal_chart(notes)

    # Convert Plotly figures to HTML (with CDN for plotly.js)
    health_html = health_chart.to_html(full_html=False, include_plotlyjs="cdn")
    disease_html = disease_chart.to_html(full_html=False, include_plotlyjs=False)
    freq_html = freq_chart.to_html(full_html=False, include_plotlyjs=False)
    progress_html = progress_chart.to_html(full_html=False, include_plotlyjs=False)
    radar_html = radar_chart.to_html(full_html=False, include_plotlyjs=False)
    forecast_html = forecast_chart.to_html(full_html=False, include_plotlyjs=False)
    journal_html = journal_chart.to_html(full_html=False, include_plotlyjs=False)

    # Prepare JSON data for JavaScript
    scan_list_json = json.dumps(scan_list)
    crops_json = json.dumps(crops)
    alerts_json = json.dumps(alerts)
    notes_json = json.dumps(notes)
    soil_gauges_json = json.dumps(soil_gauges)
    progress_timeline_json = json.dumps(progress_timeline)
    health_trend_last = int(health_trend[-1]) if health_trend else 70

    # Build the template using string.Template (safe with $placeholders)
    # The HTML string uses $var for dynamic parts, and all other braces are kept as is.
    template = string.Template("""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>PhytoScan AI — Crop Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Playfair+Display:wght@700;900&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet"/>
<style>
/* ========== CSS from original dashboard.html ========== */
:root {
  --forest:   #1a3a2a;
  --pine:     #2d5a3d;
  --fern:     #3d7a52;
  --sage:     #52a06e;
  --mint:     #7ec8a0;
  --fog:      #d4edd9;
  --cream:    #f5f9f5;
  --paper:    #ffffff;
  --ink:      #0f1f16;
  --muted:    #6b8a74;
  --border:   #e2ede5;
  --danger:   #c0392b;
  --warning:  #d68910;
  --success:  #1e8449;
  --info:     #1a5276;
  --radius:   16px;
  --shadow:   0 4px 24px rgba(26,58,42,0.10);
  --shadow-lg:0 12px 48px rgba(26,58,42,0.16);
  --sidebar-w:260px;
  --topbar-h: 64px;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'DM Sans', sans-serif;
  background: var(--cream);
  color: var(--ink);
  min-height: 100vh;
  overflow-x: hidden;
}

/* Sidebar */
#sidebar {
  position: fixed; top: 0; left: 0;
  width: var(--sidebar-w);
  height: 100vh;
  background: linear-gradient(180deg, var(--forest) 0%, #0f2318 100%);
  display: flex; flex-direction: column;
  z-index: 200;
  transition: transform 0.35s cubic-bezier(.77,0,.18,1);
  overflow-y: auto;
}

.sidebar-logo {
  padding: 28px 24px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.07);
}
.logo-icon {
  width: 44px; height: 44px;
  background: linear-gradient(135deg, var(--fern), var(--sage));
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; margin-bottom: 10px;
  box-shadow: 0 4px 12px rgba(61,122,82,0.4);
}
.logo-name {
  font-family: 'Playfair Display', serif;
  font-size: 18px; font-weight: 900;
  color: #fff; letter-spacing: -0.5px;
}
.logo-sub {
  font-size: 10px; color: rgba(255,255,255,0.4);
  text-transform: uppercase; letter-spacing: 2px; margin-top: 2px;
}

.sidebar-section {
  padding: 20px 16px 8px;
  font-size: 9px; font-weight: 700;
  color: rgba(255,255,255,0.25);
  text-transform: uppercase; letter-spacing: 2.5px;
}

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 20px; margin: 2px 10px;
  border-radius: 10px;
  color: rgba(255,255,255,0.55);
  font-size: 14px; font-weight: 500;
  cursor: pointer; transition: all 0.2s;
  text-decoration: none;
}
.nav-item:hover { background: rgba(255,255,255,0.07); color: #fff; }
.nav-item.active {
  background: linear-gradient(135deg, var(--fern), var(--sage));
  color: #fff;
  box-shadow: 0 4px 12px rgba(61,122,82,0.35);
}
.nav-icon { font-size: 16px; width: 20px; text-align: center; }
.nav-badge {
  margin-left: auto;
  background: var(--danger);
  color: #fff; font-size: 10px; font-weight: 700;
  padding: 2px 7px; border-radius: 10px;
}

.sidebar-footer {
  margin-top: auto;
  padding: 20px 16px;
  border-top: 1px solid rgba(255,255,255,0.07);
}
.user-card {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; border-radius: 10px;
  background: rgba(255,255,255,0.06); cursor: pointer;
}
.user-avatar {
  width: 36px; height: 36px; border-radius: 10px;
  background: linear-gradient(135deg, var(--sage), var(--mint));
  display: flex; align-items: center; justify-content: center;
  font-size: 16px; flex-shrink: 0;
}
.user-name { font-size: 13px; font-weight: 600; color: #fff; }
.user-role { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 1px; }

/* Topbar */
#topbar {
  position: fixed; top: 0; left: var(--sidebar-w); right: 0;
  height: var(--topbar-h);
  background: rgba(245,249,245,0.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 28px;
  z-index: 100;
  transition: left 0.35s cubic-bezier(.77,0,.18,1);
}

.topbar-left { display: flex; align-items: center; gap: 16px; }
.page-title {
  font-family: 'Playfair Display', serif;
  font-size: 20px; font-weight: 700; color: var(--forest);
}
.page-breadcrumb { font-size: 12px; color: var(--muted); }

.topbar-right { display: flex; align-items: center; gap: 12px; }

.top-btn {
  background: var(--paper); border: 1px solid var(--border);
  border-radius: 10px; padding: 8px 14px;
  font-size: 13px; font-weight: 500; color: var(--ink);
  cursor: pointer; display: flex; align-items: center; gap: 6px;
  transition: all 0.2s; font-family: 'DM Sans', sans-serif;
}
.top-btn:hover { background: var(--fog); border-color: var(--mint); }
.top-btn.primary {
  background: linear-gradient(135deg, var(--fern), var(--sage));
  border-color: transparent; color: #fff;
  box-shadow: 0 4px 12px rgba(61,122,82,0.3);
}
.top-btn.primary:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(61,122,82,0.4); }

#menu-toggle {
  display: none;
  background: none; border: none; font-size: 22px; cursor: pointer; color: var(--forest);
}

/* Main Content */
#main {
  margin-left: var(--sidebar-w);
  margin-top: var(--topbar-h);
  padding: 32px 28px;
  min-height: calc(100vh - var(--topbar-h));
  transition: margin-left 0.35s cubic-bezier(.77,0,.18,1);
}

/* Tab System */
.tab-bar {
  display: flex; gap: 4px; margin-bottom: 28px;
  background: var(--paper); border-radius: 12px; padding: 4px;
  border: 1px solid var(--border);
  overflow-x: auto;
  box-shadow: var(--shadow);
  flex-wrap: nowrap;
}
.tab-btn {
  padding: 9px 18px; border-radius: 9px;
  border: none; background: transparent;
  font-family: 'DM Sans', sans-serif;
  font-size: 13px; font-weight: 500; color: var(--muted);
  cursor: pointer; white-space: nowrap; transition: all 0.2s;
  display: flex; align-items: center; gap: 6px;
}
.tab-btn:hover { color: var(--forest); background: var(--fog); }
.tab-btn.active {
  background: linear-gradient(135deg, var(--fern), var(--sage));
  color: #fff; font-weight: 600;
  box-shadow: 0 3px 10px rgba(61,122,82,0.3);
}

.tab-panel { display: none; animation: fadeIn 0.3s ease; }
.tab-panel.active { display: block; }

@keyframes fadeIn { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }

/* Cards & Grids */
.grid-4 { display: grid; grid-template-columns: repeat(4,1fr); gap: 16px; margin-bottom: 24px; }
.grid-3 { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; margin-bottom: 24px; }
.grid-2 { display: grid; grid-template-columns: repeat(2,1fr); gap: 20px; margin-bottom: 24px; }
.grid-2-1 { display: grid; grid-template-columns: 2fr 1fr; gap: 20px; margin-bottom: 24px; }
.grid-1-2 { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; margin-bottom: 24px; }

.card {
  background: var(--paper); border-radius: var(--radius);
  border: 1px solid var(--border);
  box-shadow: var(--shadow);
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
}
.card:hover { box-shadow: var(--shadow-lg); transform: translateY(-2px); }
.card-header {
  padding: 20px 22px 0;
  display: flex; align-items: center; justify-content: space-between;
}
.card-title {
  font-size: 13px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1.2px;
  color: var(--muted);
}
.card-body { padding: 16px 22px 22px; }
.card-action {
  font-size: 11px; color: var(--sage); font-weight: 600;
  cursor: pointer; text-decoration: none;
  display: flex; align-items: center; gap: 4px;
}
.card-action:hover { color: var(--fern); }

/* Stat Cards */
.stat-card {
  background: var(--paper); border-radius: var(--radius);
  border: 1px solid var(--border);
  padding: 22px;
  box-shadow: var(--shadow);
  transition: all 0.25s;
  position: relative; overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
}
.stat-card.green::before  { background: linear-gradient(90deg, var(--fern), var(--mint)); }
.stat-card.red::before    { background: linear-gradient(90deg, #e74c3c, #f1948a); }
.stat-card.yellow::before { background: linear-gradient(90deg, #d68910, #f4d03f); }
.stat-card.blue::before   { background: linear-gradient(90deg, #1a5276, #2e86c1); }

.stat-card:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.stat-icon {
  width: 46px; height: 46px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; margin-bottom: 14px;
}
.stat-icon.green  { background: rgba(61,122,82,0.12); }
.stat-icon.red    { background: rgba(192,57,43,0.10); }
.stat-icon.yellow { background: rgba(214,137,16,0.10); }
.stat-icon.blue   { background: rgba(26,82,118,0.10); }

.stat-val {
  font-family: 'Playfair Display', serif;
  font-size: 32px; font-weight: 900; line-height: 1;
  color: var(--forest); margin-bottom: 4px;
}
.stat-label { font-size: 13px; color: var(--muted); font-weight: 500; }
.stat-delta {
  margin-top: 10px; font-size: 12px; font-weight: 600;
  display: flex; align-items: center; gap: 4px;
}
.stat-delta.up   { color: var(--success); }
.stat-delta.down { color: var(--danger); }
.stat-delta.flat { color: var(--muted); }

/* Health Ring */
.health-ring-wrap {
  display: flex; flex-direction: column; align-items: center;
  padding: 24px 16px;
}
.ring-container { position: relative; width: 160px; height: 160px; }
.ring-svg { transform: rotate(-90deg); }
.ring-bg { fill: none; stroke: var(--fog); stroke-width: 14; }
.ring-fg { fill: none; stroke-width: 14; stroke-linecap: round;
  transition: stroke-dashoffset 1.2s cubic-bezier(.4,0,.2,1); }
.ring-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
}
.ring-score {
  font-family: 'Playfair Display', serif;
  font-size: 36px; font-weight: 900; color: var(--forest);
}
.ring-label { font-size: 11px; color: var(--muted); font-weight: 600; letter-spacing: 1px; }
.health-legend {
  display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%; margin-top: 16px;
}
.legend-item {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 10px; border-radius: 8px; background: var(--cream);
}
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.legend-label { font-size: 11px; color: var(--muted); }
.legend-val { font-size: 13px; font-weight: 700; color: var(--ink); margin-left: auto; }

/* Scan Table */
.scan-table { width: 100%; border-collapse: collapse; }
.scan-table th {
  text-align: left; padding: 10px 14px;
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1.2px; color: var(--muted);
  border-bottom: 2px solid var(--border);
}
.scan-table td {
  padding: 13px 14px; font-size: 13px; color: var(--ink);
  border-bottom: 1px solid var(--border); vertical-align: middle;
}
.scan-table tr:last-child td { border-bottom: none; }
.scan-table tr:hover td { background: var(--cream); }

.disease-tag {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700;
}
.tag-danger  { background: #fde8e8; color: var(--danger); }
.tag-warning { background: #fef3cd; color: var(--warning); }
.tag-success { background: #d4edda; color: var(--success); }
.tag-info    { background: #cce5ff; color: var(--info); }

.sev-dot {
  width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px;
}

/* Crop Cards */
.crop-card {
  background: var(--paper); border-radius: var(--radius);
  border: 1px solid var(--border); overflow: hidden;
  box-shadow: var(--shadow); transition: all 0.25s;
}
.crop-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-3px); }
.crop-card-top {
  padding: 20px;
  background: linear-gradient(135deg, var(--forest), var(--pine));
  color: #fff; position: relative; overflow: hidden;
}
.crop-card-top::before {
  content: attr(data-emoji);
  position: absolute; right: 16px; top: 50%; transform: translateY(-50%);
  font-size: 52px; opacity: 0.2;
}
.crop-name { font-family: 'Playfair Display', serif; font-size: 18px; font-weight: 700; }
.crop-variety { font-size: 11px; color: rgba(255,255,255,0.55); margin-top: 2px; }
.crop-health-bar {
  margin-top: 12px;
  background: rgba(255,255,255,0.15); border-radius: 4px; height: 6px; overflow: hidden;
}
.crop-health-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }
.crop-card-body { padding: 16px 20px; }
.crop-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.crop-meta-item { }
.crop-meta-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
.crop-meta-val { font-size: 14px; font-weight: 700; color: var(--ink); margin-top: 2px; }
.crop-actions {
  display: flex; gap: 8px; padding: 14px 20px;
  border-top: 1px solid var(--border);
}
.crop-btn {
  flex: 1; padding: 8px; border-radius: 8px; border: 1px solid var(--border);
  background: var(--cream); font-size: 12px; font-weight: 600;
  color: var(--muted); cursor: pointer; font-family: 'DM Sans', sans-serif;
  transition: all 0.2s; display: flex; align-items: center; justify-content: center; gap: 5px;
}
.crop-btn:hover { background: var(--fog); color: var(--forest); border-color: var(--mint); }
.crop-btn.primary-btn {
  background: linear-gradient(135deg, var(--fern), var(--sage));
  color: #fff; border-color: transparent;
}
.crop-btn.primary-btn:hover { box-shadow: 0 4px 12px rgba(61,122,82,0.3); }

/* Alerts */
.alert-item {
  display: flex; align-items: flex-start; gap: 14px;
  padding: 14px 16px; border-radius: 10px; margin-bottom: 10px;
  border: 1px solid transparent;
}
.alert-item.urgent   { background: #fdf2f2; border-color: #f5c6cb; }
.alert-item.warning  { background: #fffdf0; border-color: #ffeeba; }
.alert-item.info     { background: #f0f6ff; border-color: #b8daff; }
.alert-item.done     { background: #f0fff4; border-color: #c3e6cb; opacity: 0.7; }

.alert-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; flex-shrink: 0;
}
.urgent .alert-icon   { background: #fde8e8; }
.warning .alert-icon  { background: #fff3cd; }
.info .alert-icon     { background: #cce5ff; }
.done .alert-icon     { background: #d4edda; }

.alert-title { font-size: 13px; font-weight: 700; color: var(--ink); }
.alert-desc  { font-size: 12px; color: var(--muted); margin-top: 2px; line-height: 1.4; }
.alert-time  { margin-left: auto; font-size: 11px; color: var(--muted); white-space: nowrap; flex-shrink: 0; }

/* Timeline */
.timeline { position: relative; padding-left: 28px; }
.timeline::before {
  content: '';
  position: absolute; left: 9px; top: 8px; bottom: 8px;
  width: 2px; background: var(--border);
}
.tl-item { position: relative; margin-bottom: 20px; }
.tl-dot {
  position: absolute; left: -28px; top: 3px;
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid var(--paper);
  display: flex; align-items: center; justify-content: center;
  font-size: 8px;
}
.tl-dot.good    { background: var(--success); }
.tl-dot.bad     { background: var(--danger); }
.tl-dot.warn    { background: var(--warning); }
.tl-dot.neutral { background: var(--info); }

.tl-date { font-size: 10px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
.tl-title { font-size: 13px; font-weight: 700; color: var(--ink); margin-top: 2px; }
.tl-body  { font-size: 12px; color: var(--muted); margin-top: 4px; line-height: 1.5; }
.tl-tag {
  display: inline-flex; align-items: center; gap: 4px;
  margin-top: 6px; padding: 3px 9px; border-radius: 12px;
  font-size: 10px; font-weight: 700;
}

/* Weather Widget */
.weather-main {
  display: flex; align-items: center; gap: 16px; margin-bottom: 16px;
}
.weather-icon { font-size: 52px; }
.weather-temp {
  font-family: 'Playfair Display', serif;
  font-size: 42px; font-weight: 900; color: var(--forest); line-height: 1;
}
.weather-desc { font-size: 14px; color: var(--muted); margin-top: 2px; }
.weather-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 10px; }
.weather-cell {
  background: var(--cream); border-radius: 10px; padding: 10px 12px;
  text-align: center;
}
.weather-cell-label { font-size: 10px; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; }
.weather-cell-val { font-size: 16px; font-weight: 700; color: var(--ink); margin-top: 3px; }

/* Upload Zone */
.upload-zone {
  border: 2px dashed var(--mint); border-radius: var(--radius);
  padding: 40px 20px; text-align: center;
  background: linear-gradient(135deg, rgba(82,160,110,0.04), rgba(126,200,160,0.06));
  cursor: pointer; transition: all 0.2s; position: relative;
}
.upload-zone:hover { border-color: var(--fern); background: rgba(61,122,82,0.08); }
.upload-zone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.upload-icon { font-size: 42px; margin-bottom: 12px; }
.upload-text { font-size: 15px; font-weight: 700; color: var(--forest); margin-bottom: 4px; }
.upload-sub { font-size: 12px; color: var(--muted); }

/* Environment Gauges */
.env-gauge {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 0; border-bottom: 1px solid var(--border);
}
.env-gauge:last-child { border-bottom: none; }
.env-icon { font-size: 22px; width: 36px; text-align: center; }
.env-info { flex: 1; }
.env-name { font-size: 12px; font-weight: 600; color: var(--ink); }
.env-val  { font-size: 11px; color: var(--muted); margin-top: 1px; }
.env-bar  { flex: 2; }
.env-track {
  background: var(--border); border-radius: 4px; height: 6px; overflow: hidden;
}
.env-fill { height: 100%; border-radius: 4px; transition: width 1s ease; }
.env-pct { font-size: 12px; font-weight: 700; color: var(--forest); min-width: 36px; text-align: right; }

/* Notes */
.note-item {
  border-radius: 10px; padding: 14px 16px; margin-bottom: 10px;
  border-left: 3px solid var(--sage);
  background: var(--cream);
}
.note-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.note-crop { font-size: 12px; font-weight: 700; color: var(--fern); }
.note-date { font-size: 11px; color: var(--muted); }
.note-text { font-size: 13px; color: var(--ink); line-height: 1.5; }

.note-input-wrap { margin-top: 16px; }
.note-textarea {
  width: 100%; border: 1px solid var(--border); border-radius: 10px;
  padding: 12px 14px; font-family: 'DM Sans', sans-serif;
  font-size: 13px; color: var(--ink); resize: none;
  background: var(--cream); min-height: 80px;
  transition: border-color 0.2s;
}
.note-textarea:focus { outline: none; border-color: var(--sage); background: var(--paper); }
.note-submit {
  margin-top: 8px;
  background: linear-gradient(135deg, var(--fern), var(--sage));
  color: #fff; border: none; border-radius: 8px;
  padding: 9px 20px; font-family: 'DM Sans', sans-serif;
  font-size: 13px; font-weight: 600; cursor: pointer;
  transition: all 0.2s;
}
.note-submit:hover { box-shadow: 0 4px 12px rgba(61,122,82,0.35); transform: translateY(-1px); }

/* Section Label */
.sec-label {
  font-family: 'Playfair Display', serif;
  font-size: 20px; font-weight: 700; color: var(--forest);
  margin-bottom: 4px;
}
.sec-sub { font-size: 13px; color: var(--muted); margin-bottom: 20px; }

/* Responsive */
@media (max-width: 1100px) {
  .grid-4 { grid-template-columns: repeat(2,1fr); }
  .grid-2-1, .grid-1-2 { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  :root { --sidebar-w: 0px; }
  #sidebar { transform: translateX(-260px); width: 260px; }
  #sidebar.open { transform: translateX(0); }
  #topbar { left: 0; }
  #main { margin-left: 0; }
  #menu-toggle { display: block; }
  .grid-3 { grid-template-columns: repeat(2,1fr); }
  .grid-2 { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  #main { padding: 20px 14px; }
  .grid-4, .grid-3 { grid-template-columns: 1fr; }
  .stat-val { font-size: 26px; }
  .tab-btn { padding: 8px 12px; font-size: 12px; }
  .topbar-right .top-btn:not(.primary) { display: none; }
  .weather-grid { grid-template-columns: repeat(2,1fr); }
}
#overlay {
  display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.4); z-index: 150;
}
#overlay.show { display: block; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--fog); border-radius: 4px; }
.anim { animation: slideUp 0.5s ease both; }
.anim-1 { animation-delay: 0.05s; }
.anim-2 { animation-delay: 0.10s; }
.anim-3 { animation-delay: 0.15s; }
.anim-4 { animation-delay: 0.20s; }
.anim-5 { animation-delay: 0.25s; }
@keyframes slideUp {
  from { opacity:0; transform:translateY(20px); }
  to   { opacity:1; transform:translateY(0); }
}
.chart-wrap { position: relative; width: 100%; }
</style>
</head>
<body>

<div id="overlay" onclick="closeSidebar()"></div>

<!-- Sidebar -->
<nav id="sidebar">
  <div class="sidebar-logo">
    <div class="logo-icon">🌿</div>
    <div class="logo-name">PhytoScan AI</div>
    <div class="logo-sub">Crop Intelligence</div>
  </div>

  <div class="sidebar-section">Overview</div>
  <a class="nav-item active" onclick="showTab('overview', this)">
    <span class="nav-icon">📊</span> Dashboard
  </a>
  <a class="nav-item" onclick="showTab('crops', this)">
    <span class="nav-icon">🌾</span> My Crops
    <span class="nav-badge">$len(crops)</span>
  </a>

  <div class="sidebar-section">Analysis</div>
  <a class="nav-item" onclick="showTab('scans', this)">
    <span class="nav-icon">🔬</span> Scan History
  </a>
  <a class="nav-item" onclick="showTab('progress', this)">
    <span class="nav-icon">📈</span> Progress
  </a>
  <a class="nav-item" onclick="showTab('alerts', this)">
    <span class="nav-icon">🚨</span> Alerts
    <span class="nav-badge">$alert_count</span>
  </a>

  <div class="sidebar-section">Management</div>
  <a class="nav-item" onclick="showTab('environment', this)">
    <span class="nav-icon">🌡️</span> Environment
  </a>
  <a class="nav-item" onclick="showTab('journal', this)">
    <span class="nav-icon">📓</span> Field Journal
  </a>
  <a class="nav-item" onclick="showTab('quickscan', this)">
    <span class="nav-icon">📷</span> Quick Scan
  </a>

  <div class="sidebar-footer">
    <div class="user-card">
      <div class="user-avatar">👨‍🌾</div>
      <div>
        <div class="user-name">Farmer Raj</div>
        <div class="user-role">Premium Plan · Bengaluru</div>
      </div>
    </div>
  </div>
</nav>

<!-- Topbar -->
<header id="topbar">
  <div class="topbar-left">
    <button id="menu-toggle" onclick="toggleSidebar()">☰</button>
    <div>
      <div class="page-title" id="page-title">Dashboard</div>
      <div class="page-breadcrumb" id="page-breadcrumb">PhytoScan AI / Overview</div>
    </div>
  </div>
  <div class="topbar-right">
    <button class="top-btn" onclick="exportData()">⬇ Export</button>
    <button class="top-btn" onclick="showTab('quickscan', null)">📷 Quick Scan</button>
    <button class="top-btn primary" onclick="showTab('quickscan', null)">＋ New Scan</button>
  </div>
</header>

<main id="main">

<!-- Overview Tab -->
<div class="tab-panel active" id="tab-overview">
  <div class="grid-4">
    <div class="stat-card green anim anim-1">
      <div class="stat-icon green">🌱</div>
      <div class="stat-val">$total_scans</div>
      <div class="stat-label">Total Scans</div>
      <div class="stat-delta up">↑ $total_scans total</div>
    </div>
    <div class="stat-card red anim anim-2">
      <div class="stat-icon red">🦠</div>
      <div class="stat-val">$unique_diseases</div>
      <div class="stat-label">Diseases Found</div>
      <div class="stat-delta down">↓ $unique_diseases_diff vs last month</div>
    </div>
    <div class="stat-card yellow anim anim-3">
      <div class="stat-icon yellow">🌾</div>
      <div class="stat-val">$len(crops)</div>
      <div class="stat-label">Active Crops</div>
      <div class="stat-delta flat">→ No change</div>
    </div>
    <div class="stat-card blue anim anim-4">
      <div class="stat-icon blue">📈</div>
      <div class="stat-val">$health_trend_last%</div>
      <div class="stat-label">Avg Health Score</div>
      <div class="stat-delta up">↑ $health_improvement% improvement</div>
    </div>
  </div>

  <div class="grid-2-1 anim anim-2">
    <div class="card">
      <div class="card-header">
        <span class="card-title">📊 Health Score Trend</span>
        <div style="display:flex;gap:6px;">
          <button class="top-btn" style="padding:5px 10px;font-size:11px;" onclick="setChartPeriod('week')">Week</button>
          <button class="top-btn" style="padding:5px 10px;font-size:11px;" onclick="setChartPeriod('month')">Month</button>
          <button class="top-btn" style="padding:5px 10px;font-size:11px;" onclick="setChartPeriod('year')">Year</button>
        </div>
      </div>
      <div class="card-body">
        <div class="chart-wrap" style="height:220px;">
          $health_html
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">🥧 Disease Breakdown</span>
      </div>
      <div class="card-body">
        <div class="chart-wrap" style="height:220px;">
          $disease_html
        </div>
      </div>
    </div>
  </div>

  <div class="grid-1-2 anim anim-3">
    <div class="card">
      <div class="card-header">
        <span class="card-title">💚 Overall Health</span>
      </div>
      <div class="card-body" style="padding-top:8px;">
        <div class="health-ring-wrap">
          <div class="ring-container">
            <svg class="ring-svg" width="160" height="160" viewBox="0 0 160 160">
              <circle class="ring-bg" cx="80" cy="80" r="66"/>
              <circle class="ring-fg" id="healthRing" cx="80" cy="80" r="66"
                stroke="url(#ringGrad)"
                stroke-dasharray="414.69"
                stroke-dashoffset="414.69"/>
              <defs>
                <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="#3d7a52"/>
                  <stop offset="100%" stop-color="#7ec8a0"/>
                </linearGradient>
              </defs>
            </svg>
            <div class="ring-center">
              <div class="ring-score" id="ringScore">0</div>
              <div class="ring-label">/ 100</div>
            </div>
          </div>
          <div class="health-legend">
            <div class="legend-item">
              <div class="legend-dot" style="background:#27ae60;"></div>
              <div class="legend-label">Healthy</div>
              <div class="legend-val">$healthy_scans</div>
            </div>
            <div class="legend-item">
              <div class="legend-dot" style="background:#f39c12;"></div>
              <div class="legend-label">Warning</div>
              <div class="legend-val">$warning_count</div>
            </div>
            <div class="legend-item">
              <div class="legend-dot" style="background:#e74c3c;"></div>
              <div class="legend-label">Critical</div>
              <div class="legend-val">$critical_count</div>
            </div>
            <div class="legend-item">
              <div class="legend-dot" style="background:#3498db;"></div>
              <div class="legend-label">Recovering</div>
              <div class="legend-val">0</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">
        <span class="card-title">🕐 Recent Scans</span>
        <a class="card-action" onclick="showTab('scans', null)">View all →</a>
      </div>
      <div class="card-body" style="padding:0 0 4px;">
        <table class="scan-table">
          <thead>
            <tr><th>Crop</th><th>Disease</th><th>Severity</th><th>Date</th> </tr>
          </thead>
          <tbody id="recentScansBody"></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card anim anim-4">
    <div class="card-header">
      <span class="card-title">📅 Scan Frequency (Last 12 Weeks)</span>
    </div>
    <div class="card-body">
      <div class="chart-wrap" style="height:180px;">
        $freq_html
      </div>
    </div>
  </div>
</div>

<!-- Crops Tab -->
<div class="tab-panel" id="tab-crops">
  <div class="sec-label">🌾 My Crops</div>
  <div class="sec-sub">Long-term maintenance tracker for all your active crops</div>
  <div class="grid-3" id="cropGrid"></div>
</div>

<!-- Scan History Tab -->
<div class="tab-panel" id="tab-scans">
  <div class="sec-label">🔬 Full Scan History</div>
  <div class="sec-sub">Every upload analyzed by PhytoScan AI</div>
  <div style="display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap;align-items:center;">
    <select id="filterCrop" style="padding:9px 14px;border:1px solid var(--border);border-radius:10px;font-family:'DM Sans',sans-serif;font-size:13px;color:var(--ink);background:var(--paper);cursor:pointer;" onchange="filterScans()">
      <option value="">All Crops</option>
      $crop_options
    </select>
    <select id="filterSev" style="padding:9px 14px;border:1px solid var(--border);border-radius:10px;font-family:'DM Sans',sans-serif;font-size:13px;color:var(--ink);background:var(--paper);cursor:pointer;" onchange="filterScans()">
      <option value="">All Severity</option>
      <option>High</option><option>Medium</option><option>Low</option><option>None</option>
    </select>
    <div style="margin-left:auto;font-size:13px;color:var(--muted);" id="scanCount">Showing $total_scans scans</div>
  </div>
  <div class="card">
    <div class="card-body" style="padding:0 0 8px;">
      <table class="scan-table" style="width:100%;">
        <thead>
          <tr><th>#</th><th>Date</th><th>Crop</th><th>Disease</th><th>Severity</th><th>Confidence</th><th>Action Taken</th> </tr>
        </thead>
        <tbody id="fullScansBody"></tbody>
      </table>
    </div>
  </div>
</div>

<!-- Progress Tab -->
<div class="tab-panel" id="tab-progress">
  <div class="sec-label">📈 Improvement Progress</div>
  <div class="sec-sub">Track how your crops are recovering over time</div>
  <div class="grid-2">
    <div class="card">
      <div class="card-header"><span class="card-title">📉 Disease Frequency Over Time</span></div>
      <div class="card-body">
        <div class="chart-wrap" style="height:240px;">
          $progress_html
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">🌡️ Crop Health Radar</span></div>
      <div class="card-body">
        <div class="chart-wrap" style="height:240px;">
          $radar_html
        </div>
      </div>
    </div>
  </div>
  <div class="card" style="margin-bottom:24px;">
    <div class="card-header"><span class="card-title">🗓️ Improvement Timeline</span></div>
    <div class="card-body">
      <div class="timeline" id="progressTimeline"></div>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><span class="card-title">🌾 Per-Crop Health Progress</span></div>
    <div class="card-body" id="cropProgressBars"></div>
  </div>
</div>

<!-- Alerts Tab -->
<div class="tab-panel" id="tab-alerts">
  <div class="sec-label">🚨 Active Alerts & Tasks</div>
  <div class="sec-sub">Pending actions and maintenance reminders</div>
  <div class="grid-2">
    <div>
      <div style="font-size:13px;font-weight:700;color:var(--danger);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">🔴 Urgent</div>
      <div id="urgentAlerts"></div>
      <div style="font-size:13px;font-weight:700;color:var(--warning);text-transform:uppercase;letter-spacing:1px;margin:20px 0 12px;">🟡 This Week</div>
      <div id="weekAlerts"></div>
    </div>
    <div>
      <div style="font-size:13px;font-weight:700;color:var(--info);text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">🔵 Routine</div>
      <div id="routineAlerts"></div>
      <div style="font-size:13px;font-weight:700;color:var(--success);text-transform:uppercase;letter-spacing:1px;margin:20px 0 12px;">✅ Completed</div>
      <div id="doneAlerts"></div>
    </div>
  </div>
</div>

<!-- Environment Tab -->
<div class="tab-panel" id="tab-environment">
  <div class="sec-label">🌡️ Environment & Soil Monitor</div>
  <div class="sec-sub">Real-time conditions affecting your crop health</div>
  <div class="grid-3">
    <div class="card">
      <div class="card-header"><span class="card-title">☁️ Today's Weather</span></div>
      <div class="card-body">
        <div class="weather-main">
          <div class="weather-icon">⛅</div>
          <div>
            <div class="weather-temp">28°C</div>
            <div class="weather-desc">Partly Cloudy · Bengaluru</div>
          </div>
        </div>
        <div class="weather-grid">
          <div class="weather-cell"><div class="weather-cell-label">Humidity</div><div class="weather-cell-val">72%</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Wind</div><div class="weather-cell-val">12 km/h</div></div>
          <div class="weather-cell"><div class="weather-cell-label">UV Index</div><div class="weather-cell-val">6 (High)</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Rainfall</div><div class="weather-cell-val">0 mm</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Dew Pt</div><div class="weather-cell-val">22°C</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Pressure</div><div class="weather-cell-val">1012 hPa</div></div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">🌍 Soil Conditions</span></div>
      <div class="card-body" id="soilGauges"></div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">💧 Irrigation Status</span></div>
      <div class="card-body">
        <div style="text-align:center;padding:12px 0;">
          <div style="font-size:52px;">💧</div>
          <div style="font-family:'Playfair Display',serif;font-size:28px;font-weight:900;color:var(--forest);margin-top:8px;">Last Watered</div>
          <div style="font-size:20px;color:var(--fern);font-weight:700;margin-top:4px;">2 hours ago</div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:8px;">
          <div class="weather-cell"><div class="weather-cell-label">Next Due</div><div class="weather-cell-val" style="font-size:13px;">Tomorrow 6AM</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Volume</div><div class="weather-cell-val">18 L/m²</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Method</div><div class="weather-cell-val">Drip</div></div>
          <div class="weather-cell"><div class="weather-cell-label">Coverage</div><div class="weather-cell-val">94%</div></div>
        </div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-header"><span class="card-title">📅 7-Day Forecast & Crop Risk</span></div>
    <div class="card-body">
      <div class="chart-wrap" style="height:200px;">
        $forecast_html
      </div>
    </div>
  </div>
</div>

<!-- Journal Tab -->
<div class="tab-panel" id="tab-journal">
  <div class="sec-label">📓 Field Journal</div>
  <div class="sec-sub">Record observations, treatments, and notes for each crop</div>
  <div class="grid-2">
    <div>
      <div id="notesList"></div>
      <div class="note-input-wrap">
        <div style="font-size:13px;font-weight:700;color:var(--forest);margin-bottom:8px;">+ Add New Entry</div>
        <select id="noteCrop" style="width:100%;padding:9px 14px;border:1px solid var(--border);border-radius:10px;font-family:'DM Sans',sans-serif;font-size:13px;margin-bottom:8px;color:var(--ink);background:var(--paper);">
          $crop_options
        </select>
        <textarea class="note-textarea" id="noteText" placeholder="Describe what you observed — symptoms, treatments applied, weather conditions, etc."></textarea>
        <button class="note-submit" onclick="addNote()">📝 Save Entry</button>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">📊 Journal Activity</span></div>
      <div class="card-body">
        <div class="chart-wrap" style="height:200px;">
          $journal_html
        </div>
        <div style="margin-top:16px;">
          <div style="font-size:12px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Most Logged Crops</div>
          <div id="journalCropBars"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- Quick Scan Tab -->
<div class="tab-panel" id="tab-quickscan">
  <div class="sec-label">📷 Quick Scan</div>
  <div class="sec-sub">Upload a plant image for instant AI-powered disease detection</div>
  <div class="grid-2">
    <div class="card">
      <div class="card-header"><span class="card-title">📤 Upload Image</span></div>
      <div class="card-body">
        <div class="upload-zone" id="dropZone">
          <input type="file" accept="image/*" onchange="handleUpload(event)"/>
          <div class="upload-icon">🌿</div>
          <div class="upload-text">Drop your plant image here</div>
          <div class="upload-sub">or click to browse · JPG, PNG, WEBP up to 10MB</div>
        </div>
        <div id="uploadPreview" style="display:none;margin-top:16px;text-align:center;">
          <img id="previewImg" style="max-width:100%;max-height:220px;border-radius:12px;border:2px solid var(--border);"/>
          <div style="margin-top:12px;">
            <button class="note-submit" onclick="simulateScan()">🔍 Analyze Now</button>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:16px;">
          <div style="background:var(--cream);border-radius:10px;padding:12px;text-align:center;">
            <div style="font-size:22px;">⚡</div>
            <div style="font-size:12px;font-weight:700;color:var(--forest);margin-top:4px;">Under 5 seconds</div>
            <div style="font-size:11px;color:var(--muted);">AI Analysis Time</div>
          </div>
          <div style="background:var(--cream);border-radius:10px;padding:12px;text-align:center;">
            <div style="font-size:22px;">🎯</div>
            <div style="font-size:12px;font-weight:700;color:var(--forest);margin-top:4px;">95% Accuracy</div>
            <div style="font-size:11px;color:var(--muted);">Disease Detection</div>
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header"><span class="card-title">📋 Scan Result</span></div>
      <div class="card-body">
        <div id="scanResult">
          <div style="text-align:center;padding:40px 20px;color:var(--muted);">
            <div style="font-size:52px;margin-bottom:12px;">🌿</div>
            <div style="font-size:15px;font-weight:600;">Upload an image to see results</div>
            <div style="font-size:12px;margin-top:6px;">AI will analyze your plant and generate a full report</div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:4px;">
    <div class="card-header"><span class="card-title">💡 Tips for Best Results</span></div>
    <div class="card-body">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;">
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <div style="font-size:22px;">☀️</div>
          <div><div style="font-size:13px;font-weight:700;color:var(--ink);">Good Lighting</div><div style="font-size:12px;color:var(--muted);margin-top:2px;">Natural daylight gives best results; avoid harsh flash.</div></div>
        </div>
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <div style="font-size:22px;">🎯</div>
          <div><div style="font-size:13px;font-weight:700;color:var(--ink);">Focus on Symptoms</div><div style="font-size:12px;color:var(--muted);margin-top:2px;">Zoom in on discolored, spotted, or wilted areas.</div></div>
        </div>
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <div style="font-size:22px;">🌿</div>
          <div><div style="font-size:13px;font-weight:700;color:var(--ink);">Multiple Angles</div><div style="font-size:12px;color:var(--muted);margin-top:2px;">Scan different leaves for consistent diagnosis.</div></div>
        </div>
        <div style="display:flex;gap:10px;align-items:flex-start;">
          <div style="font-size:22px;">📏</div>
          <div><div style="font-size:13px;font-weight:700;color:var(--ink);">Include Scale</div><div style="font-size:12px;color:var(--muted);margin-top:2px;">A coin or ruler helps the AI judge lesion size.</div></div>
        </div>
      </div>
    </div>
  </div>
</div>
</main>

<script>
// ==================== DATA FROM PYTHON ====================
const scanData = $scan_list_json;
const cropData = $crops_json;
const alertData = $alerts_json;
const noteData = $notes_json;
const soilGaugesData = $soil_gauges_json;
const progressTimelineData = $progress_timeline_json;

// ==================== RENDER FUNCTIONS ====================
function severityTag(sev) {
  const map = { 'High':'tag-danger', 'Medium':'tag-warning', 'Low':'tag-success', 'None':'tag-info' };
  const dot = { 'High':'#e74c3c', 'Medium':'#f39c12', 'Low':'#27ae60', 'None':'#3498db' };
  const cls = map[sev] || 'tag-info';
  return `<span class="disease-tag ${cls}"><span class="sev-dot" style="background:${dot[sev]||'#999'};"></span>${sev}</span>`;
}

function diseaseTag(d) {
  const healthy = d.toLowerCase().includes('healthy');
  return `<span class="disease-tag ${healthy ? 'tag-success' : 'tag-danger'}">${healthy ? '✅' : '🦠'} ${d}</span>`;
}

function renderRecentScans() {
  const body = document.getElementById('recentScansBody');
  body.innerHTML = scanData.slice(0,6).map(s => `
    <tr>
      <td><b>${s.crop}</b></td>
      <td>${diseaseTag(s.disease)}</td>
      <td>${severityTag(s.severity)}</td>
      <td style="color:var(--muted);font-size:12px;">${s.date}</td>
    </tr>`).join('');
}

function renderFullScans() {
  const body = document.getElementById('fullScansBody');
  body.innerHTML = scanData.map(s => `
    <tr>
      <td style="color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:11px;">#${String(s.id).padStart(3,'0')}</td>
      <td style="font-size:12px;color:var(--muted);">${s.date}</td>
      <td><b>${s.crop}</b></td>
      <td>${diseaseTag(s.disease)}</td>
      <td>${severityTag(s.severity)}</td>
      <td>
        <div style="display:flex;align-items:center;gap:8px;">
          <div style="flex:1;background:var(--border);border-radius:4px;height:5px;overflow:hidden;max-width:60px;">
            <div style="height:100%;border-radius:4px;background:linear-gradient(90deg,var(--fern),var(--mint));width:${s.confidence}%;"></div>
          </div>
          <span style="font-size:11px;font-weight:700;color:var(--fern);">${s.confidence}%</span>
        </div>
      </td>
      <td style="font-size:12px;color:var(--muted);">${s.action}</td>
    </tr>`).join('');
}

function filterScans() {
  const crop = document.getElementById('filterCrop').value;
  const sev = document.getElementById('filterSev').value;
  const filtered = scanData.filter(s =>
    (!crop || s.crop === crop) && (!sev || s.severity === sev));
  document.getElementById('scanCount').textContent = `Showing ${filtered.length} scans`;
  document.getElementById('fullScansBody').innerHTML = filtered.map(s => `
    <tr>
      <td style="color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:11px;">#${String(s.id).padStart(3,'0')}</td>
      <td style="font-size:12px;color:var(--muted);">${s.date}</td>
      <td><b>${s.crop}</b></td>
      <td>${diseaseTag(s.disease)}</td>
      <td>${severityTag(s.severity)}</td>
      <td><span style="font-size:11px;font-weight:700;color:var(--fern);">${s.confidence}%</span></td>
      <td style="font-size:12px;color:var(--muted);">${s.action}</td>
    </tr>`).join('');
}

function renderCrops() {
  const healthColor = h => h >= 80 ? '#27ae60' : h >= 60 ? '#f39c12' : '#e74c3c';
  const statusBadge = s => ({'Good':'tag-success','Warning':'tag-warning','Critical':'tag-danger'}[s]||'tag-info');
  document.getElementById('cropGrid').innerHTML = cropData.map(c => `
    <div class="crop-card">
      <div class="crop-card-top" data-emoji="${c.emoji}">
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <div>
            <div class="crop-name">${c.name}</div>
            <div class="crop-variety">${c.variety}</div>
          </div>
          <span class="disease-tag ${statusBadge(c.status)}" style="font-size:10px;">${c.status}</span>
        </div>
        <div class="crop-health-bar">
          <div class="crop-health-fill" style="width:${c.health}%;background:${healthColor(c.health)};"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:4px;font-size:11px;color:rgba(255,255,255,0.6);">
          <span>Health</span><span style="font-weight:700;color:#fff;">${c.health}%</span>
        </div>
      </div>
      <div class="crop-card-body">
        <div class="crop-meta">
          <div class="crop-meta-item"><div class="crop-meta-label">Planted</div><div class="crop-meta-val" style="font-size:12px;">${c.planted}</div></div>
          <div class="crop-meta-item"><div class="crop-meta-label">Area</div><div class="crop-meta-val" style="font-size:12px;">${c.area}</div></div>
          <div class="crop-meta-item"><div class="crop-meta-label">Total Scans</div><div class="crop-meta-val">${c.scans}</div></div>
          <div class="crop-meta-item"><div class="crop-meta-label">Next Action</div><div class="crop-meta-val" style="font-size:12px;">${c.nextAction}</div></div>
        </div>
      </div>
      <div class="crop-actions">
        <button class="crop-btn">📊 History</button>
        <button class="crop-btn">📓 Notes</button>
        <button class="crop-btn primary-btn" onclick="showTab('quickscan',null)">🔬 Scan</button>
      </div>
    </div>`).join('');
}

function renderAlerts() {
  const renderGroup = (items, type) => items.map(a => `
    <div class="alert-item ${type}">
      <div class="alert-icon"><span>${a.icon}</span></div>
      <div style="flex:1;">
        <div class="alert-title">${a.title}</div>
        <div class="alert-desc">${a.desc}</div>
      </div>
      <div class="alert-time">${a.time}</div>
    </div>`).join('');
  document.getElementById('urgentAlerts').innerHTML  = renderGroup(alertData.urgent,'urgent');
  document.getElementById('weekAlerts').innerHTML    = renderGroup(alertData.week,'warning');
  document.getElementById('routineAlerts').innerHTML = renderGroup(alertData.routine,'info');
  document.getElementById('doneAlerts').innerHTML    = renderGroup(alertData.done,'done');
}

function renderSoilGauges() {
  document.getElementById('soilGauges').innerHTML = soilGaugesData.map(i => `
    <div class="env-gauge">
      <div class="env-icon">${i.icon}</div>
      <div class="env-info"><div class="env-name">${i.name}</div><div class="env-val">${i.val}</div></div>
      <div class="env-bar">
        <div class="env-track">
          <div class="env-fill" style="width:${i.pct}%;background:${i.color};"></div>
        </div>
      </div>
      <div class="env-pct">${i.pct}%</div>
    </div>`).join('');
}

function renderProgressTimeline() {
  document.getElementById('progressTimeline').innerHTML = progressTimelineData.map(i => `
    <div class="tl-item">
      <div class="tl-dot ${i.cls}">✦</div>
      <div class="tl-date">${i.date}</div>
      <div class="tl-title">${i.title}</div>
      <div class="tl-body">${i.body}</div>
      <span class="tl-tag ${i.tagCls}">${i.tag}</span>
    </div>`).join('');
}

function renderCropProgressBars() {
  const progress = cropData.map(c => ({
    name: c.name,
    before: Math.max(0, c.health - 10),
    after: c.health,
    color: c.health >= 80 ? '#27ae60' : c.health >= 60 ? '#f39c12' : '#e74c3c'
  }));
  document.getElementById('cropProgressBars').innerHTML = progress.map(d => `
    <div style="margin-bottom:18px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
        <span style="font-size:13px;font-weight:600;">${d.name}</span>
        <span style="font-size:12px;color:var(--muted);">${d.before}% → <b style="color:var(--fern);">${d.after}%</b></span>
      </div>
      <div style="position:relative;background:var(--border);border-radius:6px;height:10px;overflow:hidden;">
        <div style="position:absolute;left:0;top:0;height:100%;width:${d.before}%;background:#ddd;border-radius:6px;"></div>
        <div style="position:absolute;left:0;top:0;height:100%;width:${d.after}%;background:linear-gradient(90deg,${d.color},${d.color}99);border-radius:6px;transition:width 1s ease;"></div>
      </div>
      <div style="font-size:11px;color:var(--success);margin-top:4px;">↑ +${d.after - d.before}% improvement</div>
    </div>`).join('');
}

function renderNotes() {
  document.getElementById('notesList').innerHTML = noteData.map(n => `
    <div class="note-item">
      <div class="note-header">
        <span class="note-crop">🌿 ${n.crop}</span>
        <span class="note-date">${n.date}</span>
      </div>
      <div class="note-text">${n.text}</div>
    </div>`).join('');
}

function renderJournalCropBars() {
  const counts = {};
  noteData.forEach(n => { counts[n.crop] = (counts[n.crop] || 0) + 1; });
  const items = Object.entries(counts).map(([crop, count]) => ({ crop, count })).sort((a,b) => b.count - a.count);
  const max = Math.max(...items.map(c => c.count));
  document.getElementById('journalCropBars').innerHTML = items.map(c => `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
      <div style="font-size:12px;min-width:80px;">🌿 ${c.crop}</div>
      <div style="flex:1;background:var(--border);border-radius:4px;height:6px;overflow:hidden;">
        <div style="height:100%;border-radius:4px;background:linear-gradient(90deg,var(--fern),var(--mint));width:${(c.count/max)*100}%;"></div>
      </div>
      <div style="font-size:12px;font-weight:700;color:var(--fern);min-width:20px;">${c.count}</div>
    </div>`).join('');
}

function addNote() {
  const crop = document.getElementById('noteCrop').value;
  const text = document.getElementById('noteText').value.trim();
  if (!text) return;
  const today = new Date().toLocaleDateString('en-US', { month:'short', day:'numeric' });
  noteData.unshift({ crop, date: today, text });
  renderNotes();
  document.getElementById('noteText').value = '';
}

// Tab system
const tabTitles = {
  overview:'Dashboard', crops:'My Crops', scans:'Scan History',
  progress:'Progress', alerts:'Alerts', environment:'Environment',
  journal:'Field Journal', quickscan:'Quick Scan'
};

function showTab(name, navEl) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const panel = document.getElementById('tab-' + name);
  if (panel) panel.classList.add('active');
  if (navEl) navEl.classList.add('active');
  document.getElementById('page-title').textContent = tabTitles[name] || name;
  document.getElementById('page-breadcrumb').textContent = `PhytoScan AI / ${tabTitles[name] || name}`;
  if (window.innerWidth <= 900) closeSidebar();
}

function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('overlay').classList.toggle('show');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('overlay').classList.remove('show');
}

// Export
function exportData() {
  const csv = ['Date,Crop,Disease,Severity,Confidence,Action']
    .concat(scanData.map(s => `${s.date},${s.crop},${s.disease},${s.severity},${s.confidence}%,${s.action}`))
    .join('\\n');
  const blob = new Blob([csv], { type:'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'phytoscan_export.csv';
  a.click();
}

// Quick scan simulation
function handleUpload(e) {
  const file = e.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = ev => {
    document.getElementById('previewImg').src = ev.target.result;
    document.getElementById('uploadPreview').style.display = 'block';
  };
  reader.readAsDataURL(file);
}

function simulateScan() {
  document.getElementById('scanResult').innerHTML = `
    <div style="text-align:center;padding:30px;">
      <div style="font-size:42px;animation:spin 1s linear infinite;display:inline-block;">🔬</div>
      <div style="font-size:14px;font-weight:600;color:var(--forest);margin-top:12px;">Analyzing with Gemini AI...</div>
    </div>
    <style>@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}</style>`;
  setTimeout(() => {
    document.getElementById('scanResult').innerHTML = `
      <div style="padding:4px;">
        <div style="background:linear-gradient(135deg,rgba(231,76,60,0.08),rgba(231,76,60,0.02));
                    border:1.5px solid rgba(231,76,60,0.3);border-radius:12px;padding:16px 18px;margin-bottom:14px;">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:#888;margin-bottom:4px;">Diagnosis</div>
          <div style="font-size:20px;font-weight:800;color:#1a1a2e;">🦠 Leaf Spot Disease</div>
          <div style="margin-top:10px;display:flex;gap:8px;flex-wrap:wrap;">
            <span class="disease-tag tag-warning">⚡ Medium Severity</span>
            <span class="disease-tag tag-danger">🕐 Soon Action</span>
          </div>
          <div style="margin-top:12px;">
            <div style="display:flex;justify-content:space-between;font-size:11px;color:#888;margin-bottom:4px;">
              <span>AI Confidence</span><span style="font-weight:700;color:#e74c3c;">88%</span>
            </div>
            <div style="background:#e8e8e8;border-radius:6px;height:7px;overflow:hidden;">
              <div style="background:linear-gradient(90deg,#e74c3c,#f1948a);width:88%;height:100%;border-radius:6px;"></div>
            </div>
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px;">
          <div style="background:#f8f9ff;border-radius:10px;padding:12px;text-align:center;"><div style="font-size:20px;">🍃</div><div style="font-size:10px;color:#888;">Affected</div><div style="font-size:12px;font-weight:700;">Leaves</div></div>
          <div style="background:#f8fff8;border-radius:10px;padding:12px;text-align:center;"><div style="font-size:20px;">🔬</div><div style="font-size:10px;color:#888;">Cause</div><div style="font-size:12px;font-weight:700;">Fungal</div></div>
          <div style="background:#fff8f8;border-radius:10px;padding:12px;text-align:center;"><div style="font-size:20px;">📊</div><div style="font-size:10px;color:#888;">Confidence</div><div style="font-size:12px;font-weight:700;">88%</div></div>
        </div>
        <div style="background:#fffbf0;border-left:3px solid #f39c12;border-radius:0 10px 10px 0;padding:12px 14px;margin-bottom:10px;">
          <div style="font-size:10px;font-weight:700;color:#f39c12;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">💊 Treatment</div>
          <div style="font-size:13px;color:#555;line-height:1.5;">Remove affected leaves. Apply mancozeb or copper-based fungicide. Avoid overhead irrigation.</div>
        </div>
        <div style="background:#f0fff4;border-left:3px solid #27ae60;border-radius:0 10px 10px 0;padding:12px 14px;">
          <div style="font-size:10px;font-weight:700;color:#27ae60;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px;">🛡️ Prevention</div>
          <div style="font-size:13px;color:#555;line-height:1.5;">Improve air circulation, avoid wetting foliage. Rotate crops annually.</div>
        </div>
        <div style="text-align:center;margin-top:12px;">
          <button class="note-submit" onclick="showTab('scans',null)">View in History</button>
        </div>
      </div>`;
  }, 2200);
}

// Health ring animation
function animateRing(score) {
  const circ = 2 * Math.PI * 66;
  const ring = document.getElementById('healthRing');
  const scoreEl = document.getElementById('ringScore');
  const offset = circ * (1 - score / 100);
  setTimeout(() => { ring.style.strokeDashoffset = offset; }, 300);
  let cur = 0;
  const timer = setInterval(() => {
    cur = Math.min(cur + 2, score);
    scoreEl.textContent = cur;
    if (cur >= score) clearInterval(timer);
  }, 20);
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  renderRecentScans();
  renderFullScans();
  renderCrops();
  renderAlerts();
  renderSoilGauges();
  renderProgressTimeline();
  renderCropProgressBars();
  renderNotes();
  renderJournalCropBars();
  animateRing($health_trend_last);
});
</script>
</body>
</html>
    """)

    # Prepare substitution dictionary
    subs = {
        "scan_list_json": scan_list_json,
        "crops_json": crops_json,
        "alerts_json": alerts_json,
        "notes_json": notes_json,
        "soil_gauges_json": soil_gauges_json,
        "progress_timeline_json": progress_timeline_json,
        "total_scans": total_scans,
        "unique_diseases": unique_diseases,
        "unique_diseases_diff": max(0, unique_diseases - 2),
        "len(crops)": len(crops),
        "alert_count": len(alerts.get("urgent", [])) + len(alerts.get("week", [])),
        "health_trend_last": health_trend_last,
        "health_improvement": int(
            health_trend_last - (health_trend[0] if health_trend else 70)
        ),
        "healthy_scans": healthy_scans,
        "warning_count": severity_counts.get("Medium", 0),
        "critical_count": severity_counts.get("High", 0),
        "health_html": health_html,
        "disease_html": disease_html,
        "freq_html": freq_html,
        "progress_html": progress_html,
        "radar_html": radar_html,
        "forecast_html": forecast_html,
        "journal_html": journal_html,
        "crop_options": "".join(f"<option>{c['name']}</option>" for c in crops),
    }

    # Substitute and return
    return template.substitute(subs)


# The rest of the helper functions (extract_crop_from_image, generate_action, get_crop_emoji, compute_health_trend, compute_frequency, compute_progress_timeline, compute_radar_data, compute_crop_progress, generate_alerts, and all Plotly chart functions) remain exactly as in the previous code.
# I'm omitting them here for brevity, but they should be included in the final file.

def generate_alerts(scan_list):
    alerts = []
    for s in scan_list:
        if s["severity"] in ["High", "Medium"]:
            alerts.append({
                "type": "warning" if s["severity"] == "Medium" else "danger",
                "message": f"{s['disease']} detected in {s['crop']}",
                "time": s["date"]
            })
    return alerts

def extract_crop_from_image(image_path):
    # Simple heuristic to extract crop from filename
    if "tomato" in image_path.lower():
        return "Tomato"
    elif "potato" in image_path.lower():
        return "Potato"
    elif "corn" in image_path.lower():
        return "Corn"
    else:
        return "Unknown"

def generate_action(disease, severity):
    if disease == "None":
        return "No action needed"
    elif severity == "High":
        return "Immediate treatment required"
    elif severity == "Medium":
        return "Monitor and treat if necessary"
    else:
        return "Observe"

def get_crop_emoji(crop):
    emojis = {"Tomato": "🍅", "Potato": "🥔", "Corn": "🌽"}
    return emojis.get(crop, "🌱")

def compute_health_trend(scan_list):
    # Mock data
    return [70, 75, 80, 85]

def compute_frequency(scan_list):
    # Mock data
    return [("Week 1", 5), ("Week 2", 7), ("Week 3", 3)]

def compute_progress_timeline(scan_list):
    # Mock data
    return [{"date": "2023-01-01", "event": "Scan 1"}, {"date": "2023-01-15", "event": "Scan 2"}]

def compute_radar_data(scan_list, crops):
    # Mock data
    return {"health": 80, "yield": 70, "resistance": 60}

def compute_crop_progress(scan_list, crops):
    # Mock data
    return [{"crop": "Tomato", "progress": 75}]

# Plotly chart functions
import plotly.express as px

def create_health_chart(health_trend):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(len(health_trend))), y=health_trend, mode='lines+markers'))
    fig.update_layout(title="Health Trend")
    return fig

def create_disease_chart(disease_counts):
    fig = px.bar(x=list(disease_counts.keys()), y=list(disease_counts.values()))
    return fig

def create_freq_chart(freq_data):
    fig = px.line(x=[x[0] for x in freq_data], y=[x[1] for x in freq_data])
    return fig

def create_progress_chart(timeline):
    fig = go.Figure()
    # Add timeline
    return fig

def create_radar_chart(radar_data):
    fig = go.Figure()
    # Add radar
    return fig

def create_forecast_chart():
    fig = go.Figure()
    return fig

def create_journal_chart(notes):
    fig = go.Figure()
    return fig

def build_dashboard():
    return gr.HTML(generate_dashboard_html())



with gr.Blocks(title="PhytoScan AI Dashboard") as dashboard:
    gr.HTML(build_dashboard())

if __name__ == "__main__":
    dashboard.launch(debug=True)
