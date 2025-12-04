"use client";

import { useMemo, useState } from "react";

import type { Mission } from "@/lib/api";
import MissionForm from "@/components/MissionForm";
import MissionList from "@/components/MissionList";

interface MissionBoardProps {
  initialMissions: Mission[];
}

export default function MissionBoard({ initialMissions }: MissionBoardProps) {
  const [missions, setMissions] = useState<Mission[]>(initialMissions);

  const orderedMissions = useMemo(
    () => [...missions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [missions],
  );

  function handleMissionCreated(mission: Mission) {
    setMissions((prev) => [mission, ...prev.filter((existing) => existing.id !== mission.id)]);
  }

  return (
    <div className="space-y-8">
      <MissionForm onCreated={handleMissionCreated} />
      <MissionList missions={orderedMissions} />
    </div>
  );
}
