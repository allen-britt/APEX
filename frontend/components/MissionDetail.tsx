import type { Mission } from "@/lib/api";

interface MissionDetailProps {
  mission: Mission;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function MissionDetail({ mission }: MissionDetailProps) {
  return (
    <div className="card space-y-2">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-500">Mission</p>
        <h2 className="text-2xl font-semibold text-cyan-100">{mission.name}</h2>
      </div>
      {mission.description && (
        <p className="text-sm text-slate-300 leading-relaxed">{mission.description}</p>
      )}
      <div className="text-xs text-slate-500">
        <span>Created: {formatDate(mission.created_at)}</span>
        <span className="mx-2">•</span>
        <span>Updated: {formatDate(mission.updated_at)}</span>
      </div>
    </div>
  );
}
