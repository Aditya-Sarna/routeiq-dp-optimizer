"""
╔══════════════════════════════════════════════════════════════════╗
║   RouteIQ — New Delhi DP Route Optimizer                         ║
║   Held-Karp TSP  |  OpenStreetMap  |  Haversine Distances        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import subprocess
import math
import os
import time

# ──────────────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="RouteIQ Delhi — DP Route Optimizer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────
# CSS
# ──────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
  .stApp { background: #0a0e1a; color: #f1f5f9; }
  section[data-testid="stSidebar"] { background: #111827 !important; border-right: 1px solid #1e2d45; }
  section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }
  [data-testid="metric-container"] { background: #111827; border: 1px solid #1e2d45; border-radius: 14px; padding: 16px 20px; }
  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.06em; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #60a5fa !important; font-family: 'JetBrains Mono', monospace !important; font-size: 1.6rem !important; font-weight: 700 !important; }
  .stButton > button { background: linear-gradient(135deg, #3b82f6, #6366f1) !important; color: white !important; border: none !important; border-radius: 10px !important; font-weight: 600 !important; padding: 10px 24px !important; font-size: 0.9rem !important; transition: all 0.2s !important; width: 100% !important; letter-spacing: 0.02em !important; }
  .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important; }
  .stNumberInput input, .stTextInput input { background: #1a2235 !important; border: 1px solid #1e2d45 !important; color: #f1f5f9 !important; border-radius: 8px !important; }
  .stDataFrame { background: #111827 !important; border-radius: 12px !important; }
  .streamlit-expanderHeader { background: #111827 !important; border-radius: 10px !important; border: 1px solid #1e2d45 !important; }
  .stSuccess { background: rgba(16,185,129,0.1) !important; border-left: 4px solid #10b981 !important; color: #6ee7b7 !important; }
  .stError   { background: rgba(239,68,68,0.1) !important; border-left: 4px solid #ef4444 !important; color: #fca5a5 !important; }
  .stInfo    { background: rgba(59,130,246,0.1) !important; border-left: 4px solid #3b82f6 !important; color: #93c5fd !important; }
  .hero-card { background: linear-gradient(135deg, #111827 0%, #1a2235 100%); border: 1px solid #1e2d45; border-radius: 18px; padding: 24px 32px; margin-bottom: 20px; display: flex; align-items: center; gap: 20px; }
  .hero-title { font-size: 1.9rem; font-weight: 800; color: #f1f5f9; line-height: 1.2; }
  .hero-sub   { color: #64748b; font-size: 0.88rem; margin-top: 6px; }
  .badge-row  { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; }
  .badge-blue   { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3); color: #60a5fa; }
  .badge-green  { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; }
  .badge-orange { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24; }
  .badge-purple { background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.3); color: #a78bfa; }
  .badge-red    { background: rgba(239,68,68,0.15); border: 1px solid rgba(239,68,68,0.3); color: #f87171; }
  .section-header { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.1em; border-bottom: 1px solid #1e2d45; padding-bottom: 8px; margin-bottom: 12px; }
  .route-step-item { background: #111827; border: 1px solid #1e2d45; border-radius: 10px; padding: 10px 14px; margin: 4px 0; display: flex; align-items: center; gap: 10px; }
  .dp-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  .dp-table td { padding: 6px 10px; border-bottom: 1px solid #1e2d45; }
  .dp-table td:first-child { color: #64748b; }
  .dp-table td:last-child { color: #f1f5f9; font-family: 'JetBrains Mono', monospace; font-weight: 500; }
  .sidebar-label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────
# New Delhi Landmarks
# ──────────────────────────────────────────────────────
DELHI_LANDMARKS = {
    "India Gate":             (28.6129, 77.2295),
    "Red Fort":               (28.6562, 77.2410),
    "Qutub Minar":            (28.5244, 77.1855),
    "Humayun's Tomb":         (28.5933, 77.2507),
    "Lotus Temple":           (28.5535, 77.2588),
    "Akshardham Temple":      (28.6127, 77.2773),
    "Rashtrapati Bhavan":     (28.6143, 77.1993),
    "Parliament House":       (28.6173, 77.2090),
    "Jama Masjid":            (28.6507, 77.2334),
    "Jantar Mantar":          (28.6270, 77.2166),
    "Connaught Place":        (28.6315, 77.2167),
    "Chandni Chowk":          (28.6507, 77.2301),
    "Karol Bagh":             (28.6514, 77.1908),
    "Lajpat Nagar":           (28.5677, 77.2433),
    "Sarojini Nagar":         (28.5730, 77.1952),
    "Hauz Khas Village":      (28.5494, 77.2001),
    "Paharganj":              (28.6432, 77.2127),
    "Saket Mall":             (28.5245, 77.2066),
    "IGI Airport T3":         (28.5562, 77.1000),
    "New Delhi Railway Stn":  (28.6419, 77.2194),
    "Old Delhi Railway Stn":  (28.6600, 77.2267),
    "Hazrat Nizamuddin Stn":  (28.5883, 77.2507),
    "ISBT Kashmere Gate":     (28.6669, 77.2278),
    "AIIMS Delhi":            (28.5672, 77.2100),
    "Delhi University":       (28.6880, 77.2160),
    "IIT Delhi":              (28.5450, 77.1926),
    "Dwarka Sector 21":       (28.5521, 77.0588),
    "Rohini Sector 18":       (28.7495, 77.1112),
    "Vasant Kunj":            (28.5214, 77.1569),
    "Pitampura":              (28.7008, 77.1387),
    "Noida Sector 18":        (28.5700, 77.3210),
    "Gurugram Cyber City":    (28.4950, 77.0887),
}

DEMO_TOURS = {
    "Tourist Circuit (5 stops)": [
        "India Gate", "Red Fort", "Qutub Minar", "Humayun's Tomb", "Lotus Temple"
    ],
    "Delhi Markets (6 stops)": [
        "Connaught Place", "Chandni Chowk", "Karol Bagh",
        "Lajpat Nagar", "Sarojini Nagar", "Paharganj"
    ],
    "Transport Hubs (5 stops)": [
        "IGI Airport T3", "New Delhi Railway Stn", "Old Delhi Railway Stn",
        "Hazrat Nizamuddin Stn", "ISBT Kashmere Gate"
    ],
    "Monuments Grand Tour (8 stops)": [
        "India Gate", "Red Fort", "Qutub Minar", "Humayun's Tomb",
        "Lotus Temple", "Akshardham Temple", "Rashtrapati Bhavan", "Jantar Mantar"
    ],
    "City to Airport (7 stops)": [
        "IGI Airport T3", "Connaught Place", "India Gate",
        "Akshardham Temple", "Red Fort", "Saket Mall", "Hauz Khas Village"
    ],
}

NODE_COLORS = ["#ef4444","#3b82f6","#10b981","#f59e0b","#8b5cf6","#06b6d4",
               "#ec4899","#a3e635","#fb923c","#facc15","#34d399","#a78bfa","#f472b6","#38bdf8"]

CPP_BINARY = os.path.join(os.path.dirname(__file__), "cpp_engine", "route_optimizer")
CPP_SOURCE  = os.path.join(os.path.dirname(__file__), "cpp_engine", "route_optimizer.cpp")

if not os.path.isfile(CPP_BINARY) and os.path.isfile(CPP_SOURCE):
    try:
        subprocess.run(["g++", "-O2", "-std=c++17", "-o", CPP_BINARY, CPP_SOURCE],
                       check=True, capture_output=True, timeout=30)
    except Exception:
        pass

INF = float('inf')

# ──────────────────────────────────────────────────────
# Haversine distance (km)
# ──────────────────────────────────────────────────────
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a  = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def build_dist_matrix(locations):
    n = len(locations)
    return [[0.0 if i == j else haversine(
                locations[i]['lat'], locations[i]['lon'],
                locations[j]['lat'], locations[j]['lon'])
             for j in range(n)] for i in range(n)]

# ──────────────────────────────────────────────────────
# Held-Karp DP
# ──────────────────────────────────────────────────────
def held_karp_python(dist, n):
    if n == 1:
        return 0.0, [0, 0]
    states = 1 << n
    dp     = [[INF]*n for _ in range(states)]
    parent = [[-1]*n  for _ in range(states)]
    dp[1][0] = 0.0
    for mask in range(1, states):
        if not (mask & 1):
            continue
        for u in range(n):
            if not (mask & (1 << u)) or dp[mask][u] == INF:
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                new_mask = mask | (1 << v)
                new_cost = dp[mask][u] + dist[u][v]
                if new_cost < dp[new_mask][v]:
                    dp[new_mask][v] = new_cost
                    parent[new_mask][v] = u
    full_mask = states - 1
    best_cost, last_city = INF, -1
    for u in range(1, n):
        if dp[full_mask][u] != INF:
            total = dp[full_mask][u] + dist[u][0]
            if total < best_cost:
                best_cost, last_city = total, u
    if last_city == -1:
        return INF, []
    path, mask, cur = [], full_mask, last_city
    while cur != -1:
        path.append(cur)
        prev = parent[mask][cur]
        mask ^= (1 << cur)
        cur = prev
    path.reverse()
    path.append(0)
    return best_cost, path

def run_cpp_solver(dist, n):
    if not os.path.isfile(CPP_BINARY):
        return None
    try:
        inp = f"{n}\n" + "".join(" ".join(f"{v:.6f}" for v in row)+"\n" for row in dist)
        res = subprocess.run([CPP_BINARY], input=inp, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            return None
        lines = res.stdout.strip().split("\n")
        if lines[0] == "NO_ROUTE":
            return None
        return float(lines[0]), list(map(int, lines[1].split()))
    except Exception:
        return None

def optimize(locations):
    n    = len(locations)
    dist = build_dist_matrix(locations)
    cpp  = run_cpp_solver(dist, n)
    if cpp:
        cost, path = cpp
        solver = "C++ Held-Karp (compiled)"
    else:
        cost, path = held_karp_python(dist, n)
        solver = "Python Held-Karp (interpreted)"
    segments = [{"from": path[k], "to": path[k+1],
                 "distance": round(dist[path[k]][path[k+1]], 3)}
                for k in range(len(path)-1)]
    return {"total_cost": round(cost, 3), "path": path,
            "segments": segments, "dist": dist, "solver": solver}

# ──────────────────────────────────────────────────────
# Mapbox figure — OpenStreetMap, New Delhi
# ──────────────────────────────────────────────────────
DELHI_CENTER = {"lat": 28.6139, "lon": 77.2090}

def make_map_figure(locations, result=None):
    fig = go.Figure()

    if result:
        path = result["path"]
        segs = result["segments"]

        route_lats = [locations[idx]['lat'] for idx in path]
        route_lons = [locations[idx]['lon'] for idx in path]

        # Glow halo
        fig.add_trace(go.Scattermapbox(
            lat=route_lats, lon=route_lons, mode="lines",
            line=dict(width=10, color="rgba(59,130,246,0.22)"),
            hoverinfo="skip", name="",
        ))
        # Main route
        fig.add_trace(go.Scattermapbox(
            lat=route_lats, lon=route_lons, mode="lines",
            line=dict(width=3.5, color="#3b82f6"),
            hoverinfo="skip", name="Optimal Route",
        ))
        # Distance labels at midpoints
        for seg in segs:
            mlat = (locations[seg["from"]]['lat'] + locations[seg["to"]]['lat']) / 2
            mlon = (locations[seg["from"]]['lon'] + locations[seg["to"]]['lon']) / 2
            fig.add_trace(go.Scattermapbox(
                lat=[mlat], lon=[mlon], mode="markers+text",
                marker=dict(size=1, color="rgba(0,0,0,0)"),
                text=[f"  {seg['distance']:.2f} km"],
                textfont=dict(size=11, color="#f59e0b"),
                hoverinfo="skip", name="",
            ))

    # Nodes
    for idx, loc in enumerate(locations):
        is_depot = idx == 0
        color    = "#ef4444" if is_depot else NODE_COLORS[idx % len(NODE_COLORS)]
        label    = ("⚑ " if is_depot else f"{idx}. ") + loc["name"]
        fig.add_trace(go.Scattermapbox(
            lat=[loc['lat']], lon=[loc['lon']],
            mode="markers+text",
            marker=go.scattermapbox.Marker(size=20 if is_depot else 15, color=color, opacity=0.95),
            text=[label],
            textposition="top right",
            textfont=dict(size=12, color="#f1f5f9", family="Inter"),
            hovertemplate=f"<b>{loc['name']}</b><br>Lat: {loc['lat']:.4f}<br>Lon: {loc['lon']:.4f}<extra></extra>",
            name=loc["name"],
        ))

    fig.update_layout(
        mapbox=dict(style="open-street-map", center=DELHI_CENTER, zoom=10.5),
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0a0e1a",
        margin=dict(l=0, r=0, t=0, b=0),
        height=560,
        showlegend=False,
        hovermode="closest",
        font=dict(family="Inter", color="#f1f5f9"),
    )
    return fig

# ──────────────────────────────────────────────────────
# Session State
# ──────────────────────────────────────────────────────
for key, val in [("locations", []), ("result", None), ("optimize_time", None)]:
    if key not in st.session_state:
        st.session_state[key] = val

# ──────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:12px 0 20px">
      <div style="font-size:2.4rem;margin-bottom:6px">🗺️</div>
      <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9">RouteIQ Delhi</div>
      <div style="font-size:0.75rem;color:#64748b;margin-top:4px">DP Route Optimizer · New Delhi</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # ── Demo Tours ──
    st.markdown('<div class="sidebar-label">Quick Demo Tours</div>', unsafe_allow_html=True)
    demo_choice = st.selectbox("Tour", list(DEMO_TOURS.keys()),
                               key="demo_choice", label_visibility="collapsed")
    if st.button("🎲  Load Demo Tour", key="btn_demo"):
        locs = [{"name": name, "lat": DELHI_LANDMARKS[name][0],
                 "lon": DELHI_LANDMARKS[name][1], "index": i}
                for i, name in enumerate(DEMO_TOURS[demo_choice])]
        st.session_state.locations  = locs
        st.session_state.result     = None
        st.rerun()

    st.divider()

    # ── Add Landmark ──
    st.markdown('<div class="sidebar-label">Add Landmark</div>', unsafe_allow_html=True)
    added     = {loc["name"] for loc in st.session_state.locations}
    available = ["— select —"] + sorted(n for n in DELHI_LANDMARKS if n not in added)
    sel = st.selectbox("Landmark", available, key="lm_sel", label_visibility="collapsed")
    if st.button("＋  Add Landmark", key="btn_add_lm"):
        if sel and sel != "— select —":
            lat, lon = DELHI_LANDMARKS[sel]
            n = len(st.session_state.locations)
            st.session_state.locations.append({"name": sel, "lat": lat, "lon": lon, "index": n})
            st.session_state.result = None
            st.rerun()

    st.divider()

    # ── Custom Location ──
    st.markdown('<div class="sidebar-label">Custom Location</div>', unsafe_allow_html=True)
    cname = st.text_input("Name", placeholder="My Location", key="cname", label_visibility="collapsed")
    cc1, cc2 = st.columns(2)
    with cc1:
        clat = st.number_input("Lat", value=28.6139, format="%.4f", key="clat")
    with cc2:
        clon = st.number_input("Lon", value=77.2090, format="%.4f", key="clon")
    if st.button("＋  Add Custom", key="btn_custom"):
        n    = len(st.session_state.locations)
        name = cname.strip() or f"Location {n+1}"
        st.session_state.locations.append({"name": name, "lat": float(clat), "lon": float(clon), "index": n})
        st.session_state.result = None
        st.rerun()

    st.divider()

    # ── Stops List ──
    locs = st.session_state.locations
    if locs:
        st.markdown(f'<div class="sidebar-label">Stops ({len(locs)})</div>', unsafe_allow_html=True)
        to_remove = None
        for i, loc in enumerate(locs):
            cl, cr = st.columns([5, 1])
            with cl:
                tag   = "⚑" if i == 0 else str(i)
                color = "#ef4444" if i == 0 else "#60a5fa"
                st.markdown(
                    f'<div style="padding:3px 0;font-size:0.8rem">'
                    f'<span style="color:{color};font-weight:700">{tag}</span>&nbsp;{loc["name"]}<br>'
                    f'<span style="color:#475569;font-family:monospace;font-size:0.68rem">'
                    f'{loc["lat"]:.4f}, {loc["lon"]:.4f}</span></div>',
                    unsafe_allow_html=True)
            with cr:
                if st.button("×", key=f"rm_{i}"):
                    to_remove = i
        if to_remove is not None:
            st.session_state.locations.pop(to_remove)
            for j, l in enumerate(st.session_state.locations):
                l["index"] = j
            st.session_state.result = None
            st.rerun()
        st.divider()
        if st.button("🗑️  Clear All", key="btn_clear"):
            st.session_state.locations = []
            st.session_state.result    = None
            st.rerun()

    # ── Algorithm Info ──
    st.divider()
    st.markdown('<div class="sidebar-label">Algorithm Details</div>', unsafe_allow_html=True)
    n        = len(st.session_state.locations)
    states   = 2**n if n > 0 else 0
    subprobs = n * states if n > 0 else 0
    cpp_ok   = os.path.isfile(CPP_BINARY)
    st.markdown(f"""
    <table class="dp-table">
      <tr><td>Algorithm</td><td>Held-Karp DP</td></tr>
      <tr><td>Time</td><td>O(n² · 2ⁿ)</td></tr>
      <tr><td>Space</td><td>O(n · 2ⁿ)</td></tr>
      <tr><td>Distance</td><td>Haversine (km)</td></tr>
      <tr><td>Map</td><td>OpenStreetMap</td></tr>
      <tr><td>City</td><td>New Delhi 🇮🇳</td></tr>
      <tr><td>Nodes (n)</td><td>{n}</td></tr>
      <tr><td>DP States</td><td>{states:,}</td></tr>
      <tr><td>Subproblems</td><td>{subprobs:,}</td></tr>
      <tr><td>Solver</td><td>{"C++ binary ✓" if cpp_ok else "Python ⚡"}</td></tr>
    </table>""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────
# MAIN CONTENT
# ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero-card">
  <div style="font-size:3rem">🗺️</div>
  <div>
    <div class="hero-title">RouteIQ — New Delhi Route Optimizer</div>
    <div class="hero-sub">Held-Karp Dynamic Programming on real New Delhi geography · Haversine distances · OpenStreetMap</div>
    <div class="badge-row">
      <span class="badge badge-blue">Held-Karp DP</span>
      <span class="badge badge-green">Exact Optimal Tour</span>
      <span class="badge badge-orange">Haversine km</span>
      <span class="badge badge-purple">C++ Engine</span>
      <span class="badge badge-red">New Delhi 🇮🇳</span>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

locs   = st.session_state.locations
result = st.session_state.result
n      = len(locs)

c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("Stops", n, help="Including depot (first stop)")
with c2: st.metric("Total Distance", f"{result['total_cost']:.2f} km" if result else "—", help="Optimal round-trip in km")
with c3: st.metric("DP States", f"{2**n:,}" if n > 0 else "—", help="Bitmask states explored")
with c4: st.metric("Solve Time", f"{st.session_state.optimize_time:.4f}s" if st.session_state.optimize_time else "—")

st.markdown("<br>", unsafe_allow_html=True)

map_col, info_col = st.columns([3, 1])

with map_col:
    st.markdown('<div class="section-header">New Delhi — Route Map (OpenStreetMap)</div>', unsafe_allow_html=True)
    if n >= 2:
        if st.button(f"✦  Run Held-Karp DP  ({n} stops)", key="btn_opt"):
            with st.spinner("Computing optimal tour with Held-Karp DP..."):
                t0  = time.perf_counter()
                res = optimize(locs)
                t1  = time.perf_counter()
            st.session_state.result        = res
            st.session_state.optimize_time = round(t1 - t0, 5)
            st.rerun()
    elif n == 1:
        st.info("Add at least one more stop to run the optimizer.")
    else:
        st.info("Load a **Demo Tour** or add landmarks from the sidebar, then click **Run Held-Karp DP**.")

    fig = make_map_figure(locs, st.session_state.result)
    st.plotly_chart(fig, use_container_width=True,
                    config={"displayModeBar": True,
                            "modeBarButtonsToRemove": ["lasso2d","select2d"],
                            "scrollZoom": True})

with info_col:
    st.markdown('<div class="section-header">Optimal Route</div>', unsafe_allow_html=True)
    if result:
        path = result["path"]
        segs = result["segments"]
        st.success(f"**Tour: {result['total_cost']:.2f} km**")
        st.caption(f"Solver: {result.get('solver','')}")
        for step_i, city_idx in enumerate(path):
            loc      = locs[city_idx]
            is_depot = step_i == 0 or step_i == len(path)-1
            color    = "#ef4444" if is_depot else "#3b82f6"
            label    = "⚑" if is_depot else f"#{step_i}"
            dist_tag = ""
            if step_i < len(segs):
                dist_tag = f'<span style="float:right;color:#f59e0b;font-family:monospace;font-size:0.72rem">{segs[step_i]["distance"]:.2f} km</span>'
            st.markdown(
                f'<div class="route-step-item">'
                f'<span style="color:{color};font-weight:700;font-size:0.78rem;min-width:26px">{label}</span>'
                f'<span style="font-size:0.8rem;flex:1">{loc["name"]}</span>'
                f'{dist_tag}</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Segment Breakdown</div>', unsafe_allow_html=True)
        df = pd.DataFrame([{"From": locs[s["from"]]["name"],
                             "To":   locs[s["to"]]["name"],
                             "km":   s["distance"]} for s in segs])
        st.dataframe(df, use_container_width=True, hide_index=True, height=220)
    else:
        st.markdown("""
        <div style="color:#334155;text-align:center;padding:40px 10px;font-size:0.88rem;line-height:1.8">
          <div style="font-size:2rem;margin-bottom:10px">📍</div>
          Load a demo tour or pick<br>landmarks, then click<br>
          <b style="color:#60a5fa">Run Held-Karp DP</b>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 How Held-Karp DP Works"):
        st.markdown("""
**Recurrence:**
```
dp[mask][i] = min cost to visit all
  cities in bitmask, ending at i

dp[mask|(1<<v)][v] = dp[mask][u] + dist[u][v]
```
**Distances:** Haversine formula — exact great-circle km.

**Complexity:** O(n² · 2ⁿ) time · O(n · 2ⁿ) space

**Industry use:** Amazon last-mile, FedEx, Swiggy/Zomato dispatch
        """)

st.divider()
if locs:
    with st.expander(f"🧮 Distance Matrix ({n}×{n}) — km"):
        dist  = build_dist_matrix(locs)
        names = [l["name"] for l in locs]
        df_d  = pd.DataFrame([[round(dist[i][j], 2) for j in range(n)] for i in range(n)],
                              index=names, columns=names)
        st.dataframe(df_d, use_container_width=True)
