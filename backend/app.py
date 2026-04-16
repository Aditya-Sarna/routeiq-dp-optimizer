"""
Route Optimization API
Flask backend that bridges the C++ Held-Karp DP solver with the frontend UI.
"""

import os
import subprocess
import math
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

# Path to compiled C++ binary
CPP_BINARY = os.path.join(os.path.dirname(__file__), "..", "cpp_engine", "route_optimizer")


def haversine(lat1, lon1, lat2, lon2):
    """Calculate real-world distance (km) between two GPS coordinates."""
    R = 6371  # Earth's radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def euclidean(x1, y1, x2, y2):
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


@app.route("/api/optimize", methods=["POST"])
def optimize():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    locations = data.get("locations", [])
    mode = data.get("mode", "euclidean")  # "euclidean" or "haversine"

    if len(locations) < 2:
        return jsonify({"error": "Need at least 2 locations"}), 400
    if len(locations) > 15:
        return jsonify({"error": "Maximum 15 locations supported (NP-hard exact solver)"}), 400

    n = len(locations)

    # Build distance matrix
    dist = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(0.0)
            elif mode == "haversine":
                d = haversine(
                    locations[i]["lat"], locations[i]["lng"],
                    locations[j]["lat"], locations[j]["lng"]
                )
                row.append(d)
            else:
                d = euclidean(
                    locations[i]["x"], locations[i]["y"],
                    locations[j]["x"], locations[j]["y"]
                )
                row.append(d)
        dist.append(row)

    # Format input for C++ solver
    input_str = f"{n}\n"
    for row in dist:
        input_str += " ".join(f"{v:.6f}" for v in row) + "\n"

    # Call C++ solver
    try:
        result = subprocess.run(
            [CPP_BINARY],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            return jsonify({"error": "Solver failed: " + result.stderr}), 500

        lines = result.stdout.strip().split("\n")
        if lines[0] == "NO_ROUTE":
            return jsonify({"error": "No valid route found"}), 400

        total_cost = float(lines[0])
        path_indices = list(map(int, lines[1].split()))

        # Build ordered route with location details
        route = []
        for idx in path_indices:
            loc = dict(locations[idx])
            loc["index"] = idx
            route.append(loc)

        # Build per-segment distances
        segments = []
        for k in range(len(path_indices) - 1):
            i, j = path_indices[k], path_indices[k + 1]
            segments.append({
                "from": i,
                "to": j,
                "distance": round(dist[i][j], 4)
            })

        return jsonify({
            "total_cost": round(total_cost, 4),
            "route": route,
            "segments": segments,
            "path_indices": path_indices,
            "n_locations": n
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Solver timed out"}), 504
    except FileNotFoundError:
        return jsonify({"error": "C++ solver binary not found. Please compile first."}), 500


@app.route("/api/health")
def health():
    cpp_exists = os.path.isfile(CPP_BINARY)
    return jsonify({
        "status": "ok",
        "cpp_solver": "available" if cpp_exists else "missing"
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
