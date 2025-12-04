"use client";

import { useState } from "react";

import type { GapAnalysisResponse, GapFinding } from "@/lib/api";
import { fetchGapAnalysis } from "@/lib/api";

interface GapAnalysisPanelProps {
  missionId: number;
}

export default function GapAnalysisPanel({ missionId }: GapAnalysisPanelProps) {
  const [result, setResult] = useState<GapAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRunAnalysis() {
    try {
      setLoading(true);
      setError(null);
      console.log("gap-analysis: trigger", { missionId });
      const payload = await fetchGapAnalysis(missionId, { forceRegenerate: true });
      setResult(payload);
    } catch (err) {
      console.error("Failed to run gap analysis", err);
      const message = err instanceof Error ? err.message : "Failed to run gap analysis. Please try again.";
      setError(message || "Failed to run gap analysis. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className="text-lg font-semibold text-slate-100">Gap analysis</h4>
          <p className="text-xs text-slate-400">Generate policy-aware gaps and next steps.</p>
        </div>
        <button
          type="button"
          onClick={handleRunAnalysis}
          disabled={loading}
          className="rounded border border-emerald-400 px-3 py-1 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-500/20 disabled:opacity-60"
        >
          {loading ? "Running…" : "Run gap analysis"}
        </button>
      </div>

      {error ? <p className="text-sm text-rose-300">{error}</p> : null}

      {result ? <AnalysisResult result={result} /> : <EmptyState />}
    </div>
  );
}

function EmptyState() {
  return <p className="text-xs text-slate-500">No run yet. Click the button above to generate results.</p>;
}

function AnalysisResult({ result }: { result: GapAnalysisResponse }) {
  const generatedAt = new Date(result.generated_at);
  const timestamp = Number.isNaN(generatedAt.getTime())
    ? result.generated_at
    : generatedAt.toLocaleString();

  const findingGroups: { title: string; items: GapFinding[] }[] = [
    { title: "Missing data", items: result.missing_data },
    { title: "Timeline gaps", items: result.time_gaps },
    { title: "Conflicts", items: result.conflicts },
    { title: "High-value unknowns", items: result.high_value_unknowns },
    { title: "Quality findings", items: result.quality_findings },
  ];

  const totalAlerts = findingGroups.reduce((sum, group) => sum + (group.items?.length ?? 0), 0);

  return (
    <div className="space-y-4 text-sm text-slate-200">
      <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-3">
        <p className="text-xs uppercase tracking-wide text-slate-500">Latest run</p>
        <p className="text-sm text-slate-100">Generated {timestamp}</p>
        <p className="text-xs text-slate-400">Gap alerts detected: {totalAlerts}</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {findingGroups.map((group) => (
          <FindingList key={group.title} title={group.title} findings={group.items} />
        ))}
      </div>

      <div className="rounded-xl border border-slate-800/70 bg-slate-900/30 p-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h5 className="text-sm font-semibold text-slate-300">Priorities snapshot</h5>
          <span className="text-[11px] uppercase tracking-wide text-slate-500">{result.priorities.rationale}</span>
        </div>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <PriorityList label="Entities" entries={result.priorities.entities} />
          <PriorityList label="Events" entries={result.priorities.events} />
        </div>
      </div>
    </div>
  );
}

function FindingList({ title, findings }: { title: string; findings: GapFinding[] }) {
  if (!Array.isArray(findings) || findings.length === 0) {
    return null;
  }

  return (
    <section className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-900/30 p-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-300">{title}</p>
        <span className="text-[11px] uppercase tracking-wide text-slate-500">{findings.length}</span>
      </div>
      <ul className="space-y-2 text-xs text-slate-300">
        {findings.map((finding, index) => (
          <li key={`${title}-${index}`} className="rounded-lg border border-slate-800/50 bg-slate-900/40 p-2">
            <p className="font-medium text-slate-100">{finding.title}</p>
            {finding.detail ? <p className="text-slate-400">{finding.detail}</p> : null}
            {finding.severity ? (
              <span className="mt-1 inline-flex items-center rounded-full border border-slate-800 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">
                {finding.severity}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function PriorityList({
  label,
  entries,
}: {
  label: string;
  entries: GapAnalysisResponse["priorities"]["entities"];
}) {
  if (!entries.length) {
    return <p className="text-xs text-slate-500">No {label.toLowerCase()} flagged.</p>;
  }

  return (
    <ul className="space-y-2 text-xs text-slate-300">
      {entries.map((entry, index) => (
        <li key={`${label}-${index}`} className="rounded-lg border border-slate-800/60 bg-slate-950/40 p-2">
          <div className="flex items-center justify-between gap-2">
            <p className="font-medium text-slate-100">{entry.name}</p>
            {typeof entry.score === "number" ? <span className="text-[11px] text-indigo-300">Score {entry.score.toFixed(2)}</span> : null}
          </div>
          <p className="text-slate-400">{entry.reason}</p>
        </li>
      ))}
    </ul>
  );
}
