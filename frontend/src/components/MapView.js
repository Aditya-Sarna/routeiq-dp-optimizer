import React, { useEffect, useMemo, useRef } from "react";
import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  useMap,
  useMapEvents,
  Tooltip,
  CircleMarker,
} from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { motion } from "framer-motion";

// ─────────── Custom Leaflet markers (sharp, swiss) ───────────
const buildIcon = (kind, idx) => {
  const isDepot = kind === "depot";
  const bg = isDepot ? "#FFFFFF" : "#FDE047";
  const label = isDepot ? "★" : idx;
  const size = isDepot ? 22 : 18;
  return L.divIcon({
    className: "routeiq-leaflet-icon",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `
      <div style="
        position: relative;
        width:${size}px;height:${size}px;
        background:${bg};
        border:1px solid #000;
        display:flex;align-items:center;justify-content:center;
        font-family:'JetBrains Mono',monospace;
        font-weight:700;font-size:${isDepot ? 10 : 9}px;color:#000;
        box-shadow: ${
          isDepot
            ? "0 0 12px rgba(255,255,255,0.55), 0 0 0 3px rgba(255,255,255,0.12)"
            : "0 0 8px rgba(253,224,71,0.45)"
        };
      ">
        ${label}
      </div>
    `,
  });
};

// ─────────── Click handler ───────────
function ClickCatcher({ onClick, enabled }) {
  useMapEvents({
    click: (e) => {
      if (!enabled) return;
      onClick(e.latlng.lat, e.latlng.lng);
    },
  });
  return null;
}

// ─────────── Auto-fit on locations change ───────────
function FitBounds({ locations, optimizedPath }) {
  const map = useMap();
  const lastSig = useRef("");
  useEffect(() => {
    if (!locations || locations.length === 0) return;
    const sig =
      locations.map((l) => `${l.lat?.toFixed(3)},${l.lng?.toFixed(3)}`).join("|") +
      "::" +
      (optimizedPath ? "opt" : "raw");
    if (sig === lastSig.current) return;
    lastSig.current = sig;

    const points = locations
      .filter((l) => typeof l.lat === "number" && typeof l.lng === "number")
      .map((l) => [l.lat, l.lng]);
    if (points.length === 0) return;
    if (points.length === 1) {
      map.setView(points[0], Math.max(map.getZoom(), 11));
    } else {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 14 });
    }
  }, [locations, optimizedPath, map]);
  return null;
}

// ─────────── Main MapView ───────────
export default function MapView({
  locations: rawLocations,
  optimizedPath,
  onAdd,
  onHover,
  hoveredIdx,
  enableClick = true,
  initialCenter = [28.6139, 77.209], // Delhi default — algorithmically neutral
  initialZoom = 5,
}) {
  // Defensive guard: only render entries that actually have numeric lat/lng.
  // (Protects against transient renders where canvas-shaped {x,y} entries leak in.)
  const locations = useMemo(
    () =>
      (rawLocations || []).filter(
        (l) => typeof l?.lat === "number" && typeof l?.lng === "number"
      ),
    [rawLocations]
  );
  // Build polyline for optimized tour
  const tourLine = useMemo(() => {
    if (!optimizedPath?.path_indices) return null;
    return optimizedPath.path_indices
      .map((i) => locations[i])
      .filter((l) => l && typeof l.lat === "number" && typeof l.lng === "number")
      .map((l) => [l.lat, l.lng]);
  }, [optimizedPath, locations]);

  return (
    <MapContainer
      center={initialCenter}
      zoom={initialZoom}
      scrollWheelZoom
      zoomControl={false}
      attributionControl={false}
      style={{ width: "100%", height: "100%", background: "#0A0A0C" }}
    >
      {/* Dark map tiles — CartoDB Dark Matter (no key required) */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}@2x.png"
        subdomains={["a", "b", "c", "d"]}
        maxZoom={19}
      />
      {/* Labels overlay (separate so we get crisp white labels) */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}@2x.png"
        subdomains={["a", "b", "c", "d"]}
        maxZoom={19}
      />

      <ClickCatcher onClick={onAdd} enabled={enableClick} />
      <FitBounds locations={locations} optimizedPath={optimizedPath} />

      {/* Faint complete-graph edges before optimization */}
      {!optimizedPath &&
        locations.length >= 2 &&
        locations
          .slice(0, -1)
          .flatMap((a, i) =>
            locations.slice(i + 1).map((b, j) => (
              <Polyline
                key={`raw-${i}-${i + j + 1}`}
                positions={[
                  [a.lat, a.lng],
                  [b.lat, b.lng],
                ]}
                pathOptions={{
                  color: "#27272A",
                  weight: 1,
                  dashArray: "4 6",
                  opacity:
                    hoveredIdx === i || hoveredIdx === i + j + 1 ? 0.85 : 0.45,
                }}
              />
            ))
          )}

      {/* Optimized tour — yellow with glow */}
      {tourLine && tourLine.length >= 2 && (
        <>
          <Polyline
            positions={tourLine}
            pathOptions={{
              color: "#FDE047",
              weight: 8,
              opacity: 0.18,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
          <Polyline
            positions={tourLine}
            pathOptions={{
              color: "#FDE047",
              weight: 2.5,
              opacity: 1,
              lineCap: "round",
              lineJoin: "round",
            }}
          />
          {/* per-segment distance bubbles at midpoints */}
          {optimizedPath?.segments?.map((seg, k) => {
            const a = locations[seg.from];
            const b = locations[seg.to];
            if (!a || !b) return null;
            const mid = [(a.lat + b.lat) / 2, (a.lng + b.lng) / 2];
            return (
              <CircleMarker
                key={`segbadge-${k}`}
                center={mid}
                radius={1}
                pathOptions={{ opacity: 0, fillOpacity: 0 }}
              >
                <Tooltip
                  permanent
                  direction="center"
                  className="routeiq-edge-tooltip"
                  offset={[0, 0]}
                >
                  {seg.distance < 1
                    ? `${(seg.distance * 1000).toFixed(0)} m`
                    : `${seg.distance.toFixed(2)} km`}
                </Tooltip>
              </CircleMarker>
            );
          })}
        </>
      )}

      {/* Markers */}
      {locations.map((loc, i) => (
        <Marker
          key={`m-${i}`}
          position={[loc.lat, loc.lng]}
          icon={buildIcon(i === 0 ? "depot" : "stop", i)}
          eventHandlers={{
            mouseover: () => onHover && onHover(i),
            mouseout: () => onHover && onHover(null),
          }}
        >
          <Tooltip direction="top" offset={[0, -12]} className="routeiq-tooltip">
            <div style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11 }}>
              <strong style={{ color: i === 0 ? "#FFFFFF" : "#FDE047" }}>
                {i === 0 ? "DEPOT" : `STOP ${String.fromCharCode(64 + i)}`}
              </strong>
              <br />
              <span style={{ color: "#A1A1AA" }}>{loc.name}</span>
              <br />
              <span style={{ color: "#71717A", fontSize: 10 }}>
                {loc.lat.toFixed(4)}, {loc.lng.toFixed(4)}
              </span>
            </div>
          </Tooltip>
        </Marker>
      ))}
    </MapContainer>
  );
}
