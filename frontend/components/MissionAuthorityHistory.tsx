"use client";

import type { Mission } from "@/lib/api";
import { formatAuthorityLabel } from "@/lib/authorityPolicy";

interface MissionAuthorityHistoryProps {
  mission: Mission;
}

function formatDate(value?: string | null) {
  if (!value) return "";
  return new Date(value).toLocaleString();
}

function riskBadgeClass(risk?: string) {
  switch (risk) {
    case "LOW":
      return "bg-emerald-500/10 text-emerald-200 border-emerald-500/30";
    case "MEDIUM":
      return "bg-amber-500/10 text-amber-200 border-amber-500/30";
    case "HIGH":
      return "bg-rose-500/10 text-rose-200 border-rose-500/30";
    case "BLOCKED":
      return "bg-red-500/10 text-red-200 border-red-500/30";
    default:
      return "bg-slate-700/30 text-slate-200 border-slate-600";
  }
}

export default function MissionAuthorityHistory({ mission }: MissionAuthorityHistoryProps) {
  const pivots = mission.authority_pivots ?? [];
  const originalLabel = formatAuthorityLabel(mission.original_authority ?? mission.primary_authority);

  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Authority history</h3>
      </div>

      <div className="space-y-3">
        <div className="rounded-xl border border-slate-800/70 bg-slate-950/60 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Original authority</p>
          <p className="text-sm font-semibold text-slate-100">{originalLabel}</p>
          <p className="text-xs text-slate-500">Established on {formatDate(mission.created_at)}</p>
        </div>

        {pivots.length === 0 ? (
          <p className="text-xs text-slate-500">No pivots recorded yet.</p>
        ) : (
          <ol className="space-y-3">
            {pivots.map((pivot) => (
              <li key={pivot.id} className="rounded-xl border border-slate-800/60 bg-slate-950/70 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-xs uppercase tracking-wide text-slate-500">Pivot</p>
                    <p className="text-sm font-semibold text-slate-100">
                      {formatAuthorityLabel(pivot.from_authority)}
                      <span className="mx-1 text-slate-500">→</span>
                      {formatAuthorityLabel(pivot.to_authority)}
                    </p>
                  </div>
                  <span
                    className={`rounded-full border px-3 py-0.5 text-xs font-semibold uppercase tracking-wide ${riskBadgeClass(pivot.risk)}`}
                  >
                    {pivot.risk ?? "UNKNOWN"}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-300">{pivot.justification}</p>
                {pivot.conditions?.length ? (
                  <ul className="mt-3 list-inside list-disc text-xs text-amber-200/90">
                    {pivot.conditions.map((condition, idx) => (
                      <li key={`${pivot.id}-condition-${idx}`}>{condition}</li>
                    ))}
                  </ul>
                ) : null}
                <p className="mt-3 text-xs text-slate-500">Pivoted on {formatDate(pivot.created_at)}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
