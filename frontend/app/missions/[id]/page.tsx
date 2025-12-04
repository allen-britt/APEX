import Link from "next/link";

import SystemStatusBar from "@/components/SystemStatusBar";
import MissionTabs from "@/components/MissionTabs";

import {
  fetchMission,
  fetchMissionDocuments,
  fetchAgentRuns,
  fetchMissionDatasets,
  fetchGapAnalysis,
  type GapAnalysisResponse,
  type AgentRun,
  type MissionDataset,
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
    const [mission, documents, runs, datasets, gapAnalysis] = await Promise.all([
      fetchMission(missionId),
      fetchMissionDocuments(missionId),
      fetchAgentRuns(missionId),
      fetchMissionDatasets(missionId),
      fetchGapAnalysis(missionId),
    ]);

    return (
      <div className="space-y-6">
        <SystemStatusBar />
        <MissionTabs
          mission={mission}
          missionId={missionId}
          documents={documents}
          runs={runs}
          datasets={datasets as MissionDataset[]}
          gapAnalysis={gapAnalysis as GapAnalysisResponse}
        />
      </div>
    );
  } catch (error) {
    console.error("Failed to load mission view", error);
    return (
      <div className="card border border-rose-800 bg-rose-950/40 text-sm text-rose-200">
        Failed to load mission data. Please verify the backend is running.
      </div>
    );
  }
}
