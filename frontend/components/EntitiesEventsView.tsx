"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

import type { Entity, Event } from "@/lib/api";
import {
  clearMissionEntities,
  clearMissionEvents,
  deleteEntity,
  deleteEvent,
} from "@/lib/api";

interface EntitiesEventsViewProps {
  missionId: number;
  entities: Entity[];
  events: Event[];
}

function formatDate(value?: string | null) {
  if (!value) return "Unknown";
  return new Date(value).toLocaleString();
}

export default function EntitiesEventsView({ missionId, entities, events }: EntitiesEventsViewProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const confirmAndRun = (message: string, action: () => Promise<void>) => {
    const confirmed = window.confirm(message);
    if (!confirmed) return;
    startTransition(async () => {
      try {
        await action();
        router.refresh();
      } catch (error) {
        console.error("Failed to update graph", error);
        alert("Failed to update entities/events. Please try again.");
      }
    });
  };

  return (
    <div className="grid gap-6 md:grid-cols-2">
      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Entities</h3>
          <button
            type="button"
            className="rounded border border-slate-600 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-800 disabled:opacity-60"
            disabled={isPending || entities.length === 0}
            onClick={() =>
              confirmAndRun(
                "Delete all entities for this mission?",
                () => clearMissionEntities(missionId),
              )
            }
          >
            {isPending ? "Working…" : "Clear all"}
          </button>
        </div>
        {entities.length === 0 ? (
          <p className="text-sm text-slate-400">No entities extracted yet.</p>
        ) : (
          <ul className="space-y-3">
            {entities.map((entity) => (
              <li key={entity.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-cyan-200">{entity.name}</p>
                    {entity.type && (
                      <p className="text-xs uppercase tracking-wide text-slate-500">{entity.type}</p>
                    )}
                  </div>
                  <button
                    type="button"
                    className="text-xs text-rose-300 hover:text-rose-200 disabled:opacity-60"
                    onClick={() =>
                      confirmAndRun(
                        "Delete this entity?",
                        () => deleteEntity(entity.id),
                      )
                    }
                    disabled={isPending}
                  >
                    Delete
                  </button>
                </div>
                {entity.description && (
                  <p className="mt-1 text-sm text-slate-300">{entity.description}</p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Events</h3>
          <button
            type="button"
            className="rounded border border-slate-600 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-800 disabled:opacity-60"
            disabled={isPending || events.length === 0}
            onClick={() =>
              confirmAndRun(
                "Delete all events for this mission?",
                () => clearMissionEvents(missionId),
              )
            }
          >
            {isPending ? "Working…" : "Clear all"}
          </button>
        </div>
        {events.length === 0 ? (
          <p className="text-sm text-slate-400">No events extracted yet.</p>
        ) : (
          <ul className="space-y-3">
            {events.map((event) => (
              <li key={event.id} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-cyan-200">{event.title}</p>
                    <p className="text-xs text-slate-500">
                      {formatDate(event.timestamp)}
                      {event.location ? ` • ${event.location}` : ""}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="text-xs text-rose-300 hover:text-rose-200 disabled:opacity-60"
                    onClick={() =>
                      confirmAndRun(
                        "Delete this event?",
                        () => deleteEvent(event.id),
                      )
                    }
                    disabled={isPending}
                  >
                    Delete
                  </button>
                </div>
                {event.summary && <p className="mt-1 text-sm text-slate-300">{event.summary}</p>}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
