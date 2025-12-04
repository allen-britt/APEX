"use client";

import { useTransition } from "react";

import { clearMissionAgentRuns, deleteAgentRun } from "@/lib/api";
import { useMission } from "@/context/MissionContext";
import GuardrailBadge from "./GuardrailBadge";
import PolicyFootprint from "@/components/PolicyFootprint";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function AgentSummary() {
  const { mission, latestRun, setLatestRun } = useMission();
  const [isPending, startTransition] = useTransition();
  const missionId = mission.id;

  const handleDeleteRun = () => {
    if (!latestRun) return;
    const confirmed = window.confirm("Delete this agent run? This cannot be undone.");
    if (!confirmed) return;

    startTransition(async () => {
      try {
        await deleteAgentRun(latestRun.id);
        setLatestRun(null);
      } catch (error) {
        console.error("Failed to delete agent run", error);
        alert("Failed to delete agent run. Please try again.");
      }
    });
  };

  const handleClearRuns = () => {
    const confirmed = window.confirm(
      "Delete all agent runs for this mission? This cannot be undone.",
    );
    if (!confirmed) return;

    startTransition(async () => {
      try {
        await clearMissionAgentRuns(missionId);
        setLatestRun(null);
      } catch (error) {
        console.error("Failed to clear agent runs", error);
        alert("Failed to clear agent runs. Please try again.");
      }
    });
  };

  if (!latestRun) {
    return (
      <div className="card space-y-3">
        <p className="text-sm text-slate-400">No analysis has been run yet.</p>
        <button
          type="button"
          className="rounded border border-slate-600 px-3 py-1 text-sm font-medium text-slate-100 transition hover:bg-slate-800 disabled:opacity-60"
          onClick={handleClearRuns}
          disabled={isPending}
        >
          {isPending ? "Clearing…" : "Clear history"}
        </button>
      </div>
    );
  }

  return (
    <div className="card space-y-4">
      <PolicyFootprint mission={mission} layout="stacked" showSecondary={false} />
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">Last run</p>
          <p className="text-lg font-semibold capitalize">{latestRun.status}</p>
        </div>
        <span className="text-xs uppercase tracking-wide text-slate-500">
          {formatDate(latestRun.created_at)}
        </span>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-300">Summary</h4>
        <p className="text-sm text-slate-200 whitespace-pre-line">{latestRun.summary || "—"}</p>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-300">Next steps</h4>
        <p className="text-sm text-slate-200 whitespace-pre-line">{latestRun.next_steps || "—"}</p>
      </div>

      <div>
        <p className="text-sm font-semibold text-slate-300">Guardrail posture</p>
        <p className="text-xs text-slate-500">
          Guardrails monitor mission intent for {mission.primary_authority || "configured authority"} across {mission.int_types?.join(", ") || "selected INT lanes"}.
        </p>
        <div className="mt-2">
          <GuardrailBadge status={latestRun.guardrail_status} issues={latestRun.guardrail_issues ?? []} />
        </div>
      </div>

      <div className="flex flex-wrap gap-2 pt-3">
        <button
          type="button"
          className="rounded border border-rose-600 px-3 py-1 text-sm font-medium text-rose-100 transition hover:bg-rose-900/50 disabled:opacity-60"
          onClick={handleDeleteRun}
          disabled={isPending}
        >
          {isPending ? "Deleting…" : "Delete this run"}
        </button>
        <button
          type="button"
          className="rounded border border-slate-600 px-3 py-1 text-sm font-medium text-slate-100 transition hover:bg-slate-800 disabled:opacity-60"
          onClick={handleClearRuns}
          disabled={isPending}
        >
          {isPending ? "Clearing…" : "Clear all runs"}
        </button>
      </div>
    </div>
  );
}
