"use client";

import { useState } from "react";

import type { GapAnalysisResponse } from "@/lib/api";
import { fetchGapAnalysis } from "@/lib/api";

interface GapsPrioritiesProps {
  missionId: number;
  initialData: GapAnalysisResponse;
}

interface FindingGroup {
  title: string;
  items: GapAnalysisResponse[keyof GapAnalysisResponse];
}

function renderFindingList(label: string, findings: GapAnalysisResponse[keyof GapAnalysisResponse]) {
  if (!Array.isArray(findings) || findings.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <h4 className="text-sm font-semibold text-slate-200">{label}</h4>
      <ul className="mt-2 space-y-2 text-sm text-slate-300">
        {findings.map((finding, index) => (
          <li key={`${label}-${index}`} className="rounded-lg border border-slate-800/60 bg-slate-900/40 p-2">
            <p className="font-medium text-slate-100">{finding.title}</p>
            {finding.detail ? <p className="text-xs text-slate-400">{finding.detail}</p> : null}
            {finding.severity ? (
              <span className="mt-1 inline-flex items-center rounded-full border border-slate-700 px-2 py-0.5 text-[11px] uppercase tracking-wide text-slate-300">
                {finding.severity}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function renderPriorityList(label: string, entries: GapAnalysisResponse["priorities"]["entities"]) {
  if (!entries.length) {
    return null;
  }
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-3">
      <h4 className="text-sm font-semibold text-slate-200">{label}</h4>
      <ul className="mt-2 space-y-2 text-sm text-slate-300">
        {entries.map((entry, index) => (
          <li key={`${label}-${index}`} className="rounded-lg border border-slate-800/60 bg-slate-900/40 p-2">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium text-slate-100">{entry.name}</p>
              {typeof entry.score === "number" ? (
                <span className="text-xs text-indigo-300">Score: {entry.score.toFixed(2)}</span>
              ) : null}
            </div>
            <p className="text-xs text-slate-400">{entry.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function GapsPriorities({ missionId, initialData }: GapsPrioritiesProps) {
  const [data, setData] = useState<GapAnalysisResponse>(initialData);
  const [loading, setLoading] = useState(false);

  async function refreshAnalysis() {
    try {
      setLoading(true);
      const next = await fetchGapAnalysis(missionId, { forceRegenerate: true });
      setData(next);
    } catch (error) {
      console.error("Failed to refresh gap analysis", error);
    } finally {
      setLoading(false);
    }
  }

  const generatedDate = new Date(data.generated_at);
  const timestamp = Number.isNaN(generatedDate.getTime())
    ? data.generated_at
    : generatedDate.toLocaleString();

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-xl font-semibold">Gaps & Priorities</h3>
          <p className="text-xs text-slate-400">Generated {timestamp}</p>
        </div>
        <button
          type="button"
          onClick={refreshAnalysis}
          disabled={loading}
          className="rounded border border-indigo-400 px-3 py-1 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-500/20 disabled:opacity-60"
        >
          {loading ? "Updating…" : "Refresh analysis"}
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {renderFindingList("Missing data", data.missing_data)}
        {renderFindingList("Timeline gaps", data.time_gaps)}
        {renderFindingList("Conflicts", data.conflicts)}
        {renderFindingList("High-value unknowns", data.high_value_unknowns)}
        {renderFindingList("Quality findings", data.quality_findings)}
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h4 className="text-lg font-semibold text-slate-100">Priorities</h4>
          <p className="text-xs uppercase tracking-wide text-slate-500">{data.priorities.rationale}</p>
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {renderPriorityList("Priority entities", data.priorities.entities)}
          {renderPriorityList("Priority events", data.priorities.events)}
        </div>
      </div>
    </section>
  );
}
