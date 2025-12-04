import Link from "next/link";

import type { Mission } from "@/lib/api";
import { MissionActions } from "@/components/MissionActions";
import PolicyFootprint from "@/components/PolicyFootprint";

interface MissionListProps {
  missions: Mission[];
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function MissionList({ missions }: MissionListProps) {
  if (!missions.length) {
    return (
      <div className="card">
        <p className="text-sm text-slate-400">No missions yet. Create one above.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {missions.map((mission) => (
        <div key={mission.id} className="card">
          <div className="flex items-start justify-between gap-4">
            <div>
              <Link
                href={`/missions/${mission.id}`}
                className="text-lg font-semibold text-cyan-300 hover:text-cyan-200"
              >
                {mission.name}
              </Link>
              {mission.description && (
                <p className="mt-1 text-sm text-slate-400 line-clamp-2">{mission.description}</p>
              )}
              <PolicyFootprint mission={mission} layout="inline" showSecondary={false} />
            </div>
            <div className="flex flex-col items-end gap-1 text-right">
              <span className="text-xs uppercase tracking-wide text-slate-500">
                {formatDate(mission.created_at)}
              </span>
              <MissionActions missionId={mission.id} missionName={mission.name} />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
