"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import useSWR from "swr";

import { fetchMission, type AgentRun, type Mission } from "@/lib/api";

interface MissionContextValue {
  mission: Mission;
  latestRun: AgentRun | null;
  refreshMission: () => void;
  setLatestRun: (run: AgentRun | null) => void;
}

const MissionContext = createContext<MissionContextValue | undefined>(undefined);

interface MissionProviderProps {
  initialMission: Mission;
  initialRun?: AgentRun | null;
  children: React.ReactNode;
}

export function MissionProvider({ initialMission, initialRun, children }: MissionProviderProps) {
  const defaultRun = initialRun ?? initialMission.latest_agent_run ?? null;
  const [mission, setMission] = useState(initialMission);
  const [latestRun, setLatestRunState] = useState<AgentRun | null>(defaultRun);
  const { mutate } = useSWR(["mission", mission.id], () => fetchMission(mission.id), {
    fallbackData: initialMission,
  });

  const applyMission = useCallback((updated: Mission) => {
    setMission(updated);
    setLatestRunState(updated.latest_agent_run ?? null);
    return updated;
  }, []);

  const refreshMission = useCallback(() => {
    mutate(undefined, {
      revalidate: true,
      optimisticData: mission,
      populateCache: (updated) => {
        if (updated) {
          return applyMission(updated);
        }
        return mission;
      },
    }).catch((err) => console.warn("Failed to refresh mission", err));
  }, [applyMission, mission, mutate]);

  const setLatestRun = useCallback((run: AgentRun | null) => {
    setLatestRunState(run);
    setMission((prev) => ({
      ...prev,
      latest_agent_run: run ?? null,
    }));
  }, []);

  const value = useMemo(
    () => ({ mission, latestRun, refreshMission, setLatestRun }),
    [mission, latestRun, refreshMission, setLatestRun],
  );

  return <MissionContext.Provider value={value}>{children}</MissionContext.Provider>;
}

export function useMission() {
  const ctx = useContext(MissionContext);
  if (!ctx) {
    throw new Error("useMission must be used within a MissionProvider");
  }
  return ctx;
}
