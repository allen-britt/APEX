"use client";

import { useState } from "react";

import { analyzeMission } from "@/lib/api";

type RunAnalysisButtonProps = {
  missionId: number;
  onCompleted?: () => void;
};

export function RunAnalysisButton({ missionId, onCompleted }: RunAnalysisButtonProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    if (isRunning) return;

    setIsRunning(true);
    setError(null);

    try {
      await analyzeMission(missionId);
      onCompleted?.();
    } catch (err) {
      console.error("Failed to run analysis", err);
      setError("Failed to run analysis. Please try again.");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex flex-col items-end gap-2">
      <button
        type="button"
        onClick={handleClick}
        disabled={isRunning}
        className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-900 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isRunning ? "Running..." : "Run Analysis"}
      </button>
      {error && <p className="text-xs text-rose-400">{error}</p>}
    </div>
  );
}
