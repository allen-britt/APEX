"use client";

import { useEffect, useState } from "react";

import { fetchSystemStatus, type ComponentStatusValue, type SystemStatus } from "@/lib/api";

const POLL_INTERVAL_MS = 15_000;

type StatusLevel = "ok" | "degraded" | "down" | "unknown";

function normalizeStatus(value: ComponentStatusValue): {
  status: StatusLevel;
  label: string;
  detail?: string;
} {
  const raw = typeof value === "string" ? value : value?.status ?? "unknown";
  const normalized = raw?.toLowerCase() ?? "unknown";

  if (normalized === "ok") {
    return { status: "ok", label: "OK", detail: typeof value === "string" ? undefined : value?.detail };
  }
  if (normalized === "degraded" || normalized === "warn" || normalized === "warning") {
    return { status: "degraded", label: "Degraded", detail: typeof value === "string" ? undefined : value?.detail };
  }
  if (normalized === "error" || normalized === "down" || normalized === "fail") {
    return { status: "down", label: "Down", detail: typeof value === "string" ? undefined : value?.detail };
  }
  return { status: "unknown", label: "Unknown", detail: typeof value === "string" ? undefined : value?.detail };
}

function statusClasses(level: StatusLevel): string {
  switch (level) {
    case "ok":
      return "border-emerald-500/60 text-emerald-200";
    case "degraded":
      return "border-amber-400/70 text-amber-200";
    case "down":
      return "border-rose-500/70 text-rose-200";
    default:
      return "border-slate-500/60 text-slate-200";
  }
}

function StatusBadge({ label, value }: { label: string; value: ComponentStatusValue }) {
  const normalized = normalizeStatus(value);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-slate-400">{label}</span>
      <span
        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${statusClasses(normalized.status)}`}
      >
        {normalized.label}
      </span>
    </div>
  );
}

export default function SystemStatusBar() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const data = await fetchSystemStatus();
        if (cancelled) return;
        setStatus(data);
        setError(null);
      } catch (err) {
        console.error("Failed to load system status", err);
        if (!cancelled) {
          setError("Status unavailable");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    load();
    const intervalId = window.setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, []);

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/70 px-4 py-3 text-xs text-slate-200">
      {loading && !status ? <p className="text-slate-400">Checking system status…</p> : null}
      {!loading && error ? <p className="text-rose-300">{error}</p> : null}
      {status ? (
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-slate-400">Overall</span>
            <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] uppercase tracking-wide ${statusClasses(normalizeStatus(status.overall).status)}`}>
              {normalizeStatus(status.overall).label}
            </span>
          </div>
          <StatusBadge label="Backend" value={status.backend} />
          <StatusBadge label="AggreGator" value={status.aggregator} />
          <StatusBadge label="LLM" value={status.llm} />
        </div>
      ) : null}
    </div>
  );
}
