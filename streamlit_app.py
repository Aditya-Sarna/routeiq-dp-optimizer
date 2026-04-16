"""
╔══════════════════════════════════════════════════════════════════╗
║   RouteIQ — Dynamic Programming Route Optimizer                  ║
║   Held-Karp TSP Algorithm  |  Industry-Grade  |  Streamlit UI   ║
║                                                                   ║
║   Algorithm: Held-Karp DP  (same core used in Google OR-Tools)   ║
║   Complex : O(n² · 2ⁿ) time  |  O(n · 2ⁿ) space                ║
║   Industry : Last-mile delivery, fleet routing, logistics        ║
╚══════════════════════════════════════════════════════════════════╝
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import subprocess
import math
import os
import time
import random

# ──────────────────────────────────────────────────────
# Page Config
# ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="RouteIQ — DP Route Optimizer",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────
# Custom CSS — Dark premium theme
# ──────────────────────────────────────────────────────
st.markdown("""
<style>
  /* ── Global ── */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

  /* ── App background ── */
  .stApp { background: #0a0e1a; color: #f1f5f9; }
  section[data-testid="stSidebar"] { background: #111827 !important; border-right: 1px solid #1e2d45; }
  section[data-testid="stSidebar"] * { color: #f1f5f9 !important; }

  /* ── Hide Streamlit chrome ── */
  #MainMenu, footer, header { visibility: hidden; }
  .block-container { padding-top: 1rem !important; padding-bottom: 1rem !important; }

  /* ── Metric cards ── */
  [data-testid="metric-container"] {
    background: #111827;
    border: 1px solid #1e2d45;
    border-radius: 14px;
    padding: 16px 20px;
  }
  [data-testid="metric-container"] label { color: #64748b !important; font-size: 0.75rem !important; text-transform: uppercase; letter-spacing: 0.06em; }
  [data-testid="metric-container"] [data-testid="stMetricValue"] { color: #60a5fa !important; font-family: 'JetBrains Mono', monospace !important; font-size: 1.6rem !important; font-weight: 700 !important; }

  /* ── Buttons ── */
  .stButton > button {
    background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
    color: white !important; border: none !important;
    border-radius: 10px !important; font-weight: 600 !important;
    padding: 10px 24px !important; font-size: 0.9rem !important;
    transition: all 0.2s !important; width: 100% !important;
    letter-spacing: 0.02em !important;
  }
  .stButton > button:hover { transform: translateY(-2px) !important; box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important; }

  /* ── Inputs ── */
  .stNumberInput input, .stTextInput input, .stSelectbox select {
    background: #1a2235 !important; border: 1px solid #1e2d45 !important;
    color: #f1f5f9 !important; border-radius: 8px !important;
    font-family: 'Inter', sans-serif !important;
  }
  .stNumberInput input:focus, .stTextInput input:focus { border-color: #3b82f6 !important; }

  /* ── Dataframe ── */
  .stDataFrame { background: #111827 !important; border-radius: 12px !important; }

  /* ── Expander ── */
  .streamlit-expanderHeader { background: #111827 !important; border-radius: 10px !important; border: 1px solid #1e2d45 !important; }

  /* ── Alert boxes ── */
  .stSuccess { background: rgba(16,185,129,0.1) !important; border-left: 4px solid #10b981 !important; color: #6ee7b7 !important; }
  .stError   { background: rgba(239,68,68,0.1) !important; border-left: 4px solid #ef4444 !important; color: #fca5a5 !important; }
  .stInfo    { background: rgba(59,130,246,0.1) !important; border-left: 4px solid #3b82f6 !important; color: #93c5fd !important; }
  .stWarning { background: rgba(245,158,11,0.1) !important; border-left: 4px solid #f59e0b !important; color: #fcd34d !important; }

  /* ── Custom header card ── */
  .hero-card {
    background: linear-gradient(135deg, #111827 0%, #1a2235 100%);
    border: 1px solid #1e2d45; border-radius: 18px;
    padding: 24px 32px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 20px;
  }
  .hero-icon { font-size: 3rem; }
  .hero-title { font-size: 1.9rem; font-weight: 800; color: #f1f5f9; line-height: 1.2; }
  .hero-sub   { color: #64748b; font-size: 0.88rem; margin-top: 6px; }
  .badge-row  { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .badge {
    padding: 4px 12px; border-radius: 20px; font-size: 0.72rem; font-weight: 600;
    letter-spacing: 0.05em;
  }
  .badge-blue   { background: rgba(59,130,246,0.15); border: 1px solid rgba(59,130,246,0.3); color: #60a5fa; }
  .badge-green  { background: rgba(16,185,129,0.15); border: 1px solid rgba(16,185,129,0.3); color: #34d399; }
  .badge-orange { background: rgba(245,158,11,0.15); border: 1px solid rgba(245,158,11,0.3); color: #fbbf24; }
  .badge-purple { background: rgba(139,92,246,0.15); border: 1px solid rgba(139,92,246,0.3); color: #a78bfa; }

  /* ── Section header ── */
  .section-header {
    font-size: 0.75rem; font-weight: 700; color: #64748b;
    text-transform: uppercase; letter-spacing: 0.1em;
    border-bottom: 1px solid #1e2d45; padding-bottom: 8px; margin-bottom: 12px;
  }

  /* ── Route step ── */
  .route-step-item {
    background: #111827; border: 1px solid #1e2d45; border-radius: 10px;
    padding: 10px 14px; margin: 4px 0;
    display: flex; align-items: center; gap: 10px;
  }

  /* ── DP info table ── */
  .dp-table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  .dp-table td { padding: 6px 10px; border-bottom: 1px solid #1e2d45; }
  .dp-table td:first-child { color: #64748b; }
  .dp-table td:last-child { color: #f1f5f9; font-family: 'JetBrains Mono', monospace; font-weight: 500; }

  /* ── Sidebar label ── */
  .sidebar-label { font-size: 0.75rem; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────
CPP_BINARY = os.path.join(os.path.dirname(__file__), "cpp_engine", "route_optimizer")
CPP_SOURCE = os.path.join(os.path.dirname(__file__), "cpp_engine", "route_optimizer.cpp")

# Auto-compile C++ solver if binary is missing (runs on Streamlit Cloud first boot)
if not os.path.isfile(CPP_BINARY) and os.path.isfile(CPP_SOURCE):
    try:
        subprocess.run(
            ["g++", "-O2", "-std=c++17", "-o", CPP_BINARY, CPP_SOURCE],
            check=True, capture_output=True, timeout=30
        )
    except Exception:
        pass  # Python fallback will be used
NODE_COLORS = ["#ef4444","#3b82f6","#10b981","#f59e0b","#8b5cf6","#06b6d4",
               "#ec4899","#a3e635","#fb923c","#facc15","#34d399","#a78bfa","#f472b6","#38bdf8"]
INF = float('inf')

# ──────────────────────────────────────────────────────
# Held-Karp DP  (Python fallback — exact same algorithm)
# ──────────────────────────────────────────────────────
def held_karp_python(dist, n):
    """
    Held-Karp DP TSP Solver (Pure Python).
    dp[mask][i] = min cost to visit exactly cities in 'mask', ending at city i.
    """
    if n == 1:
        return 0.0, [0, 0]

    states = 1 << n
    dp = [[INF] * n for _ in range(states)]
    parent = [[-1] * n for _ in range(states)]

    dp[1][0] = 0.0

    for mask in range(1, states):
        if not (mask & 1):
            continue
        for u in range(n):
            if not (mask & (1 << u)):
                continue
            if dp[mask][u] == INF:
                continue
            for v in range(n):
                if mask & (1 << v):
                    continue
                if dist[u][v] == INF:
                    continue
                new_mask = mask | (1 << v)
                new_cost = dp[mask][u] + dist[u][v]
                if new_cost < dp[new_mask][v]:
                    dp[new_mask][v] = new_cost
                    parent[new_mask][v] = u

    full_mask = states - 1
    best_cost = INF
    last_city = -1

    for u in range(1, n):
        if dp[full_mask][u] == INF:
            continue
        if dist[u][0] == INF:
            continue
        total = dp[full_mask][u] + dist[u][0]
        if total < best_cost:
            best_cost = total
            last_city = u

    if last_city == -1:
        return INF, []

    path = []
    mask = full_mask
    cur = last_city
    while cur != -1:
        path.append(cur)
        prev = parent[mask][cur]
        mask ^= (1 << cur)
        cur = prev

    path.reverse()
    path.append(0)
    return best_cost, path


def euclidean(a, b):
    return math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2)


def build_dist_matrix(locations):
    n = len(locations)
    dist = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                row.append(euclidean(
                    (locations[i]['x'], locations[i]['y']),
                    (locations[j]['x'], locations[j]['y'])
                ))
        dist.append(row)
    return dist


def run_cpp_solver(dist, n):
    """Try C++ solver first, fallback to Python."""
    if not os.path.isfile(CPP_BINARY):
        return None
    try:
        inp = f"{n}\n"
        for row in dist:
            inp += " ".join(f"{v:.6f}" for v in row) + "\n"
        result = subprocess.run([CPP_BINARY], input=inp, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            return None
        lines = result.stdout.strip().split("\n")
        if lines[0] == "NO_ROUTE":
            return None
        cost = float(lines[0])
        path = list(map(int, lines[1].split()))
        return cost, path
    except Exception:
        return None


def optimize(locations):
    n = len(locations)
    dist = build_dist_matrix(locations)

    # Try C++ binary first (faster), else use Python
    cpp_result = run_cpp_solver(dist, n)
    if cpp_result:
        cost, path = cpp_result
        solver_used = "C++ Held-Karp (compiled)"
    else:
        cost, path = held_karp_python(dist, n)
        solver_used = "Python Held-Karp (interpreted)"

    segments = []
    for k in range(len(path) - 1):
        i, j = path[k], path[k+1]
        segments.append({"from": i, "to": j, "distance": round(dist[i][j], 2)})

    return {
        "total_cost": round(cost, 2),
        "path": path,
        "segments": segments,
        "dist": dist,
        "solver": solver_used,
    }


# ──────────────────────────────────────────────────────
#  Plotly Route Chart
# ──────────────────────────────────────────────────────
def make_route_figure(locations, result=None):
    fig = go.Figure()

    # Dark background
    fig.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0d1220",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=True, gridcolor="#1a2a3a", zeroline=False, showticklabels=False, range=[-20, 820]),
        yaxis=dict(showgrid=True, gridcolor="#1a2a3a", zeroline=False, showticklabels=False, range=[-20, 620]),
        height=520,
        showlegend=False,
        hovermode="closest",
    )

    if not locations:
        fig.add_annotation(
            text="Add locations in the sidebar to begin",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="#334155"),
        )
        return fig

    # ── Draw route edges ──
    if result:
        path = result["path"]
        segs = result["segments"]

        # Build continuous x/y arrays for the full tour path
        xs = [locations[idx]['x'] for idx in path]
        ys = [locations[idx]['y'] for idx in path]

        # Glow halo — single wide trace behind the route
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines",
            line=dict(color="rgba(59,130,246,0.18)", width=14),
            hoverinfo="skip",
        ))
        # Main route line — single continuous trace
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="lines",
            line=dict(color="#3b82f6", width=3),
            hoverinfo="skip",
        ))

        # Per-segment: distance labels + directional arrows
        for k, seg in enumerate(segs):
            i, j = seg["from"], seg["to"]
            ax, ay = locations[i]['x'], locations[i]['y']
            bx, by = locations[j]['x'], locations[j]['y']
            mx, my = (ax + bx) / 2, (ay + by) / 2
            ang = math.atan2(by - ay, bx - ax)

            # Distance label mid-segment
            fig.add_annotation(
                x=mx, y=my,
                text=f"<b>{seg['distance']:.1f}</b>",
                showarrow=False,
                font=dict(size=9, color="#f59e0b", family="JetBrains Mono"),
                yshift=10,
                bgcolor="rgba(13,18,32,0.7)",
            )
            # Directional arrow at midpoint
            offset = 14
            fig.add_annotation(
                x=mx + math.cos(ang) * offset,
                y=my + math.sin(ang) * offset,
                ax=mx - math.cos(ang) * offset,
                ay=my - math.sin(ang) * offset,
                xref="x", yref="y", axref="x", ayref="y",
                showarrow=True,
                arrowhead=3, arrowsize=1.4, arrowwidth=2,
                arrowcolor="#60a5fa",
            )
    else:
        # Faint all-edges preview
        for i in range(len(locations)):
            for j in range(i+1, len(locations)):
                fig.add_trace(go.Scatter(
                    x=[locations[i]['x'], locations[j]['x']],
                    y=[locations[i]['y'], locations[j]['y']],
                    mode="lines",
                    line=dict(color="rgba(59,130,246,0.08)", width=1, dash="dot"),
                    hoverinfo="skip",
                ))

    # ── Draw node markers ──
    for idx, loc in enumerate(locations):
        is_depot = idx == 0
        color = "#ef4444" if is_depot else NODE_COLORS[idx % len(NODE_COLORS)]
        label = "⚑" if is_depot else str(idx)
        symbol = "diamond" if is_depot else "circle"

        # Outer glow ring
        fig.add_trace(go.Scatter(
            x=[loc['x']], y=[loc['y']],
            mode="markers",
            marker=dict(
                size=36 if is_depot else 28,
                color=f"rgba({int(color[1:3], 16)},{int(color[3:5], 16)},{int(color[5:7], 16)},0.15)",
                symbol=symbol,
                line=dict(color=color, width=2),
            ),
            hovertemplate=f"<b>{loc['name']}</b><br>x: {loc['x']}, y: {loc['y']}<extra></extra>",
        ))
        # Inner dot
        fig.add_trace(go.Scatter(
            x=[loc['x']], y=[loc['y']],
            mode="markers+text",
            marker=dict(size=18 if is_depot else 14, color=color, symbol=symbol),
            text=label,
            textposition="middle center",
            textfont=dict(size=9, color="white", family="Inter"),
            hoverinfo="skip",
        ))
        # Name tag above
        fig.add_annotation(
            x=loc['x'], y=loc['y'] + (26 if is_depot else 22),
            text=f"<b>{loc['name']}</b>",
            showarrow=False,
            font=dict(size=11, color="#e2e8f0", family="Inter"),
        )

    return fig


# ──────────────────────────────────────────────────────
# Session State Init
# ──────────────────────────────────────────────────────
if "locations" not in st.session_state:
    st.session_state.locations = []
if "result" not in st.session_state:
    st.session_state.result = None
if "optimize_time" not in st.session_state:
    st.session_state.optimize_time = None


# ──────────────────────────────────────────────────────
#  SIDEBAR
# ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:12px 0 20px">
      <div style="font-size:2.4rem;margin-bottom:6px">🗺️</div>
      <div style="font-size:1.2rem;font-weight:800;color:#f1f5f9">RouteIQ</div>
      <div style="font-size:0.75rem;color:#64748b;margin-top:4px">DP Route Optimizer</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # ── Add Location ──
    st.markdown('<div class="sidebar-label">Add Location</div>', unsafe_allow_html=True)

    loc_name = st.text_input("Name", placeholder="e.g. Warehouse A", key="loc_name", label_visibility="collapsed")
    col1, col2 = st.columns(2)
    with col1:
        loc_x = st.number_input("X", min_value=0.0, max_value=800.0, value=100.0, step=10.0, key="loc_x", label_visibility="visible")
    with col2:
        loc_y = st.number_input("Y", min_value=0.0, max_value=600.0, value=100.0, step=10.0, key="loc_y", label_visibility="visible")

    if st.button("＋  Add Location", key="btn_add"):
        locs = st.session_state.locations
        n = len(locs)
        name = loc_name.strip() or ("Depot" if n == 0 else f"Stop {chr(64+n)}")
        locs.append({"name": name, "x": float(loc_x), "y": float(loc_y), "index": n})
        st.session_state.result = None
        st.rerun()

    st.divider()

    # ── Random Demo ──
    st.markdown('<div class="sidebar-label">Quick Demo</div>', unsafe_allow_html=True)

    demo_n = st.slider("Number of stops", 3, 12, 6, key="demo_n")
    if st.button("🎲  Generate Random Tour", key="btn_demo"):
        random.seed(int(time.time()))
        locs = [{"name": "Depot", "x": 400.0, "y": 300.0, "index": 0}]
        for i in range(1, demo_n):
            locs.append({
                "name": f"Stop {chr(64+i)}",
                "x": round(random.uniform(50, 750), 1),
                "y": round(random.uniform(50, 550), 1),
                "index": i,
            })
        st.session_state.locations = locs
        st.session_state.result = None
        st.rerun()

    st.divider()

    # ── Locations List ──
    locs = st.session_state.locations
    if locs:
        st.markdown(f'<div class="sidebar-label">Locations ({len(locs)})</div>', unsafe_allow_html=True)
        to_remove = None
        for i, loc in enumerate(locs):
            col_l, col_r = st.columns([4, 1])
            with col_l:
                tag = "⚑" if i == 0 else str(i)
                color = "#ef4444" if i == 0 else "#60a5fa"
                st.markdown(
                    f'<div style="padding:4px 0;font-size:0.82rem">'
                    f'<span style="color:{color};font-weight:700">{tag}</span>&nbsp; '
                    f'{loc["name"]} <span style="color:#64748b;font-family:monospace;font-size:0.7rem">({int(loc["x"])},{int(loc["y"])})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_r:
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
            st.session_state.result = None
            st.rerun()

    # ── DP Algorithm Info ──
    st.divider()
    st.markdown('<div class="sidebar-label">Algorithm Details</div>', unsafe_allow_html=True)
    n = len(st.session_state.locations)
    states = 2**n if n > 0 else 0
    subproblems = n * states if n > 0 else 0
    cpp_available = os.path.isfile(CPP_BINARY)

    st.markdown(f"""
    <table class="dp-table">
      <tr><td>Algorithm</td><td>Held-Karp DP</td></tr>
      <tr><td>Time</td><td>O(n² · 2ⁿ)</td></tr>
      <tr><td>Space</td><td>O(n · 2ⁿ)</td></tr>
      <tr><td>Nodes (n)</td><td>{n}</td></tr>
      <tr><td>DP States</td><td>{states:,}</td></tr>
      <tr><td>Subproblems</td><td>{subproblems:,}</td></tr>
      <tr><td>C++ Solver</td><td>{"✓ Compiled" if cpp_available else "⚡ Python"}</td></tr>
      <tr><td>Industry</td><td>Logistics / TSP</td></tr>
    </table>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────
#  MAIN CONTENT
# ──────────────────────────────────────────────────────

# ── Hero Header ──
st.markdown("""
<div class="hero-card">
  <div class="hero-icon">🗺️</div>
  <div>
    <div class="hero-title">RouteIQ — Route Optimizer</div>
    <div class="hero-sub">Industry-grade Dynamic Programming solver for the Travelling Salesman Problem</div>
    <div class="badge-row">
      <span class="badge badge-blue">Held-Karp DP</span>
      <span class="badge badge-green">Exact Optimal Solution</span>
      <span class="badge badge-orange">O(n² · 2ⁿ)</span>
      <span class="badge badge-purple">C++ Engine</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


# ── Metrics Row ──
locs = st.session_state.locations
result = st.session_state.result
n = len(locs)

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1:
    st.metric("Locations", n, help="Total stops including depot")
with col_m2:
    st.metric("Total Distance", f"{result['total_cost']:.1f}" if result else "—", help="Optimal tour length")
with col_m3:
    states_val = f"{2**n:,}" if n > 0 else "—"
    st.metric("DP States", states_val, help="Bitmask states computed")
with col_m4:
    st.metric("Solve Time", f"{st.session_state.optimize_time:.3f}s" if st.session_state.optimize_time else "—", help="CPU time for DP solve")

st.markdown("<br>", unsafe_allow_html=True)

# ── Main columns ──
chart_col, info_col = st.columns([2, 1])

with chart_col:
    st.markdown('<div class="section-header">Route Visualization</div>', unsafe_allow_html=True)

    # ── Optimize Button ──
    if n >= 2:
        if st.button(f"✦  Optimize Route  ({n} locations)", key="btn_optimize"):
            with st.spinner("Running Held-Karp DP solver..."):
                t0 = time.perf_counter()
                res = optimize(locs)
                t1 = time.perf_counter()
            st.session_state.result = res
            st.session_state.optimize_time = round(t1 - t0, 4)
            st.rerun()
    else:
        st.info("Add at least 2 locations in the sidebar to optimize.")

    # ── Plotly Chart ──
    fig = make_route_figure(locs, st.session_state.result)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


with info_col:
    # ── Route Steps ──
    st.markdown('<div class="section-header">Optimal Route Steps</div>', unsafe_allow_html=True)

    if result:
        path = result["path"]
        segs = result["segments"]
        solver = result.get("solver", "")
        st.success(f"**Optimal tour found!**  Total: `{result['total_cost']:.2f}` units")
        st.caption(f"Solver: {solver}")

        for step_i, city_idx in enumerate(path):
            loc = locs[city_idx]
            is_depot = step_i == 0 or step_i == len(path) - 1
            color = "#ef4444" if is_depot else "#3b82f6"
            label = "⚑ DEPOT" if is_depot else f"#{step_i}"
            dist_str = ""
            if step_i < len(segs):
                dist_str = f'<span style="float:right;color:#f59e0b;font-family:monospace;font-size:0.75rem">{segs[step_i]["distance"]:.1f}</span>'
            st.markdown(
                f'<div class="route-step-item">'
                f'<span style="color:{color};font-weight:700;font-size:0.78rem;min-width:52px">{label}</span>'
                f'<span style="font-size:0.82rem;flex:1">{loc["name"]}</span>'
                f'{dist_str}'
                f'</div>',
                unsafe_allow_html=True,
            )

        # ── Segments Table ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">Segment Breakdown</div>', unsafe_allow_html=True)
        seg_data = []
        for seg in segs:
            seg_data.append({
                "From": locs[seg["from"]]["name"],
                "To":   locs[seg["to"]]["name"],
                "Dist": seg["distance"],
            })
        df = pd.DataFrame(seg_data)
        st.dataframe(df, use_container_width=True, hide_index=True, height=200)

    else:
        st.markdown("""
        <div style="color:#334155;text-align:center;padding:40px 10px;font-size:0.9rem">
          <div style="font-size:2rem;margin-bottom:12px">⚡</div>
          Run optimization to see<br>the optimal route
        </div>
        """, unsafe_allow_html=True)

    # ── DP Explanation ──
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📖 How Held-Karp DP Works", expanded=False):
        st.markdown("""
**Held-Karp** (1962) is the classic exact DP algorithm for the **Travelling Salesman Problem**.

**Recurrence:**
```
dp[S][i] = min cost to visit all cities in set S, ending at city i
         = min over j in S-{i} of:
             dp[S-{i}][j]  +  dist[j][i]
```

**Bitmask trick:** The set S is encoded as an integer bitmask.  
City `i` ∈ S if bit `i` of the mask is 1.

**Steps:**
1. Start: `dp[{0}][0] = 0`
2. Fill all `2ⁿ × n` subproblems bottom-up
3. Answer: `min over i: dp[all][i] + dist[i][0]`
4. Reconstruct path by tracing parent pointers

**Industry use:** Amazon logistics, FedEx routing, Uber driver assignment, PCB drilling paths
        """)

st.divider()

# ── Bottom: Distance Matrix ──
if locs:
    with st.expander(f"🧮 Distance Matrix  ({n}×{n})", expanded=False):
        dist = build_dist_matrix(locs)
        names = [l["name"] for l in locs]
        df_dist = pd.DataFrame(
            [[round(dist[i][j], 1) for j in range(n)] for i in range(n)],
            index=names, columns=names,
        )
        st.dataframe(df_dist, use_container_width=True)
