import Link from "next/link";

import MissionDetail from "@/components/MissionDetail";
import DocumentForm from "@/components/DocumentForm";
import DocumentList from "@/components/DocumentList";
import AgentSummary from "@/components/AgentSummary";
import GuardrailBadge from "@/components/GuardrailBadge";
import RunAnalysisButton from "@/components/RunAnalysisButtonWrapper";
import EntitiesEventsView from "@/components/EntitiesEventsView";
import {
  fetchMission,
  fetchMissionDocuments,
  fetchAgentRuns,
  fetchMissionGraph,
  type AgentRun,
} from "@/lib/api";

interface MissionPageProps {
  params: { id: string };
}

function getLatestRun(runs: AgentRun[]): AgentRun | null {
  return runs.length ? runs[0] : null;
}

export default async function MissionPage({ params }: MissionPageProps) {
  const missionId = Number(params.id);

  if (Number.isNaN(missionId)) {
    return <div className="text-red-400">Invalid mission id.</div>;
  }

  try {
    const [mission, documents, runs, graph] = await Promise.all([
      fetchMission(missionId),
      fetchMissionDocuments(missionId),
      fetchAgentRuns(missionId),
      fetchMissionGraph(missionId),
    ]);

    const latestRun = getLatestRun(runs);

    return (
      <div className="space-y-8">
        <MissionDetail mission={mission} />

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold">Documents</h3>
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span>{documents.length} files</span>
              <Link
                href={`/missions/${missionId}/report`}
                className="rounded border border-slate-600 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-800"
              >
                View report
              </Link>
            </div>
          </div>
          <div className="grid gap-6 lg:grid-cols-2">
            <DocumentList missionId={missionId} documents={documents} />
            <DocumentForm missionId={missionId} />
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="space-y-4">
            <div className="card space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Agent</h3>
                <RunAnalysisButton missionId={missionId} />
              </div>
              <p className="text-sm text-slate-400">
                Run an APEX analysis to extract entities, events, and next steps.
              </p>
            </div>
            <AgentSummary missionId={missionId} run={latestRun} />
          </div>

          <div className="card space-y-3">
            <h3 className="text-xl font-semibold">Guardrail status</h3>
            <GuardrailBadge
              status={latestRun?.guardrail_status ?? "ok"}
              issues={latestRun?.guardrail_issues ?? []}
            />
          </div>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-semibold">Entities & Events</h3>
            <span className="text-sm text-slate-400">
              {graph.entities.length} entities • {graph.events.length} events
            </span>
          </div>
          <EntitiesEventsView missionId={missionId} entities={graph.entities} events={graph.events} />
        </section>
      </div>
    );
  } catch (err) {
    console.error("Failed to load mission view", err);
    return (
      <div className="card border border-rose-800 bg-rose-950/40 text-sm text-rose-200">
        Failed to load mission data. Please verify the backend is running.
      </div>
    );
  }
}
