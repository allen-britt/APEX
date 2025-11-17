"use client";

import { useRouter } from "next/navigation";

import { RunAnalysisButton } from "@/components/RunAnalysisButton";

interface RunAnalysisButtonWrapperProps {
  missionId: number;
}

export default function RunAnalysisButtonWrapper({ missionId }: RunAnalysisButtonWrapperProps) {
  const router = useRouter();

  return (
    <RunAnalysisButton
      missionId={missionId}
      onCompleted={() => {
        router.refresh();
      }}
    />
  );
}
