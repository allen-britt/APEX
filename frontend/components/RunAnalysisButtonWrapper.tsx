"use client";

import { RunAnalysisButton } from "@/components/RunAnalysisButton";
import { useMission } from "@/context/MissionContext";

interface RunAnalysisButtonWrapperProps {
  missionId: number;
}

export default function RunAnalysisButtonWrapper({ missionId }: RunAnalysisButtonWrapperProps) {
  const { setLatestRun } = useMission();

  return <RunAnalysisButton missionId={missionId} onCompleted={setLatestRun} />;
}
