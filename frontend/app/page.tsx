import MissionBoard from "@/components/MissionBoard";
import { fetchMissions } from "@/lib/api";

import type { Mission } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  let missions: Mission[] = [];
  let error: string | null = null;

  try {
    missions = await fetchMissions();
  } catch (err) {
    console.error("Failed to load missions", err);
    error = "Unable to load missions. Check backend availability.";
  }

  return (
    <section className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-cyan-100">APEX – Missions</h1>
        <p className="text-sm text-slate-400">
          Review current operations or create a new mission package.
        </p>
      </div>

      {error ? (
        <div className="card border border-rose-800 bg-rose-950/40 text-sm text-rose-200">
          {error}
        </div>
      ) : (
        <MissionBoard initialMissions={missions} />
      )}
    </section>
  );
}
