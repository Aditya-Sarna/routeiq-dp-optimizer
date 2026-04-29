import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import { motion, AnimatePresence } from "framer-motion";
import { Search, MapPin, Xmark } from "iconoir-react";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export default function GeocodeSearch({ onSelect, disabled }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const inputRef = useRef(null);
  const wrapperRef = useRef(null);
  const debounceRef = useRef(null);
  const reqIdRef = useRef(0);

  // Debounced search
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!q || q.trim().length < 2) {
      setResults([]);
      setErr(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    debounceRef.current = setTimeout(async () => {
      const myReq = ++reqIdRef.current;
      try {
        const { data } = await axios.get(`${API}/geocode`, {
          params: { q: q.trim(), limit: 6 },
        });
        if (myReq !== reqIdRef.current) return; // stale
        setResults(data?.results || []);
        setErr((data?.results || []).length === 0 ? "No matches" : null);
        setActiveIdx(-1);
      } catch (e) {
        if (myReq !== reqIdRef.current) return;
        setErr("Geocoder unavailable");
        setResults([]);
      } finally {
        if (myReq === reqIdRef.current) setLoading(false);
      }
    }, 350);
    return () => debounceRef.current && clearTimeout(debounceRef.current);
  }, [q]);

  // Close on outside click
  useEffect(() => {
    const onDoc = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const pick = (r) => {
    if (!r) return;
    onSelect && onSelect({ lat: r.lat, lng: r.lng, name: r.name || r.label });
    setQ("");
    setResults([]);
    setOpen(false);
    setActiveIdx(-1);
    inputRef.current?.blur();
  };

  const onKeyDown = (e) => {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && results[0]) pick(results[0]);
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIdx((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => (i - 1 + results.length) % results.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(results[activeIdx >= 0 ? activeIdx : 0]);
    } else if (e.key === "Escape") {
      setOpen(false);
      inputRef.current?.blur();
    }
  };

  return (
    <div
      ref={wrapperRef}
      className="absolute top-4 left-4 z-[400] w-[340px] pointer-events-auto"
      data-testid="geocode-search"
    >
      <div
        className={`flex items-stretch border ${
          open ? "border-[#FDE047]" : "border-[#27272A]"
        } bg-black/85 backdrop-blur-md transition-colors`}
      >
        <div className="flex items-center pl-3 pr-2 text-[#FDE047]">
          <Search width={14} height={14} strokeWidth={1.8} />
        </div>
        <input
          ref={inputRef}
          data-testid="geocode-search-input"
          value={q}
          disabled={disabled}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="Search a place · e.g. Bandra, SoHo, Camden"
          className="flex-1 bg-transparent border-0 outline-none text-white text-[12px] font-mono placeholder:text-neutral-600 py-2.5 pr-2 disabled:opacity-50"
        />
        {q && (
          <button
            data-testid="geocode-clear-btn"
            onClick={() => {
              setQ("");
              setResults([]);
              setErr(null);
              inputRef.current?.focus();
            }}
            className="px-2 text-neutral-500 hover:text-white transition-colors"
          >
            <Xmark width={14} height={14} strokeWidth={1.8} />
          </button>
        )}
      </div>

      <AnimatePresence>
        {open && q.trim().length >= 2 && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="mt-1 bg-[#050505] border border-[#27272A] divide-y divide-[#1A1A1D] shadow-2xl"
          >
            {loading && (
              <div className="px-3 py-2.5 flex items-center gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-neutral-500">
                <span className="w-3 h-3 border border-neutral-600 border-t-[#FDE047] rounded-full animate-spin" />
                SEARCHING NOMINATIM…
              </div>
            )}

            {!loading && err && results.length === 0 && (
              <div
                data-testid="geocode-empty-state"
                className="px-3 py-2.5 text-[11px] font-mono text-neutral-500"
              >
                {err}
              </div>
            )}

            {!loading &&
              results.map((r, i) => (
                <button
                  key={`${r.lat}-${r.lng}-${i}`}
                  data-testid={`geocode-result-${i}`}
                  onMouseEnter={() => setActiveIdx(i)}
                  onClick={() => pick(r)}
                  className={`w-full text-left px-3 py-2.5 flex items-start gap-2.5 transition-colors group ${
                    activeIdx === i ? "bg-[#0F0F11]" : "hover:bg-[#0F0F11]"
                  }`}
                >
                  <MapPin
                    width={14}
                    height={14}
                    strokeWidth={1.6}
                    className={`mt-0.5 shrink-0 ${
                      activeIdx === i ? "text-[#FDE047]" : "text-neutral-500"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] text-white truncate font-medium">
                      {r.label || r.name}
                    </div>
                    <div className="text-[10px] font-mono text-neutral-500 mt-0.5 truncate">
                      {r.lat.toFixed(4)}, {r.lng.toFixed(4)} · {r.type}
                    </div>
                  </div>
                  {activeIdx === i && (
                    <span className="text-[9px] font-mono text-[#FDE047] uppercase tracking-[0.2em] mt-1">
                      ↵
                    </span>
                  )}
                </button>
              ))}

            {!loading && results.length > 0 && (
              <div className="px-3 py-1.5 text-[9px] font-mono uppercase tracking-[0.2em] text-neutral-600 bg-[#0A0A0C]">
                {results.length} RESULT{results.length === 1 ? "" : "S"} · ↑/↓ NAV · ↵ SELECT · ESC
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
