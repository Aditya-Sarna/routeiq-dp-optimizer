# RouteIQ — DP Route Optimizer · PRD

## Original Problem Statement
> https://github.com/Aditya-Sarna/routeiq-dp-optimizer build a world class ui ux modern and stylistically great for this

## User Choices (gathered via ask_human)
- (1a) Clone the repo and rebuild the UI on top of the existing logic
- (2) Algorithm = Rabin-Karp *(actual repo implements Held-Karp DP for TSP — proceeded with the real algorithm)*
- (3b) Interactive map with routes
- (4 a/b) Dark futuristic OR clean minimal — design agent chose **Dark Swiss High-Contrast** (Bloomberg/Linear style) with `#FDE047` algorithmic accent
- No 3rd-party integrations / no auth needed

## Architecture
- **Backend**: FastAPI (`/app/backend/server.py`) wraps the C++ Held-Karp binary (`/app/backend/route_optimizer`) via `subprocess.run`.
- **C++ Engine**: Compiled from upstream `cpp_engine/route_optimizer.cpp` with `g++ -O2 -std=c++17`. Implements Held-Karp DP (O(n²·2ⁿ)).
- **Frontend**: React 19 + framer-motion + iconoir-react. Single-file App with Topbar / left sidebar (Mode + Presets + Nodes ledger) / center canvas (SVG route + DOM crosshair markers) / right sidebar (Solver / Algorithm / Tour ledger) / bottom terminal status bar.
- **Persistence**: MongoDB collection `optimizations` records every run; surfaced via `GET /api/history`.

## API Surface (all under `/api`)
| Method | Route | Purpose |
|---|---|---|
| GET | `/` | Service banner |
| GET | `/health` | Solver health (`cpp_solver: available`) |
| POST | `/optimize` | Body `{ locations[], mode: euclidean|haversine }`. Returns `total_cost`, `route`, `segments`, `path_indices`, `n_locations`, `elapsed_ms`, `states_explored`, `subproblems` |
| GET | `/history` | Last N runs |

## Implemented Features (Iter 1 · 2026-01-29)
- Click-to-drop canvas with crosshair node markers; depot pulses, stops use accent yellow
- Manual XY mode with name + numeric inputs
- 3 presets: `DELHI-NCR · 6`, `MANHATTAN · 8`, `RANDOM · 10` (auto-scaled to canvas)
- Animated optimal tour rendering: stroke-drawing yellow lines, arrowhead markers, per-edge distance badges
- DP telemetry float card: N, 2ⁿ states, n·2ⁿ subproblems, elapsed ms, cost
- Right sidebar: Solver card (engine/status/N/states), Algorithm DP-recurrence snippet, Tour ledger with per-edge Δ
- Terminal-style bottom status bar with blinking AWAIT cursor
- Error toast for invalid inputs / solver failures
- All interactive elements include `data-testid` attributes
- 100 % testing-agent success: 9/9 backend pytest cases + full frontend e2e flows

## Personas
- **Logistics engineer** evaluating exact DP for last-mile clusters (≤15 stops)
- **CS student / interviewer** wanting a beautiful Held-Karp visualization
- **Portfolio reviewer / hiring manager** judging UI craft

## Backlog (P1/P2)
- P1 · Real-map mode (Mapbox / Leaflet) using haversine distances
- P1 · Compare algorithms tab (Held-Karp vs nearest-neighbor vs 2-opt) with side-by-side metrics
- P2 · Save / share runs via short-link URL
- P2 · CSV import for delivery stop lists
- P2 · Cost weighting (time vs distance) and capacity-constrained VRP extension
- P2 · Run history sidebar (already persisted, just needs UI)

## Next Action Items
- Add real-map (Mapbox/Leaflet) mode using haversine
- Add algorithm comparison view
