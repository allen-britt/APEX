"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

import type { AgentRun } from "@/lib/api";
import { clearMissionAgentRuns, deleteAgentRun } from "@/lib/api";
import GuardrailBadge from "./GuardrailBadge";

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

interface AgentSummaryProps {
  missionId: number;
  run: AgentRun | null;
}

export default function AgentSummary({ missionId, run }: AgentSummaryProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleDeleteRun = () => {
    if (!run) return;
    const confirmed = window.confirm("Delete this agent run? This cannot be undone.");
    if (!confirmed) return;

    startTransition(async () => {
      try {
        await deleteAgentRun(run.id);
        router.refresh();
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
        router.refresh();
      } catch (error) {
        console.error("Failed to clear agent runs", error);
        alert("Failed to clear agent runs. Please try again.");
      }
    });
  };

  if (!run) {
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
    <div className="card space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">Last run</p>
          <p className="text-lg font-semibold capitalize">{run.status}</p>
        </div>
        <span className="text-xs uppercase tracking-wide text-slate-500">
          {formatDate(run.created_at)}
        </span>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-300">Summary</h4>
        <p className="text-sm text-slate-200 whitespace-pre-line">{run.summary || "—"}</p>
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-slate-300">Next steps</h4>
        <p className="text-sm text-slate-200 whitespace-pre-line">{run.next_steps || "—"}</p>
      </div>

      <GuardrailBadge status={run.guardrail_status} issues={run.guardrail_issues ?? []} />

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
