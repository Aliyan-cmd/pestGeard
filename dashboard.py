"""
dashboard.py — PhytoScan AI · Full Analytics Dashboard
Complete standalone dashboard with nav bar, footer, and rich visualizations
Matches the UI style of app.py
"""

import os
import pickle
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import numpy as np

import gradio as gr
import plotly.graph_objects as go
import plotly.express as px

# ─── Configuration ───────────────────────────────────────────────────────────
HISTORY_FILE = "scan_history.pkl"

# ─── Helper Functions ─────────────────────────────────────────────────────────
def load_scans():
    """Load scan history from pickle file"""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "rb") as f:
                data = pickle.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def extract_crop_from_image(path: str) -> str:
    """Extract crop name from image filename"""
    if not path:
        return "Plant"
    name = os.path.basename(path).lower()
    crops = ["tomato", "potato", "corn", "wheat", "rice", "pepper",
             "mango", "grape", "apple", "banana", "brinjal", "onion"]
    for crop in crops:
        if crop in name:
            return crop.capitalize()
    return "Plant"

def get_crop_emoji(crop: str) -> str:
    """Get emoji for crop type"""
    emoji_map = {
        "Tomato": "🍅", "Potato": "🥔", "Corn": "🌽", "Wheat": "🌾",
        "Rice": "🍚", "Pepper": "🫑", "Mango": "🥭", "Grape": "🍇",
        "Apple": "🍎", "Banana": "🍌", "Brinjal": "🍆", "Onion": "🧅"
    }
    return emoji_map.get(crop, "🌱")

def get_severity_color(severity: str) -> str:
    """Get color for severity level"""
    colors = {
        "High": "#e74c3c",
        "Medium": "#f39c12", 
        "Low": "#27ae60",
        "None": "#3498db"
    }
    return colors.get(severity, "#95a5a6")

def get_severity_icon(severity: str) -> str:
    """Get icon for severity level"""
    icons = {
        "High": "🔴",
        "Medium": "🟡",
        "Low": "🟢",
        "None": "⚪"
    }
    return icons.get(severity, "❓")

def parse_date(date_str):
    """Parse date string to datetime object"""
    try:
        return datetime.strptime(date_str, "%b %d, %Y %H:%M")
    except:
        return datetime.now()

def process_scan_data(scans):
    """Process raw scan data into structured format"""
    processed = []
    for idx, scan in enumerate(scans):
        crop = scan.get("crop") or extract_crop_from_image(scan.get("image", ""))
        disease = scan.get("disease", "Unknown")
        severity = scan.get("severity", "Unknown")
        
        confidence = scan.get("confidence", 85)
        
        processed.append({
            "id": idx + 1,
            "date": scan.get("date", "Unknown"),
            "datetime": parse_date(scan.get("date", "")),
            "crop": crop,
            "disease": disease,
            "severity": severity,
            "confidence": confidence,
            "cause": scan.get("cause", "Unknown"),
            "is_healthy": "healthy" in disease.lower(),
            "image_path": scan.get("image", ""),
        })
    return processed

def get_stats(processed_scans):
    """Calculate statistics from processed scans"""
    total = len(processed_scans)
    healthy = sum(1 for s in processed_scans if s["is_healthy"])
    diseased = total - healthy
    
    severity_counts = Counter(s["severity"] for s in processed_scans)
    disease_counts = Counter(s["disease"] for s in processed_scans if not s["is_healthy"])
    crop_counts = Counter(s["crop"] for s in processed_scans)
    
    # Calculate average health score
    health_scores = []
    for s in processed_scans:
        if s["is_healthy"]:
            health_scores.append(95)
        else:
            score_map = {"High": 40, "Medium": 65, "Low": 80, "None": 95}
            health_scores.append(score_map.get(s["severity"], 70))
    
    avg_health = int(np.mean(health_scores)) if health_scores else 85
    
    return {
        "total_scans": total,
        "healthy_scans": healthy,
        "diseased_scans": diseased,
        "unique_diseases": len(disease_counts),
        "unique_crops": len(crop_counts),
        "severity_counts": severity_counts,
        "disease_counts": disease_counts,
        "crop_counts": crop_counts,
        "avg_health": avg_health,
        "critical_count": severity_counts.get("High", 0),
        "warning_count": severity_counts.get("Medium", 0),
    }

# ─── Chart Creation Functions ─────────────────────────────────────────────────
def create_health_trend_chart(processed_scans):
    """Create health trend over time chart"""
    if not processed_scans:
        dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(7, -1, -1)]
        values = [70, 72, 75, 78, 80, 82, 85, 87]
    else:
        sorted_scans = sorted(processed_scans, key=lambda x: x["datetime"])
        recent_scans = sorted_scans[-12:]
        
        dates = []
        values = []
        for scan in recent_scans:
            dates.append(scan["date"].split()[0] if " " in scan["date"] else scan["date"])
            if scan["is_healthy"]:
                score = 95
            else:
                score_map = {"High": 40, "Medium": 65, "Low": 80, "None": 95}
                score = score_map.get(scan["severity"], 70)
            values.append(score)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines+markers",
        line=dict(color="#2d6a4f", width=3),
        marker=dict(size=8, color="#40916c", symbol="circle"),
        fill="tozeroy",
        fillcolor="rgba(45,106,79,0.1)",
        hovertemplate="Date: %{x}<br>Health Score: %{y}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text="Health Score Trend", font=dict(size=14, color="#1b4332", family="Space Grotesk")),
        xaxis_title="Scan Date",
        yaxis_title="Health Score (%)",
        yaxis_range=[0, 100],
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40),
        font=dict(family="Nunito")
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="#e9ecef")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e9ecef")
    
    return fig

def create_disease_pie_chart(disease_counts):
    """Create pie chart for disease distribution"""
    if not disease_counts:
        disease_counts = {"No Data": 1}
    
    sorted_diseases = sorted(disease_counts.items(), key=lambda x: x[1], reverse=True)[:6]
    labels = [d[0] for d in sorted_diseases]
    values = [d[1] for d in sorted_diseases]
    
    colors = ["#e74c3c", "#f39c12", "#27ae60", "#3498db", "#9b59b6", "#1abc9c"]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors[:len(labels)], line=dict(color="white", width=2)),
        textinfo="label+percent",
        textfont=dict(size=11),
        hoverinfo="label+value+percent",
    )])
    
    fig.update_layout(
        title=dict(text="Disease Distribution", font=dict(size=14, color="#1b4332", family="Space Grotesk")),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=10)),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=20, r=100, t=50, b=20)
    )
    
    return fig

def create_severity_bar_chart(severity_counts):
    """Create bar chart for severity distribution"""
    if not severity_counts:
        severity_counts = {"None": 0, "Low": 0, "Medium": 0, "High": 0}
    
    severity_order = ["None", "Low", "Medium", "High"]
    colors = ["#3498db", "#27ae60", "#f39c12", "#e74c3c"]
    
    x = [s for s in severity_order]
    y = [severity_counts.get(s, 0) for s in severity_order]
    
    fig = go.Figure(data=[go.Bar(
        x=x,
        y=y,
        marker=dict(color=colors, line=dict(color="white", width=2)),
        text=y,
        textposition="auto",
        hovertemplate="Severity: %{x}<br>Count: %{y}<extra></extra>"
    )])
    
    fig.update_layout(
        title=dict(text="Severity Distribution", font=dict(size=14, color="#1b4332", family="Space Grotesk")),
        xaxis_title="Severity Level",
        yaxis_title="Number of Cases",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e9ecef")
    
    return fig

def create_activity_timeline(processed_scans):
    """Create timeline of scan activity"""
    if not processed_scans:
        dates = [(datetime.now() - timedelta(days=i)).strftime("%b %d") for i in range(6, -1, -1)]
        counts = [0, 0, 0, 0, 0, 0, 0]
    else:
        # Group by date
        date_groups = defaultdict(int)
        for scan in processed_scans:
            date_key = scan["date"].split()[0] if " " in scan["date"] else scan["date"]
            date_groups[date_key] += 1
        
        # Get last 7 days
        dates = []
        counts = []
        for i in range(6, -1, -1):
            date = (datetime.now() - timedelta(days=i)).strftime("%b %d")
            dates.append(date)
            counts.append(date_groups.get(date, 0))
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates,
        y=counts,
        marker=dict(color="#2d6a4f", line=dict(color="white", width=1)),
        text=counts,
        textposition="auto",
        hovertemplate="Date: %{x}<br>Scans: %{y}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(text="Scan Activity (Last 7 Days)", font=dict(size=14, color="#1b4332", family="Space Grotesk")),
        xaxis_title="Date",
        yaxis_title="Number of Scans",
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=280,
        margin=dict(l=40, r=40, t=50, b=40)
    )
    
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="#e9ecef")
    
    return fig

def create_crop_health_gauge(avg_health):
    """Create gauge chart for overall crop health"""
    # Determine color based on health
    if avg_health >= 80:
        color = "#27ae60"
        status = "Excellent"
    elif avg_health >= 60:
        color = "#f39c12"
        status = "Good"
    elif avg_health >= 40:
        color = "#e67e22"
        status = "Fair"
    else:
        color = "#e74c3c"
        status = "Poor"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_health,
        title=dict(text="Overall Crop Health", font=dict(size=14, color="#1b4332")),
        number=dict(suffix="%", font=dict(size=24, color=color)),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#95a5a6"),
            bar=dict(color=color),
            bgcolor="white",
            borderwidth=2,
            bordercolor="#e9ecef",
            steps=[
                {"range": [0, 40], "color": "rgba(231, 76, 60, 0.2)"},
                {"range": [40, 60], "color": "rgba(230, 126, 34, 0.2)"},
                {"range": [60, 80], "color": "rgba(243, 156, 18, 0.2)"},
                {"range": [80, 100], "color": "rgba(39, 174, 96, 0.2)"}
            ]
        )
    ))
    
    fig.update_layout(
        height=250,
        margin=dict(l=40, r=40, t=50, b=20),
        paper_bgcolor="white"
    )
    
    return fig

# ─── HTML Components ─────────────────────────────────────────────────────────
def build_dashboard_html():
    """Generate complete dashboard HTML"""
    # Load and process data
    raw_scans = load_scans()
    processed_scans = process_scan_data(raw_scans)
    stats = get_stats(processed_scans)
    
    # Create charts
    health_chart = create_health_trend_chart(processed_scans)
    disease_chart = create_disease_pie_chart(stats["disease_counts"])
    severity_chart = create_severity_bar_chart(stats["severity_counts"])
    activity_chart = create_activity_timeline(processed_scans)
    gauge_chart = create_crop_health_gauge(stats["avg_health"])
    
    # Convert charts to HTML
    health_html = health_chart.to_html(full_html=False, include_plotlyjs="cdn")
    disease_html = disease_chart.to_html(full_html=False, include_plotlyjs=False)
    severity_html = severity_chart.to_html(full_html=False, include_plotlyjs=False)
    activity_html = activity_chart.to_html(full_html=False, include_plotlyjs=False)
    gauge_html = gauge_chart.to_html(full_html=False, include_plotlyjs=False)
    
    # Build recent scans table
    recent_scans_html = ""
    for scan in processed_scans[:10]:
        severity_color = get_severity_color(scan["severity"])
        severity_icon = get_severity_icon(scan["severity"])
        
        health_badge = "✅ Healthy" if scan["is_healthy"] else f"{severity_icon} {scan['severity']}"
        badge_color = "#27ae60" if scan["is_healthy"] else severity_color
        
        recent_scans_html += f"""
        <tr style="border-bottom:1px solid #e9ecef;">
            <td style="padding:12px;color:#495057;">{scan["date"]}</td>
            <td style="padding:12px;"><strong>{scan["crop"]}</strong></td>
            <td style="padding:12px;">{scan["disease"]}</td>
            <td style="padding:12px;">
                <span style="background:{badge_color}20;color:{badge_color};padding:4px 8px;border-radius:12px;font-size:11px;font-weight:600;">
                    {health_badge}
                </span>
            </td>
            <td style="padding:12px;">
                <div style="display:flex;align-items:center;gap:6px;">
                    <div style="flex:1;background:#e9ecef;border-radius:4px;height:4px;max-width:60px;">
                        <div style="background:{severity_color};width:{scan["confidence"]}%;height:100%;border-radius:4px;"></div>
                    </div>
                    <span style="font-size:11px;color:#495057;">{scan["confidence"]}%</span>
                </div>
            </td>
        </tr>"""
    
    if not recent_scans_html:
        recent_scans_html = '<tr><td colspan="5" style="padding:40px;text-align:center;color:#6c757d;">No scans yet. Start analyzing plants to see history!</td></tr>'
    
    # Build crop cards
    crop_cards_html = ""
    for crop, count in stats["crop_counts"].most_common(6):
        emoji = get_crop_emoji(crop)
        # Find last scan date
        crop_scans = [s for s in processed_scans if s["crop"] == crop]
        last_scan = crop_scans[0]["date"] if crop_scans else "Never"
        
        # Determine health status
        if crop_scans:
            if crop_scans[0]["is_healthy"]:
                status_color = "#27ae60"
                status_text = "Healthy"
                status_icon = "✅"
            elif crop_scans[0]["severity"] == "High":
                status_color = "#e74c3c"
                status_text = "Critical"
                status_icon = "🔴"
            elif crop_scans[0]["severity"] == "Medium":
                status_color = "#f39c12"
                status_text = "Warning"
                status_icon = "⚠️"
            else:
                status_color = "#27ae60"
                status_text = "Good"
                status_icon = "✅"
        else:
            status_color = "#95a5a6"
            status_text = "Unknown"
            status_icon = "❓"
        
        crop_cards_html += f"""
        <div style="background:white;border-radius:12px;border:1px solid #e9ecef;overflow:hidden;">
            <div style="background:linear-gradient(135deg, #1b4332, #2d6a4f);padding:16px;color:white;">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:32px;margin-bottom:4px;">{emoji}</div>
                        <div style="font-size:18px;font-weight:700;">{crop}</div>
                    </div>
                    <div style="background:{status_color};padding:4px 12px;border-radius:20px;font-size:11px;font-weight:600;">
                        {status_icon} {status_text}
                    </div>
                </div>
            </div>
            <div style="padding:16px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px;">
                    <div>
                        <div style="font-size:11px;color:#6c757d;margin-bottom:4px;">Total Scans</div>
                        <div style="font-size:20px;font-weight:700;color:#1b4332;">{count}</div>
                    </div>
                    <div>
                        <div style="font-size:11px;color:#6c757d;margin-bottom:4px;">Last Scan</div>
                        <div style="font-size:11px;color:#495057;">{last_scan}</div>
                    </div>
                </div>
            </div>
        </div>"""
    
    # Build alerts
    alerts_html = ""
    high_alerts = [s for s in processed_scans if s["severity"] == "High"][:3]
    for alert in high_alerts:
        alerts_html += f"""
        <div style="background:#fde8e8;border-left:4px solid #e74c3c;border-radius:8px;padding:12px;margin-bottom:12px;">
            <div style="display:flex;align-items:flex-start;gap:10px;">
                <div style="font-size:20px;">🚨</div>
                <div style="flex:1;">
                    <div style="font-weight:700;color:#1b4332;margin-bottom:4px;">Critical: {alert['disease']}</div>
                    <div style="font-size:12px;color:#6c757d;margin-bottom:6px;">Detected in {alert['crop']} - Immediate action required</div>
                    <div style="font-size:11px;color:#e74c3c;">{alert['date']}</div>
                </div>
            </div>
        </div>"""
    
    if not high_alerts:
        alerts_html = """
        <div style="background:#d4edda;border-left:4px solid #27ae60;border-radius:8px;padding:12px;">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="font-size:20px;">✅</div>
                <div>
                    <div style="font-weight:700;color:#1b4332;">No Critical Issues</div>
                    <div style="font-size:12px;color:#6c757d;">All crops are in good health. Keep monitoring regularly.</div>
                </div>
            </div>
        </div>"""
    
    # Generate complete HTML with navbar and footer
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PhytoScan AI · Crop Health Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Space+Grotesk:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Nunito', sans-serif;
            background: #f0f4f0;
            color: #1b4332;
        }}
        
        /* Navbar Styles - Matching app.py */
        #navbar {{
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
        }}
        
        #nav-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        
        #nav-brand-icon {{
            width: 40px;
            height: 40px;
            background: rgba(255,255,255,0.2);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }}
        
        #nav-brand-text {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: white;
            letter-spacing: -0.5px;
        }}
        
        #nav-brand-sub {{
            font-size: 10px;
            color: rgba(255,255,255,0.6);
            letter-spacing: 2px;
            text-transform: uppercase;
            margin-top: -4px;
        }}
        
        #nav-links {{
            display: flex;
            gap: 6px;
        }}
        
        .nav-btn {{
            color: rgba(255,255,255,0.85);
            background: transparent;
            border: none;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            font-family: 'Nunito', sans-serif;
            text-decoration: none;
            display: inline-block;
        }}
        
        .nav-btn:hover, .nav-btn.active {{
            background: rgba(255,255,255,0.15);
            color: white;
        }}
        
        /* Hero Section */
        #hero {{
            background: linear-gradient(135deg, #1b4332 0%, #2d6a4f 60%, #52b788 100%);
            padding: 48px 32px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        #hero::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
        }}
        
        #hero-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: clamp(28px, 5vw, 48px);
            font-weight: 700;
            color: white;
            margin-bottom: 12px;
            position: relative;
        }}
        
        #hero-sub {{
            font-size: clamp(13px, 2vw, 16px);
            color: rgba(255,255,255,0.75);
            max-width: 560px;
            margin: 0 auto 28px;
            line-height: 1.6;
            position: relative;
        }}
        
        .hero-stats {{
            display: flex;
            justify-content: center;
            gap: 32px;
            flex-wrap: wrap;
            position: relative;
        }}
        
        .hero-stat {{
            text-align: center;
            color: white;
        }}
        
        .hero-stat-num {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 28px;
            font-weight: 700;
            line-height: 1;
        }}
        
        .hero-stat-label {{
            font-size: 11px;
            color: rgba(255,255,255,0.6);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-top: 4px;
        }}
        
        /* Main Content */
        #main-content {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 32px 24px;
        }}
        
        .section-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: #1b4332;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .section-sub {{
            font-size: 13px;
            color: #888;
            margin-bottom: 20px;
        }}
        
        .card {{
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
            border: 1px solid rgba(0,0,0,0.04);
            margin-bottom: 24px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 20px;
            margin-bottom: 32px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 16px;
            padding: 20px;
            border: 1px solid #e9ecef;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            transition: all 0.3s;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 24px;
            margin-bottom: 24px;
        }}
        
        .crops-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 24px;
        }}
        
        .scan-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .scan-table th {{
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            font-size: 12px;
            font-weight: 700;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 1px;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .scan-table td {{
            padding: 12px;
            font-size: 13px;
        }}
        
        .scan-table tr:hover {{
            background: #f8f9fa;
        }}
        
        /* Footer - Matching app.py */
        #footer {{
            background: linear-gradient(135deg, #0d2818 0%, #1b4332 100%);
            color: rgba(255,255,255,0.8);
            padding: 48px 32px 24px;
            margin-top: 32px;
        }}
        
        .footer-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 32px;
            max-width: 1200px;
            margin: 0 auto 32px;
        }}
        
        .footer-brand h3 {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: white;
            margin: 0 0 8px;
        }}
        
        .footer-brand p {{
            font-size: 13px;
            line-height: 1.6;
            color: rgba(255,255,255,0.5);
            margin: 0;
        }}
        
        .footer-col h4 {{
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 2px;
            color: #52b788;
            margin: 0 0 14px;
            font-weight: 700;
        }}
        
        .footer-col ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        
        .footer-col ul li {{
            font-size: 13px;
            color: rgba(255,255,255,0.5);
            margin-bottom: 8px;
            cursor: pointer;
            transition: color 0.2s;
        }}
        
        .footer-col ul li:hover {{
            color: #52b788;
        }}
        
        .footer-bottom {{
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
        }}
        
        .footer-badges {{
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }}
        
        .footer-badge {{
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 6px;
            padding: 4px 10px;
            font-size: 11px;
            color: rgba(255,255,255,0.5);
        }}
        
        @media (max-width: 768px) {{
            #navbar {{
                padding: 0 16px;
                height: auto;
                padding: 12px 16px;
            }}
            #hero {{
                padding: 32px 16px;
            }}
            #main-content {{
                padding: 20px 16px;
            }}
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <!-- Navbar -->
    <div id="navbar">
        <div id="nav-brand">
            <div id="nav-brand-icon">🌿</div>
            <div>
                <div id="nav-brand-text">PhytoScan AI</div>
                <div id="nav-brand-sub">Crop Health Dashboard</div>
            </div>
        </div>
        <div id="nav-links">
            <a href="http://localhost:7860" class="nav-btn">🏠 Home</a>
            <a href="http://localhost:7861" class="nav-btn active">📊 Dashboard</a>
            <a href="http://localhost:7860" class="nav-btn">🔬 Analyze</a>
        </div>
    </div>
    
    <!-- Hero Section -->
    <div id="hero">
        <div id="hero-title">📊 Crop Health Analytics Dashboard</div>
        <div id="hero-sub">Comprehensive insights and visualizations from your plant scans history</div>
        <div class="hero-stats">
            <div class="hero-stat"><div class="hero-stat-num">{stats["total_scans"]}</div><div class="hero-stat-label">Total Scans</div></div>
            <div class="hero-stat"><div class="hero-stat-num">{stats["unique_crops"]}</div><div class="hero-stat-label">Crops</div></div>
            <div class="hero-stat"><div class="hero-stat-num">{stats["healthy_scans"]}</div><div class="hero-stat-label">Healthy</div></div>
            <div class="hero-stat"><div class="hero-stat-num">{stats["critical_count"]}</div><div class="hero-stat-label">Critical</div></div>
        </div>
    </div>
    
    <!-- Main Content -->
    <div id="main-content">
        <!-- Stats Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div style="font-size:32px;margin-bottom:8px;">📊</div>
                <div style="font-size:28px;font-weight:800;color:#1b4332;">{stats["total_scans"]}</div>
                <div style="font-size:13px;color:#6c757d;">Total Scans</div>
                <div style="margin-top:8px;font-size:11px;color:#27ae60;">↑ All time</div>
            </div>
            <div class="stat-card">
                <div style="font-size:32px;margin-bottom:8px;">🌾</div>
                <div style="font-size:28px;font-weight:800;color:#1b4332;">{stats["unique_crops"]}</div>
                <div style="font-size:13px;color:#6c757d;">Active Crops</div>
                <div style="margin-top:8px;font-size:11px;color:#6c757d;">→ Monitored</div>
            </div>
            <div class="stat-card">
                <div style="font-size:32px;margin-bottom:8px;">✅</div>
                <div style="font-size:28px;font-weight:800;color:#1b4332;">{stats["healthy_scans"]}</div>
                <div style="font-size:13px;color:#6c757d;">Healthy Plants</div>
                <div style="margin-top:8px;font-size:11px;color:#27ae60;">{stats['healthy_scans']/max(1,stats['total_scans'])*100:.0f}% of scans</div>
            </div>
            <div class="stat-card">
                <div style="font-size:32px;margin-bottom:8px;">🦠</div>
                <div style="font-size:28px;font-weight:800;color:#1b4332;">{stats["unique_diseases"]}</div>
                <div style="font-size:13px;color:#6c757d;">Unique Diseases</div>
                <div style="margin-top:8px;font-size:11px;color:#e74c3c;">Detected</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="card">
                {health_html}
            </div>
            <div class="card">
                {gauge_html}
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="card">
                {disease_html}
            </div>
            <div class="card">
                {severity_html}
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="card">
                {activity_html}
            </div>
            <div class="card">
                <div style="height:280px;display:flex;align-items:center;justify-content:center;">
                    <div style="text-align:center;">
                        <div style="font-size:48px;margin-bottom:16px;">🌿</div>
                        <div style="font-size:14px;color:#1b4332;font-weight:600;">AI-Powered Insights</div>
                        <div style="font-size:12px;color:#6c757d;margin-top:8px;">Real-time crop health monitoring</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Crop Cards -->
        <div class="section-title">🌱 Active Crops</div>
        <div class="section-sub">Health status and monitoring history</div>
        <div class="crops-grid">
            {crop_cards_html}
        </div>
        
        <!-- Alerts Section -->
        <div class="section-title">🚨 Active Alerts</div>
        <div class="section-sub">Critical issues requiring immediate attention</div>
        <div class="card">
            {alerts_html}
        </div>
        
        <!-- Recent Scans -->
        <div class="section-title">📋 Recent Scans</div>
        <div class="section-sub">Latest plant health analyses</div>
        <div class="card" style="padding: 0; overflow-x: auto;">
            <table class="scan-table">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Crop</th>
                        <th>Disease</th>
                        <th>Status</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {recent_scans_html}
                </tbody>
            </table>
        </div>
    </div>
    
    <!-- Footer -->
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
                    <li>📊 Analytics Dashboard</li>
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
                    <li>🎨 Plotly & Gradio</li>
                    <li>🐍 Python</li>
                    <li>🔑 Google AI Studio</li>
                </ul>
            </div>
        </div>
        <div class="footer-bottom">
            <div>© 2026 PhytoScan AI · Built for smarter farming 🌾</div>
            <div class="footer-badges">
                <div class="footer-badge">🆓 Free to Use</div>
                <div class="footer-badge">🔒 Privacy First</div>
                <div class="footer-badge">⚡ Real-time Analytics</div>
            </div>
        </div>
    </div>
</body>
</html>
    """
    
    return html

# ─── Gradio App ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    custom_css = """
    .gradio-container {
        max-width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    footer {
        display: none !important;
    }
    """
    
    # For Gradio 6.0+, move css to launch() instead of Blocks constructor
    with gr.Blocks(title="PhytoScan AI Dashboard") as demo:
        gr.HTML(build_dashboard_html())
    
    demo.launch(server_port=7861, debug=True, share=False, css=custom_css)