import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import "@/App.css";
import "./components/leaflet-overrides.css";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import {
  MapPin,
  Plus,
  Xmark,
  Flash,
  PathArrow,
  RefreshDouble,
  CursorPointer,
  EditPencil,
  Cpu,
  WarningTriangle,
  Github,
  ArrowRight,
  Compass,
  Erase,
  Globe,
  ViewGrid,
} from "iconoir-react";
import MapView from "./components/MapView";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// ─────────────────────────── presets ───────────────────────────
const ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";

const PRESETS = {
  "DELHI–NCR · 6": [
    { name: "Depot · Gurugram HQ",   x: 180, y: 480 },
    { name: "Connaught Place",        x: 460, y: 320 },
    { name: "Noida Sector 18",        x: 740, y: 360 },
    { name: "Faridabad Hub",          x: 520, y: 580 },
    { name: "Dwarka",                 x: 240, y: 380 },
    { name: "Ghaziabad",              x: 720, y: 220 },
  ],
  "MANHATTAN · 8": [
    { name: "Depot · DUMBO",          x: 720, y: 540 },
    { name: "Wall Street",            x: 600, y: 580 },
    { name: "SoHo",                   x: 540, y: 460 },
    { name: "Times Square",           x: 460, y: 360 },
    { name: "Central Park",           x: 420, y: 240 },
    { name: "UN Plaza",               x: 580, y: 300 },
    { name: "Chelsea",                x: 380, y: 420 },
    { name: "Harlem",                 x: 340, y: 140 },
  ],
  "RANDOM · 10": null, // generated on demand
};

// Real-world map presets (lat, lng) — used by Map workspace
const MAP_PRESETS = {
  "DELHI–NCR · 6": [
    { name: "Depot · Gurugram",       lat: 28.4595, lng: 77.0266 },
    { name: "Connaught Place",        lat: 28.6315, lng: 77.2167 },
    { name: "Noida Sector 18",        lat: 28.5708, lng: 77.3260 },
    { name: "Faridabad Hub",          lat: 28.4089, lng: 77.3178 },
    { name: "Dwarka",                 lat: 28.5921, lng: 77.0460 },
    { name: "Ghaziabad",              lat: 28.6692, lng: 77.4538 },
  ],
  "MANHATTAN · 8": [
    { name: "Depot · DUMBO",          lat: 40.7033, lng: -73.9881 },
    { name: "Wall Street",            lat: 40.7074, lng: -74.0113 },
    { name: "SoHo",                   lat: 40.7233, lng: -74.0030 },
    { name: "Times Square",           lat: 40.7580, lng: -73.9855 },
    { name: "Central Park",           lat: 40.7829, lng: -73.9654 },
    { name: "UN Plaza",               lat: 40.7489, lng: -73.9680 },
    { name: "Chelsea",                lat: 40.7466, lng: -74.0011 },
    { name: "Harlem",                 lat: 40.8116, lng: -73.9465 },
  ],
  "BENGALURU · 7": [
    { name: "Depot · Whitefield",     lat: 12.9698, lng: 77.7500 },
    { name: "MG Road",                lat: 12.9759, lng: 77.6063 },
    { name: "Indiranagar",            lat: 12.9784, lng: 77.6408 },
    { name: "Koramangala",            lat: 12.9352, lng: 77.6245 },
    { name: "Electronic City",        lat: 12.8452, lng: 77.6602 },
    { name: "HSR Layout",             lat: 12.9116, lng: 77.6473 },
    { name: "Hebbal",                 lat: 13.0354, lng: 77.5970 },
  ],
  "LONDON · 8": [
    { name: "Depot · Canary Wharf",   lat: 51.5054, lng: -0.0235 },
    { name: "King's Cross",           lat: 51.5308, lng: -0.1238 },
    { name: "Westminster",            lat: 51.4995, lng: -0.1248 },
    { name: "Tower Bridge",           lat: 51.5055, lng: -0.0754 },
    { name: "Shoreditch",             lat: 51.5237, lng: -0.0782 },
    { name: "Camden",                 lat: 51.5390, lng: -0.1426 },
    { name: "Greenwich",              lat: 51.4826, lng: -0.0077 },
    { name: "Kensington",             lat: 51.4988, lng: -0.1749 },
  ],
  "RANDOM · 10": null,
};

// ─────────────────────────── Held-Karp DP visual snippet ───────────────────────────
const SOLVER_SNIPPET = `// HELD–KARP · O(n² · 2ⁿ)
dp[1<<0][0] = 0;
for (mask = 1; mask < 1<<n; ++mask)
  for (u = 0; u < n; ++u)
    if (mask & 1<<u && dp[mask][u] < ∞)
      for (v = 0; v < n; ++v)
        if (!(mask & 1<<v))
          dp[mask|1<<v][v] = min(
            dp[mask|1<<v][v],
            dp[mask][u] + dist[u][v]);`;

// ─────────────────────────── App ───────────────────────────
function App() {
  const [workspace, setWorkspace] = useState("canvas"); // canvas | map
  const [locations, setLocations] = useState([]);
  const [mode, setMode] = useState("grid"); // grid | manual (canvas mode only)
  const [optimizedPath, setOptimizedPath] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [solverHealth, setSolverHealth] = useState("unknown");
  const [hoveredIdx, setHoveredIdx] = useState(null);
  const [manualName, setManualName] = useState("");
  const [manualX, setManualX] = useState("");
  const [manualY, setManualY] = useState("");
  const [manualLat, setManualLat] = useState("");
  const [manualLng, setManualLng] = useState("");

  const canvasWrapperRef = useRef(null);
  const [size, setSize] = useState({ w: 800, h: 600 });

  // ── health ping ──
  useEffect(() => {
    axios
      .get(`${API}/health`)
      .then((r) => setSolverHealth(r.data.cpp_solver))
      .catch(() => setSolverHealth("offline"));
  }, []);

  // ── canvas size ──
  useEffect(() => {
    const update = () => {
      const el = canvasWrapperRef.current;
      if (!el) return;
      setSize({ w: el.clientWidth, h: el.clientHeight });
    };
    update();
    const ro = new ResizeObserver(update);
    if (canvasWrapperRef.current) ro.observe(canvasWrapperRef.current);
    return () => ro.disconnect();
  }, []);

  // ── helpers ──
  const showError = (msg) => {
    setError(msg);
    setTimeout(() => setError(null), 3500);
  };

  // Synchronous workspace switcher — clears incompatible state in the same render
  const switchWorkspace = useCallback((next) => {
    if (next === workspace) return;
    setLocations([]);
    setOptimizedPath(null);
    setError(null);
    setMode("grid");
    setWorkspace(next);
  }, [workspace]);

  const addLocation = useCallback(
    (a, b, customName = null) => {
      // a, b mean (x, y) for canvas, (lat, lng) for map
      setLocations((prev) => {
        if (prev.length >= 15) {
          showError("Max 15 locations · Held-Karp is NP-hard exact");
          return prev;
        }
        const idx = prev.length;
        const name =
          customName || (idx === 0 ? "Depot" : `Stop ${ALPHABET[idx - 1]}`);
        setOptimizedPath(null);
        if (workspace === "map") {
          return [...prev, { lat: a, lng: b, name, index: idx }];
        }
        return [...prev, { x: a, y: b, name, index: idx }];
      });
    },
    [workspace]
  );

  const removeLocation = (idx) => {
    setLocations((prev) =>
      prev
        .filter((_, i) => i !== idx)
        .map((l, i) => ({
          ...l,
          index: i,
          name: i === 0 && (l.name.startsWith("Stop") || l.name === "Depot") ? "Depot" : l.name,
        }))
    );
    setOptimizedPath(null);
  };

  const clearAll = () => {
    setLocations([]);
    setOptimizedPath(null);
    setError(null);
  };

  const loadPreset = (key) => {
    if (workspace === "map") {
      let data = MAP_PRESETS[key];
      if (!data) {
        // RANDOM · 10 — random points in a US-spanning bbox
        data = [];
        const cx = 39.5, cy = -98.35; // continental US center-ish
        for (let i = 0; i < 10; i++) {
          data.push({
            name: i === 0 ? "Depot · Origin" : `Stop ${ALPHABET[i - 1]}`,
            lat: cx + (Math.random() - 0.5) * 14,
            lng: cy + (Math.random() - 0.5) * 40,
          });
        }
      }
      setLocations(data.map((d, i) => ({ ...d, index: i })));
      setOptimizedPath(null);
      setError(null);
      return;
    }

    let data = PRESETS[key];
    if (!data) {
      // RANDOM · 10
      data = [];
      const margin = 60;
      for (let i = 0; i < 10; i++) {
        data.push({
          name: i === 0 ? "Depot · Origin" : `Stop ${ALPHABET[i - 1]}`,
          x: margin + Math.random() * (size.w - margin * 2),
          y: margin + Math.random() * (size.h - margin * 2),
        });
      }
    }
    // Scale presets to current canvas dimensions
    const xs = data.map((d) => d.x);
    const ys = data.map((d) => d.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs);
    const minY = Math.min(...ys), maxY = Math.max(...ys);
    const padW = 80, padH = 80;
    const targetW = Math.max(200, size.w - padW * 2);
    const targetH = Math.max(200, size.h - padH * 2);
    const sX = (maxX - minX) > 0 ? targetW / (maxX - minX) : 1;
    const sY = (maxY - minY) > 0 ? targetH / (maxY - minY) : 1;
    const scale = Math.min(sX, sY);
    const placed = data.map((d, i) => ({
      x: padW + (d.x - minX) * scale,
      y: padH + (d.y - minY) * scale,
      name: d.name,
      index: i,
    }));
    setLocations(placed);
    setOptimizedPath(null);
    setError(null);
  };

  const onCanvasClick = (e) => {
    if (mode !== "grid") return;
    const rect = canvasWrapperRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    addLocation(x, y, null);
  };

  const onAddManual = () => {
    if (workspace === "map") {
      const lat = parseFloat(manualLat);
      const lng = parseFloat(manualLng);
      if (Number.isNaN(lat) || Number.isNaN(lng)) {
        showError("Enter valid latitude and longitude");
        return;
      }
      if (lat < -90 || lat > 90 || lng < -180 || lng > 180) {
        showError("Lat must be in [-90, 90], Lng in [-180, 180]");
        return;
      }
      addLocation(lat, lng, manualName.trim() || null);
      setManualName("");
      setManualLat("");
      setManualLng("");
      return;
    }
    const x = parseFloat(manualX);
    const y = parseFloat(manualY);
    if (Number.isNaN(x) || Number.isNaN(y)) {
      showError("Enter valid X and Y coordinates");
      return;
    }
    addLocation(
      Math.max(20, Math.min(size.w - 20, x)),
      Math.max(20, Math.min(size.h - 20, y)),
      manualName.trim() || null
    );
    setManualName("");
    setManualX("");
    setManualY("");
  };

  const optimizeRoute = async () => {
    if (locations.length < 2) return;
    setLoading(true);
    setError(null);
    try {
      const payload =
        workspace === "map"
          ? {
              mode: "haversine",
              locations: locations.map((l) => ({
                x: 0,
                y: 0,
                lat: l.lat,
                lng: l.lng,
                name: l.name,
              })),
            }
          : {
              mode: "euclidean",
              locations: locations.map((l) => ({
                x: l.x,
                y: l.y,
                name: l.name,
              })),
            };
      const { data } = await axios.post(`${API}/optimize`, payload);
      setOptimizedPath(data);
    } catch (err) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        "Could not reach optimizer service.";
      showError(typeof msg === "string" ? msg : "Optimization failed");
    } finally {
      setLoading(false);
    }
  };

  // ── derived ──
  const dpStates = locations.length > 0 ? Math.pow(2, locations.length) : 0;
  const subproblems = locations.length > 0 ? locations.length * dpStates : 0;
  const canOptimize = locations.length >= 2 && !loading;

  return (
    <div className="App font-body bg-[#050505] text-white">
      <Topbar solverHealth={solverHealth} />

      <div
        className="grid"
        style={{
          gridTemplateColumns: "minmax(360px, 380px) 1fr minmax(280px, 320px)",
          height: "calc(100vh - 56px - 32px)",
        }}
      >
        {/* ═════════════ LEFT: CONTROLS ═════════════ */}
        <aside
          className="border-r border-[#27272A] bg-[#0F0F11] overflow-y-auto"
          data-testid="control-sidebar"
        >
          <SectionHeader index="01" title="Mode" subtitle="How to add nodes" />
          <div className="px-5 pb-5 grid grid-cols-2 gap-2">
            <ModeButton
              active={mode === "grid"}
              onClick={() => setMode("grid")}
              icon={<CursorPointer width={16} height={16} strokeWidth={1.6} />}
              label="Click-to-Drop"
              hint="Click on the canvas"
              testid="mode-toggle-grid"
            />
            <ModeButton
              active={mode === "manual"}
              onClick={() => setMode("manual")}
              icon={<EditPencil width={16} height={16} strokeWidth={1.6} />}
              label="Manual XY"
              hint="Type coordinates"
              testid="mode-toggle-manual"
            />
          </div>

          {mode === "manual" && (
            <div className="px-5 pb-5">
              <div className="border border-[#27272A] bg-[#050505] p-4">
                <Label>{workspace === "map" ? "Add Location · LAT/LNG" : "Add Location"}</Label>
                <input
                  data-testid="manual-name-input"
                  value={manualName}
                  onChange={(e) => setManualName(e.target.value)}
                  placeholder="e.g. Warehouse · Yard 4"
                  className="w-full bg-[#0F0F11] border border-[#27272A] focus:border-[#FDE047] px-3 py-2 text-sm font-mono placeholder:text-neutral-700 mb-2"
                />
                <div className="grid grid-cols-2 gap-2 mb-3">
                  {workspace === "map" ? (
                    <>
                      <input
                        data-testid="manual-lat-input"
                        value={manualLat}
                        onChange={(e) => setManualLat(e.target.value)}
                        placeholder="Lat"
                        type="number"
                        step="0.0001"
                        className="w-full bg-[#0F0F11] border border-[#27272A] focus:border-[#FDE047] px-3 py-2 text-sm font-mono placeholder:text-neutral-700"
                      />
                      <input
                        data-testid="manual-lng-input"
                        value={manualLng}
                        onChange={(e) => setManualLng(e.target.value)}
                        placeholder="Lng"
                        type="number"
                        step="0.0001"
                        className="w-full bg-[#0F0F11] border border-[#27272A] focus:border-[#FDE047] px-3 py-2 text-sm font-mono placeholder:text-neutral-700"
                      />
                    </>
                  ) : (
                    <>
                      <input
                        data-testid="manual-x-input"
                        value={manualX}
                        onChange={(e) => setManualX(e.target.value)}
                        placeholder="X"
                        type="number"
                        className="w-full bg-[#0F0F11] border border-[#27272A] focus:border-[#FDE047] px-3 py-2 text-sm font-mono placeholder:text-neutral-700"
                      />
                      <input
                        data-testid="manual-y-input"
                        value={manualY}
                        onChange={(e) => setManualY(e.target.value)}
                        placeholder="Y"
                        type="number"
                        className="w-full bg-[#0F0F11] border border-[#27272A] focus:border-[#FDE047] px-3 py-2 text-sm font-mono placeholder:text-neutral-700"
                      />
                    </>
                  )}
                </div>
                <button
                  data-testid="add-manual-location-btn"
                  onClick={onAddManual}
                  className="w-full bg-white text-black font-bold tracking-[0.18em] uppercase text-[11px] py-2.5 hover:bg-neutral-200 transition-colors flex items-center justify-center gap-2"
                >
                  <Plus width={14} height={14} strokeWidth={2.2} />
                  Add Node
                </button>
              </div>
            </div>
          )}

          <Divider />

          <SectionHeader index="02" title="Presets" subtitle={workspace === "map" ? "Real cities · lat/lng" : "Hydrate the canvas instantly"} />
          <div className="px-5 pb-5 flex flex-col gap-2">
            {Object.keys(workspace === "map" ? MAP_PRESETS : PRESETS).map((k) => (
              <button
                key={k}
                data-testid={`preset-${k.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
                onClick={() => loadPreset(k)}
                className="group flex items-center justify-between border border-[#27272A] hover:border-[#FDE047] bg-[#050505] px-3 py-2.5 text-[12px] font-mono uppercase tracking-[0.12em] text-neutral-400 hover:text-white transition-colors"
              >
                <span>{k}</span>
                <ArrowRight
                  width={14}
                  height={14}
                  strokeWidth={1.6}
                  className="opacity-50 group-hover:opacity-100 group-hover:translate-x-0.5 transition-transform"
                />
              </button>
            ))}
          </div>

          <Divider />

          <SectionHeader
            index="03"
            title="Nodes"
            subtitle={`${locations.length}/15 ledger entries`}
            right={
              locations.length > 0 ? (
                <button
                  data-testid="clear-canvas-button"
                  onClick={clearAll}
                  className="text-[10px] uppercase tracking-[0.2em] font-bold text-neutral-500 hover:text-[#EF4444] flex items-center gap-1.5 transition-colors"
                >
                  <Erase width={12} height={12} strokeWidth={1.8} /> Clear
                </button>
              ) : null
            }
          />
          <div className="px-5 pb-6">
            {locations.length === 0 ? (
              <EmptyLedger />
            ) : (
              <div className="border border-[#27272A] bg-[#050505]">
                {locations.map((loc, i) => (
                  <NodeRow
                    key={i}
                    idx={i}
                    loc={loc}
                    onRemove={() => removeLocation(i)}
                    onHover={setHoveredIdx}
                  />
                ))}
              </div>
            )}
          </div>
        </aside>

        {/* ═════════════ CENTER: CANVAS ═════════════ */}
        <main className="relative flex flex-col bg-[#0A0A0C]">
          {/* canvas toolbar */}
          <div className="h-11 border-b border-[#27272A] flex items-center px-5 gap-4 bg-[#0F0F11] shrink-0">
            <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.2em] text-neutral-400">
              {workspace === "map" ? (
                <>
                  <Globe width={14} height={14} strokeWidth={1.6} className="text-[#FDE047]" />
                  WORLD MAP · LAT/LNG · HAVERSINE
                </>
              ) : (
                <>
                  <Compass width={14} height={14} strokeWidth={1.6} className="text-[#FDE047]" />
                  CANVAS · WORLD-SPACE
                </>
              )}
            </div>
            <div className="flex-1" />
            {/* Workspace toggle pill */}
            <div className="flex items-stretch border border-[#27272A] bg-[#050505]" data-testid="workspace-toggle">
              <button
                data-testid="workspace-canvas-btn"
                onClick={() => switchWorkspace("canvas")}
                className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-[0.18em] transition-colors flex items-center gap-1.5 ${
                  workspace === "canvas"
                    ? "bg-white text-black"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <ViewGrid width={12} height={12} strokeWidth={1.8} /> Canvas
              </button>
              <button
                data-testid="workspace-map-btn"
                onClick={() => switchWorkspace("map")}
                className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-[0.18em] transition-colors flex items-center gap-1.5 ${
                  workspace === "map"
                    ? "bg-[#FDE047] text-black"
                    : "text-neutral-400 hover:text-white"
                }`}
              >
                <Globe width={12} height={12} strokeWidth={1.8} /> World Map
              </button>
            </div>
            <span className="h-3 w-px bg-[#27272A]" />
            <span className="text-[10px] font-mono uppercase tracking-[0.16em] text-neutral-500">
              {workspace === "map"
                ? mode === "manual"
                  ? "MANUAL LAT/LNG"
                  : "CLICK MAP TO DROP"
                : mode === "grid"
                ? "CLICK ANYWHERE TO DROP"
                : "MANUAL ENTRY MODE"}
            </span>
          </div>

          <div
            ref={canvasWrapperRef}
            onClick={workspace === "canvas" ? onCanvasClick : undefined}
            className={`relative flex-1 ${
              workspace === "canvas"
                ? `dot-grid ${mode === "grid" ? "cursor-crosshair" : "cursor-default"}`
                : "bg-[#0A0A0C]"
            }`}
            data-testid="route-canvas"
          >
            {workspace === "map" ? (
              <>
                <MapView
                  locations={locations}
                  optimizedPath={optimizedPath}
                  onAdd={(lat, lng) => addLocation(lat, lng, null)}
                  onHover={setHoveredIdx}
                  hoveredIdx={hoveredIdx}
                  enableClick={mode === "grid"}
                />
                {locations.length === 0 && <MapEmptyHint />}
                <AlgorithmFloatingCard
                  n={locations.length}
                  states={dpStates}
                  subs={subproblems}
                  elapsed={optimizedPath?.elapsed_ms}
                  cost={optimizedPath?.total_cost}
                  unit="km"
                />
              </>
            ) : (
              <>
                {/* Crosshair frame markers */}
                <CornerMarks />

                {/* SVG Routes */}
                <RouteSVG
                  locations={locations}
                  optimizedPath={optimizedPath}
                  hoveredIdx={hoveredIdx}
                  size={size}
                />

                {/* Nodes (DOM, on top of SVG) */}
                {locations.map((loc, i) => (
                  <NodeMarker
                    key={i}
                    idx={i}
                    loc={loc}
                    onHover={setHoveredIdx}
                    hovered={hoveredIdx === i}
                  />
                ))}

                {/* Empty state */}
                {locations.length === 0 && <CanvasEmptyState mode={mode} />}

                {/* Floating algorithm card */}
                <AlgorithmFloatingCard
                  n={locations.length}
                  states={dpStates}
                  subs={subproblems}
                  elapsed={optimizedPath?.elapsed_ms}
                  cost={optimizedPath?.total_cost}
                />
              </>
            )}
          </div>

          {/* Bottom action bar */}
          <div className="border-t border-[#27272A] bg-[#0F0F11] px-5 py-3 flex items-center gap-3 shrink-0">
            <button
              data-testid="optimize-route-button"
              onClick={optimizeRoute}
              disabled={!canOptimize}
              className={`group relative px-6 py-3 font-bold uppercase tracking-[0.2em] text-[11px] flex items-center gap-3 transition-all
                ${
                  canOptimize
                    ? "bg-[#FDE047] text-black hover:bg-[#FEF08A] shadow-[0_0_20px_rgba(253,224,71,0.25)] hover:shadow-[0_0_30px_rgba(253,224,71,0.45)]"
                    : "bg-[#18181B] text-neutral-600 cursor-not-allowed"
                }`}
            >
              {loading ? (
                <>
                  <Spinner /> COMPUTING DP TABLE…
                </>
              ) : (
                <>
                  <Flash width={14} height={14} strokeWidth={2.4} />
                  {optimizedPath ? "RE-OPTIMIZE" : "RUN HELD-KARP"}
                  <span className="font-mono opacity-70 normal-case tracking-tight ml-1">
                    O(n²·2ⁿ)
                  </span>
                </>
              )}
            </button>
            <div className="flex-1" />
            <Stat label="Nodes" value={locations.length} />
            <span className="h-6 w-px bg-[#27272A]" />
            <Stat label="DP States" value={dpStates ? dpStates.toLocaleString() : "—"} mono />
            <span className="h-6 w-px bg-[#27272A]" />
            <Stat
              label="Optimal Cost"
              value={
                optimizedPath
                  ? `${optimizedPath.total_cost.toFixed(2)}${
                      workspace === "map" ? " km" : ""
                    }`
                  : "—"
              }
              mono
              accent={!!optimizedPath}
            />
          </div>
        </main>

        {/* ═════════════ RIGHT: RESULTS / TELEMETRY ═════════════ */}
        <aside
          className="border-l border-[#27272A] bg-[#0F0F11] overflow-y-auto"
          data-testid="results-sidebar"
        >
          <SectionHeader index="04" title="Solver" subtitle="Held-Karp · exact DP" />
          <div className="px-5 pb-5">
            <SolverCard
              cppHealth={solverHealth}
              n={locations.length}
              states={dpStates}
              subs={subproblems}
              elapsed={optimizedPath?.elapsed_ms}
            />
          </div>

          <Divider />

          <SectionHeader index="05" title="Algorithm" subtitle="The DP recurrence" />
          <div className="px-5 pb-5">
            <pre
              className="font-mono text-[10px] leading-relaxed text-neutral-400 bg-[#050505] border border-[#27272A] p-3 overflow-x-auto whitespace-pre"
              data-testid="algorithm-snippet"
            >
{SOLVER_SNIPPET}
            </pre>
            <p className="text-[11px] text-neutral-500 mt-3 leading-relaxed">
              Used in production by{" "}
              <span className="text-white font-semibold">Amazon</span>,{" "}
              <span className="text-white font-semibold">FedEx</span>, and{" "}
              <span className="text-white font-semibold">UPS</span> for last-mile
              delivery routing on small clusters.
            </p>
          </div>

          <Divider />

          <SectionHeader
            index="06"
            title="Tour"
            subtitle={optimizedPath ? "Optimal path · ledger" : "No tour computed"}
          />
          <div className="px-5 pb-8">
            {optimizedPath ? (
              <RouteLedger data={optimizedPath} locations={locations} unit={workspace === "map" ? "km" : ""} />
            ) : (
              <div className="border border-dashed border-[#27272A] p-5 text-[11px] text-neutral-500 leading-relaxed">
                Add at least <span className="font-mono text-white">2</span> nodes
                and press <span className="font-mono text-[#FDE047]">RUN HELD-KARP</span>{" "}
                to compute the optimal tour and per-edge distances.
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Bottom status bar — terminal style */}
      <BottomStatus
        n={locations.length}
        cost={optimizedPath?.total_cost}
        cppHealth={solverHealth}
        loading={loading}
        workspace={workspace}
      />

      {/* Error toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            className="fixed bottom-12 left-1/2 -translate-x-1/2 z-50 bg-[#050505] border border-[#EF4444]/60 px-4 py-3 flex items-center gap-3 shadow-2xl"
            data-testid="error-toast"
          >
            <WarningTriangle
              width={18}
              height={18}
              strokeWidth={1.8}
              className="text-[#EF4444]"
            />
            <span className="font-mono text-xs text-[#FCA5A5]">{error}</span>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ═════════════════════════ Components ═════════════════════════

function Topbar({ solverHealth }) {
  const ok = solverHealth === "available";
  return (
    <header className="h-14 border-b border-[#27272A] bg-[#050505] flex items-center px-6 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-[#FDE047] flex items-center justify-center">
          <PathArrow width={16} height={16} strokeWidth={2.4} className="text-black" />
        </div>
        <div>
          <div className="font-display font-black text-[15px] tracking-[-0.04em] leading-none">
            ROUTE<span className="text-[#FDE047]">IQ</span>
          </div>
          <div className="text-[9px] font-mono uppercase tracking-[0.18em] text-neutral-500 mt-0.5">
            HELD-KARP · DP · O(n²·2ⁿ)
          </div>
        </div>
      </div>

      <nav className="ml-10 hidden md:flex items-center gap-7 text-[11px] font-mono uppercase tracking-[0.2em] text-neutral-500">
        <span className="text-white border-b border-[#FDE047] pb-1">Optimizer</span>
        <span className="hover:text-white transition-colors cursor-default">Algorithm</span>
        <span className="hover:text-white transition-colors cursor-default">Telemetry</span>
        <span className="hover:text-white transition-colors cursor-default">Docs</span>
      </nav>

      <div className="flex-1" />

      <div className="hidden md:flex items-center gap-3 mr-5">
        <div className="flex items-center gap-2 px-3 py-1.5 border border-[#27272A] text-[10px] font-mono uppercase tracking-[0.18em]">
          <span
            className={`w-1.5 h-1.5 ${ok ? "bg-[#22C55E]" : "bg-[#EF4444]"} rounded-full`}
            style={{
              animation: ok ? "accent-pulse 2s ease-in-out infinite" : "none",
            }}
          />
          <span className="text-neutral-400">
            C++ SOLVER · <span className={ok ? "text-[#22C55E]" : "text-[#EF4444]"}>
              {ok ? "READY" : (solverHealth || "BOOT").toUpperCase()}
            </span>
          </span>
        </div>
      </div>

      <a
        href="https://github.com/Aditya-Sarna/routeiq-dp-optimizer"
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-2 px-3 py-1.5 border border-[#27272A] hover:border-white text-[10px] font-mono uppercase tracking-[0.2em] text-neutral-400 hover:text-white transition-colors"
        data-testid="github-link"
      >
        <Github width={12} height={12} strokeWidth={1.8} />
        Source
      </a>
    </header>
  );
}

function SectionHeader({ index, title, subtitle, right }) {
  return (
    <div className="px-5 pt-6 pb-4 flex items-end justify-between gap-3">
      <div>
        <div className="text-[10px] font-mono text-[#FDE047] tracking-[0.24em] mb-1">
          /{index}
        </div>
        <div className="font-display font-black text-[20px] tracking-tight leading-none">
          {title}
        </div>
        {subtitle && (
          <div className="text-[11px] font-mono uppercase tracking-[0.14em] text-neutral-500 mt-1.5">
            {subtitle}
          </div>
        )}
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  );
}

function Divider() {
  return <div className="h-px bg-[#27272A] mx-5" />;
}

function Label({ children }) {
  return (
    <div className="text-[9px] font-mono uppercase tracking-[0.22em] text-neutral-500 mb-2">
      {children}
    </div>
  );
}

function ModeButton({ active, onClick, icon, label, hint, testid }) {
  return (
    <button
      onClick={onClick}
      data-testid={testid}
      className={`text-left p-3 border transition-colors ${
        active
          ? "border-white bg-white text-black"
          : "border-[#27272A] text-neutral-300 hover:border-white hover:text-white bg-[#050505]"
      }`}
    >
      <div className={`flex items-center gap-2 mb-1.5 ${active ? "text-black" : "text-[#FDE047]"}`}>
        {icon}
        <span className="text-[10px] font-mono uppercase tracking-[0.2em]">
          {active ? "ACTIVE" : "USE"}
        </span>
      </div>
      <div className="font-bold text-[13px] leading-tight">{label}</div>
      <div className={`text-[10px] font-mono mt-0.5 ${active ? "text-black/60" : "text-neutral-500"}`}>
        {hint}
      </div>
    </button>
  );
}

function NodeRow({ idx, loc, onRemove, onHover }) {
  const isDepot = idx === 0;
  const coordText =
    typeof loc.lat === "number"
      ? `${loc.lat.toFixed(4)}, ${loc.lng.toFixed(4)}`
      : `x:${Math.round(loc.x)} · y:${Math.round(loc.y)}`;
  return (
    <div
      onMouseEnter={() => onHover(idx)}
      onMouseLeave={() => onHover(null)}
      className="flex items-center gap-3 px-3 py-2.5 border-b last:border-b-0 border-[#1A1A1D] hover:bg-[#0F0F11] transition-colors group"
      data-testid={`location-list-item-${idx}`}
    >
      <div className="text-[10px] font-mono text-neutral-600 w-5 shrink-0">
        {String(idx).padStart(2, "0")}
      </div>
      <div
        className={`w-3 h-3 shrink-0 ${
          isDepot ? "bg-white" : "bg-[#FDE047]"
        }`}
        style={isDepot ? { boxShadow: "0 0 8px rgba(255,255,255,0.5)" } : {}}
      />
      <div className="flex-1 min-w-0">
        <div className="text-[12px] truncate font-medium">{loc.name}</div>
        <div className="text-[10px] font-mono text-neutral-500 mt-0.5">
          {coordText}
        </div>
      </div>
      <button
        onClick={onRemove}
        data-testid={`remove-node-button-${idx}`}
        className="opacity-50 hover:opacity-100 text-neutral-500 hover:text-[#EF4444] transition-colors p-1"
      >
        <Xmark width={14} height={14} strokeWidth={1.8} />
      </button>
    </div>
  );
}

function EmptyLedger() {
  return (
    <div className="border border-dashed border-[#27272A] py-8 px-4 text-center">
      <MapPin
        width={20}
        height={20}
        strokeWidth={1.4}
        className="mx-auto text-neutral-600 mb-2"
      />
      <div className="text-[11px] font-mono uppercase tracking-[0.18em] text-neutral-500">
        LEDGER EMPTY
      </div>
      <div className="text-[10px] font-mono text-neutral-600 mt-1">
        Drop nodes on the canvas →
      </div>
    </div>
  );
}

function NodeMarker({ idx, loc, onHover, hovered }) {
  const isDepot = idx === 0;
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.25, type: "spring", damping: 14 }}
      onMouseEnter={() => onHover(idx)}
      onMouseLeave={() => onHover(null)}
      onClick={(e) => e.stopPropagation()}
      className="absolute z-20 pointer-events-auto"
      style={{
        left: loc.x,
        top: loc.y,
        transform: "translate(-50%, -50%)",
      }}
      data-testid={`canvas-node-${idx}`}
    >
      {/* Outer crosshair */}
      <div
        className="absolute"
        style={{
          left: -28,
          top: -28,
          width: 56,
          height: 56,
          pointerEvents: "none",
        }}
      >
        <svg width="56" height="56" viewBox="0 0 56 56">
          <line
            x1="28" y1="0" x2="28" y2="14"
            stroke={isDepot ? "#FFFFFF" : "#FDE047"}
            strokeWidth="1"
            opacity={hovered ? 0.9 : 0.4}
          />
          <line
            x1="28" y1="42" x2="28" y2="56"
            stroke={isDepot ? "#FFFFFF" : "#FDE047"}
            strokeWidth="1"
            opacity={hovered ? 0.9 : 0.4}
          />
          <line
            x1="0" y1="28" x2="14" y2="28"
            stroke={isDepot ? "#FFFFFF" : "#FDE047"}
            strokeWidth="1"
            opacity={hovered ? 0.9 : 0.4}
          />
          <line
            x1="42" y1="28" x2="56" y2="28"
            stroke={isDepot ? "#FFFFFF" : "#FDE047"}
            strokeWidth="1"
            opacity={hovered ? 0.9 : 0.4}
          />
        </svg>
      </div>

      {/* Marker */}
      <div
        className={`w-4 h-4 ${
          isDepot ? "bg-white" : "bg-[#FDE047]"
        } border border-black flex items-center justify-center relative`}
        style={{
          animation: isDepot
            ? "depot-pulse 2.2s ease-in-out infinite"
            : hovered
            ? "accent-pulse 1.4s ease-in-out infinite"
            : "none",
        }}
      >
        <span
          className={`font-mono text-[8px] font-bold ${
            isDepot ? "text-black" : "text-black"
          }`}
        >
          {isDepot ? "★" : idx}
        </span>
      </div>

      {/* Label badge */}
      <div
        className={`absolute left-1/2 -translate-x-1/2 mt-2 whitespace-nowrap pointer-events-none transition-opacity ${
          hovered ? "opacity-100" : "opacity-70"
        }`}
        style={{ top: 12 }}
      >
        <div
          className={`font-mono text-[9px] uppercase tracking-[0.14em] px-1.5 py-0.5 ${
            isDepot
              ? "bg-white text-black"
              : "bg-[#050505] text-[#FDE047] border border-[#27272A]"
          }`}
        >
          {isDepot ? "DEPOT" : `${ALPHABET[idx - 1]} · ${loc.name.slice(0, 14)}`}
        </div>
      </div>
    </motion.div>
  );
}

function CornerMarks() {
  const markStyle = "absolute w-3 h-3 border-[#27272A]";
  return (
    <>
      <div className={`${markStyle} top-3 left-3 border-t border-l`} />
      <div className={`${markStyle} top-3 right-3 border-t border-r`} />
      <div className={`${markStyle} bottom-3 left-3 border-b border-l`} />
      <div className={`${markStyle} bottom-3 right-3 border-b border-r`} />
    </>
  );
}

function MapEmptyHint() {
  return (
    <div className="absolute top-4 left-4 z-30 max-w-[300px] bg-black/85 backdrop-blur-md border border-[#27272A] p-4 pointer-events-none">
      <div className="font-mono text-[10px] uppercase tracking-[0.24em] text-[#FDE047] mb-2">
        // CLICK ANY POINT ON THE MAP
      </div>
      <div className="font-display font-black text-[18px] tracking-[-0.03em] leading-tight text-white">
        First click drops the <span className="text-[#FDE047]">depot</span>.
        <br />Then drop your <span className="text-neutral-400">delivery stops</span>.
      </div>
      <p className="font-mono text-[10px] text-neutral-500 mt-3 leading-relaxed">
        Distances use the Haversine formula on real lat/lng — same Held-Karp DP, world-scale.
      </p>
    </div>
  );
}

function CanvasEmptyState({ mode }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center pointer-events-none select-none">
      <div className="text-center max-w-md px-8">
        <div className="font-mono text-[10px] uppercase tracking-[0.3em] text-[#FDE047] mb-3">
          // EMPTY · WAITING FOR INPUT
        </div>
        <div className="font-display font-black text-[44px] tracking-[-0.04em] leading-[0.95] text-white">
          Drop the <span className="text-[#FDE047]">depot</span>.
          <br />
          Drop the <span className="text-neutral-400">stops</span>.
          <br />
          Solve the <span className="underline decoration-[#FDE047] decoration-2 underline-offset-4">tour</span>.
        </div>
        <p className="font-mono text-[11px] text-neutral-500 mt-5 leading-relaxed tracking-wide">
          {mode === "grid"
            ? "Click anywhere on this grid. The first pin becomes the depot · the rest become delivery stops. Held-Karp returns the exact optimal tour."
            : "Switch to Click-to-Drop mode, or enter coordinates manually in the left panel."}
        </p>
      </div>
    </div>
  );
}

function RouteSVG({ locations, optimizedPath, hoveredIdx, size }) {
  // Render unoptimized faint edges OR the optimal tour with framer-motion stroke-drawing.
  const optimal = optimizedPath?.path_indices;
  return (
    <svg
      width={size.w}
      height={size.h}
      className="absolute inset-0 pointer-events-none"
      style={{ zIndex: 5 }}
    >
      <defs>
        <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <marker
          id="arrow"
          viewBox="0 0 10 10"
          refX="8"
          refY="5"
          markerWidth="6"
          markerHeight="6"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" fill="#FDE047" />
        </marker>
      </defs>

      {/* faint complete graph BEFORE optimization */}
      {!optimal &&
        locations.length >= 2 &&
        locations.map((a, i) =>
          locations.slice(i + 1).map((b, j) => (
            <line
              key={`${i}-${j}`}
              x1={a.x}
              y1={a.y}
              x2={b.x}
              y2={b.y}
              stroke="#27272A"
              strokeWidth="1"
              strokeDasharray="4 6"
              opacity={hoveredIdx === i || hoveredIdx === i + j + 1 ? 0.8 : 0.35}
            />
          ))
        )}

      {/* optimal tour */}
      {optimal && optimal.length > 1 &&
        optimal.slice(0, -1).map((fromIdx, k) => {
          const toIdx = optimal[k + 1];
          const a = locations[fromIdx];
          const b = locations[toIdx];
          if (!a || !b) return null;
          const seg = optimizedPath.segments[k];
          const mx = (a.x + b.x) / 2;
          const my = (a.y + b.y) / 2;
          return (
            <g key={`route-${k}`}>
              {/* Underglow */}
              <motion.line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="#FDE047"
                strokeWidth="6"
                opacity="0.18"
                filter="url(#glow)"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.2, delay: k * 0.12, ease: "easeInOut" }}
              />
              {/* Crisp line */}
              <motion.line
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke="#FDE047"
                strokeWidth="2"
                markerEnd="url(#arrow)"
                initial={{ pathLength: 0 }}
                animate={{ pathLength: 1 }}
                transition={{ duration: 1.2, delay: k * 0.12, ease: "easeInOut" }}
              />
              {/* Distance badge */}
              {seg && (
                <motion.g
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.25, delay: k * 0.12 + 0.9 }}
                >
                  <rect
                    x={mx - 22}
                    y={my - 9}
                    width="44"
                    height="16"
                    fill="#050505"
                    stroke="#27272A"
                  />
                  <text
                    x={mx}
                    y={my + 3}
                    fontFamily="JetBrains Mono"
                    fontSize="10"
                    fill="#FDE047"
                    textAnchor="middle"
                  >
                    {seg.distance.toFixed(1)}
                  </text>
                </motion.g>
              )}
            </g>
          );
        })}
    </svg>
  );
}

function AlgorithmFloatingCard({ n, states, subs, elapsed, cost, unit }) {
  return (
    <div
      className="absolute top-4 right-4 z-30 bg-black/85 backdrop-blur-md border border-[#27272A] w-[260px]"
      data-testid="algorithm-card"
    >
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#27272A]">
        <div className="flex items-center gap-2">
          <Cpu width={12} height={12} strokeWidth={1.6} className="text-[#FDE047]" />
          <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-300">
            DP · TELEMETRY
          </span>
        </div>
        <span className="font-mono text-[9px] text-neutral-600">/LIVE</span>
      </div>
      <div className="divide-y divide-[#1A1A1D]">
        <KV k="N" v={n || "—"} />
        <KV k="2ⁿ STATES" v={states ? states.toLocaleString() : "—"} />
        <KV k="SUBPROBLEMS" v={subs ? subs.toLocaleString() : "—"} />
        <KV
          k="ELAPSED"
          v={elapsed != null ? `${elapsed.toFixed(2)} ms` : "—"}
          accent={!!elapsed}
        />
        <KV
          k="COST"
          v={cost != null ? `${cost.toFixed(2)}${unit ? " " + unit : ""}` : "—"}
          accent={!!cost}
        />
      </div>
      <div className="px-3 py-2 border-t border-[#27272A] text-center">
        <span className="font-mono text-[10px] tracking-[0.18em] text-[#FDE047]">
          O(n² · 2ⁿ)
        </span>
      </div>
    </div>
  );
}

function KV({ k, v, accent }) {
  return (
    <div className="flex items-center justify-between px-3 py-1.5">
      <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-neutral-500">
        {k}
      </span>
      <span
        className={`font-mono text-[11px] ${
          accent ? "text-[#FDE047]" : "text-white"
        }`}
      >
        {v}
      </span>
    </div>
  );
}

function Stat({ label, value, mono, accent }) {
  return (
    <div className="flex flex-col items-end">
      <span className="text-[9px] font-mono uppercase tracking-[0.2em] text-neutral-500">
        {label}
      </span>
      <span
        className={`text-[14px] leading-tight ${mono ? "font-mono" : "font-bold"} ${
          accent ? "text-[#FDE047]" : "text-white"
        }`}
      >
        {value}
      </span>
    </div>
  );
}

function Spinner() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" className="animate-spin">
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeOpacity="0.25"
      />
      <path
        d="M22 12a10 10 0 0 0-10-10"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

function SolverCard({ cppHealth, n, states, subs, elapsed }) {
  const ok = cppHealth === "available";
  const rows = [
    { k: "ENGINE", v: "C++17 · -O2", mono: true },
    { k: "STATUS", v: ok ? "READY" : (cppHealth || "BOOT").toUpperCase(), accent: ok ? "#22C55E" : "#EF4444" },
    { k: "N", v: n || "—", mono: true },
    { k: "2ⁿ STATES", v: states ? states.toLocaleString() : "—", mono: true },
    { k: "n·2ⁿ SUBPROBLEMS", v: subs ? subs.toLocaleString() : "—", mono: true },
    { k: "LAST RUN", v: elapsed != null ? `${elapsed.toFixed(2)} ms` : "—", mono: true, accent: elapsed != null ? "#FDE047" : null },
  ];
  return (
    <div className="border border-[#27272A] bg-[#050505]">
      {rows.map((r, i) => (
        <div
          key={i}
          className="flex items-center justify-between px-3 py-2 border-b last:border-b-0 border-[#1A1A1D]"
        >
          <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-neutral-500">
            {r.k}
          </span>
          <span
            className={`text-[12px] ${r.mono ? "font-mono" : ""}`}
            style={{ color: r.accent || "#FFFFFF" }}
          >
            {r.v}
          </span>
        </div>
      ))}
    </div>
  );
}

function RouteLedger({ data, locations, unit }) {
  const path = data.path_indices;
  const u = unit || "";
  return (
    <div className="border border-[#27272A] bg-[#050505]">
      {/* header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#27272A] bg-[#0F0F11]">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-[#FDE047]">
          OPTIMAL TOUR
        </span>
        <span className="font-mono text-[10px] text-neutral-500">
          Σ = <span className="text-[#FDE047]">{data.total_cost.toFixed(2)}{u && ` ${u}`}</span>
        </span>
      </div>
      <div>
        {path.map((idx, i) => {
          const loc = locations[idx] || data.route[i];
          const seg = data.segments[i];
          const isDepotStart = i === 0;
          const isDepotEnd = i === path.length - 1;
          return (
            <React.Fragment key={i}>
              <div
                className="flex items-center gap-2 px-3 py-2 border-b last:border-b-0 border-[#1A1A1D]"
                data-testid={`tour-step-${i}`}
              >
                <span className="font-mono text-[10px] text-neutral-600 w-5">
                  {String(i).padStart(2, "0")}
                </span>
                <span
                  className={`w-2 h-2 ${
                    isDepotStart || isDepotEnd ? "bg-white" : "bg-[#FDE047]"
                  }`}
                />
                <span className="text-[12px] flex-1 truncate font-medium">
                  {loc?.name}
                </span>
                <span className="font-mono text-[10px] text-neutral-500">
                  #{idx}
                </span>
              </div>
              {seg && (
                <div className="flex items-center gap-2 px-3 py-1 bg-[#0A0A0C] border-b border-[#1A1A1D]">
                  <span className="w-5" />
                  <span className="text-[10px] font-mono text-neutral-600">
                    │
                  </span>
                  <span className="text-[10px] font-mono text-neutral-500 flex-1">
                    edge → next
                  </span>
                  <span className="text-[10px] font-mono text-[#FDE047]">
                    Δ {seg.distance.toFixed(2)}{u && ` ${u}`}
                  </span>
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function BottomStatus({ n, cost, cppHealth, loading, workspace }) {
  const isMap = workspace === "map";
  const items = [
    { k: "SVC", v: "ROUTEIQ", color: "#FDE047" },
    { k: "ALGO", v: "HELD-KARP" },
    { k: "ENGINE", v: cppHealth === "available" ? "C++ READY" : (cppHealth || "BOOT").toUpperCase(), color: cppHealth === "available" ? "#22C55E" : "#EF4444" },
    { k: "WORKSPACE", v: isMap ? "WORLD MAP" : "CANVAS", color: isMap ? "#FDE047" : null },
    { k: "NODES", v: String(n).padStart(2, "0") },
    { k: "MODE", v: isMap ? "HAVERSINE · KM" : "EUCLIDEAN" },
    { k: "STATE", v: loading ? "COMPUTING…" : cost != null ? `OPTIMAL Σ=${cost.toFixed(2)}${isMap ? "km" : ""}` : "IDLE", color: cost != null ? "#FDE047" : null },
  ];
  return (
    <div
      className="h-8 border-t border-[#27272A] bg-[#050505] flex items-center px-5 gap-5 overflow-hidden shrink-0"
      data-testid="bottom-status-bar"
    >
      {items.map((it, i) => (
        <React.Fragment key={i}>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.18em] whitespace-nowrap">
            <span className="text-neutral-600">{it.k}</span>
            <span style={{ color: it.color || "#FFFFFF" }}>{it.v}</span>
          </div>
          {i < items.length - 1 && <span className="text-neutral-700">·</span>}
        </React.Fragment>
      ))}
      <div className="flex-1" />
      <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-neutral-600 blink">
        AWAIT
      </span>
    </div>
  );
}

export default App;
