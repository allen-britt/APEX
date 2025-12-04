"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import type { MissionDataset } from "@/lib/api";
import { buildMissionDatasetSemanticProfile } from "@/lib/api";

interface MissionDatasetListProps {
  missionId: number;
  datasets: MissionDataset[];
}

type TableProfile = {
  name?: string;
  row_count?: number;
};

type ColumnSemantic = {
  name?: string;
  semantic_type?: string;
  confidence?: number;
  role?: string;
  notes?: string;
};

function extractTables(profile: unknown): TableProfile[] {
  if (!profile || typeof profile !== "object") {
    return [];
  }

  const maybeTables = (profile as { tables?: unknown }).tables;
  if (!Array.isArray(maybeTables)) {
    return [];
  }

  return maybeTables
    .filter((table): table is Record<string, unknown> => Boolean(table) && typeof table === "object")
    .map((table) => {
      const name = table.name;
      const rowCount = table.row_count;
      return {
        name: typeof name === "string" ? name : undefined,
        row_count: typeof rowCount === "number" ? rowCount : undefined,
      };
    });
}

function extractColumnSemantics(semanticProfile: unknown): ColumnSemantic[] {
  if (!semanticProfile || typeof semanticProfile !== "object") {
    return [];
  }

  const maybeColumns = (semanticProfile as { columns?: unknown }).columns;
  if (!Array.isArray(maybeColumns)) {
    return [];
  }

  return maybeColumns
    .filter((col): col is Record<string, unknown> => Boolean(col) && typeof col === "object")
    .map((col) => ({
      name: typeof col.name === "string" ? col.name : undefined,
      semantic_type: typeof col.semantic_type === "string" ? col.semantic_type : undefined,
      confidence: typeof col.confidence === "number" ? col.confidence : undefined,
      role: typeof col.role === "string" ? col.role : undefined,
      notes: typeof col.notes === "string" ? col.notes : undefined,
    }));
}

function formatConfidence(value?: number) {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "—";
  }
  return `${Math.round(value * 100)}%`;
}

function formatTimestamp(value?: string) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function statusStyles(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "ready") {
    return "bg-emerald-500/20 text-emerald-300";
  }
  if (normalized === "building") {
    return "bg-amber-500/20 text-amber-200";
  }
  return "bg-slate-600/30 text-slate-200";
}

export default function MissionDatasetList({ missionId, datasets }: MissionDatasetListProps) {
  const router = useRouter();
  const [pendingId, setPendingId] = useState<number | null>(null);
  const [openSemanticId, setOpenSemanticId] = useState<number | null>(null);

  async function handleSemanticProfile(datasetId: number) {
    try {
      setPendingId(datasetId);
      await buildMissionDatasetSemanticProfile(missionId, datasetId);
      router.refresh();
    } catch (error) {
      console.error("Failed to build semantic profile", error);
    } finally {
      setPendingId(null);
    }
  }

  function toggleSemanticView(datasetId: number) {
    setOpenSemanticId((current) => (current === datasetId ? null : datasetId));
  }

  if (!datasets.length) {
    return (
      <div className="card">
        <p className="text-sm text-slate-400">
          No mission datasets yet. Create one to see AggreGator profiles.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {datasets.map((dataset) => {
        const tables = extractTables(dataset.profile);
        const tablesCount = tables.length || undefined;
        const totalRows = tables.reduce(
          (sum, table) =>
            sum + (typeof table.row_count === "number" ? table.row_count : 0),
          0,
        );
        const columnSemantics = extractColumnSemantics(dataset.semantic_profile);
        const hasSemanticProfile = columnSemantics.length > 0;

        return (
          <div
            key={dataset.id}
            className="rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-3 shadow-sm"
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-base font-semibold text-slate-100">
                  {dataset.name}
                </p>
                <p className="text-xs text-slate-500">
                  Created {formatTimestamp(dataset.created_at)}
                </p>
              </div>
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${statusStyles(
                  dataset.status,
                )}`}
              >
                {dataset.status}
              </span>
            </div>

            <div className="mt-3 flex flex-wrap gap-4 text-sm text-slate-300">
              <div>
                <p className="text-xs text-slate-500">Tables</p>
                <p className="font-semibold text-slate-100">
                  {tablesCount ?? "—"}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Rows (total)</p>
                <p className="font-semibold text-slate-100">
                  {totalRows || "—"}
                </p>
              </div>
            </div>

            {tablesCount ? (
              <div className="mt-3 space-y-1 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-xs text-slate-300">
                {tables.slice(0, 3).map((table, index) => (
                  <div
                    key={`${table.name ?? "table"}-${index}`}
                    className="flex items-center justify-between"
                  >
                    <span className="font-medium text-slate-100">
                      {table.name ?? `Table ${index + 1}`}
                    </span>
                    <span>
                      {typeof table.row_count === "number"
                        ? `${table.row_count} rows`
                        : "?"}
                    </span>
                  </div>
                ))}
                {tablesCount > 3 && (
                  <p className="text-right text-slate-500">
                    +{tablesCount - 3} more
                  </p>
                )}
              </div>
            ) : null}

            <div className="mt-4 flex flex-col gap-3 border-t border-slate-800 pt-3">
              <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                <span>
                  Semantic profile: {hasSemanticProfile ? "ready" : "not generated"}
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleSemanticProfile(dataset.id)}
                    disabled={pendingId === dataset.id}
                    className="inline-flex items-center rounded-md border border-indigo-400 px-3 py-1 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {pendingId === dataset.id ? "Profiling…" : "Build semantic profile"}
                  </button>
                  {hasSemanticProfile ? (
                    <button
                      type="button"
                      onClick={() => toggleSemanticView(dataset.id)}
                      className="inline-flex items-center rounded-md border border-slate-600 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-800"
                    >
                      {openSemanticId === dataset.id
                        ? "Hide column semantics"
                        : "View column semantics"}
                    </button>
                  ) : null}
                </div>
              </div>

              {openSemanticId === dataset.id && hasSemanticProfile ? (
                <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs text-slate-200">
                  <div className="mb-2 flex items-center justify-between text-[11px] uppercase tracking-wide text-slate-500">
                    <span>Column</span>
                    <span className="w-24 text-center">Confidence</span>
                  </div>
                  <div className="space-y-2">
                    {columnSemantics.map((column) => (
                      <div
                        key={column.name ?? column.role ?? crypto.randomUUID()}
                        className="rounded-lg border border-slate-900 bg-slate-900/60 p-2"
                      >
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                          <div>
                            <p className="text-sm font-semibold text-slate-50">
                              {column.name ?? "Unnamed column"}
                            </p>
                            <p className="text-[11px] uppercase tracking-wide text-indigo-300">
                              {column.semantic_type ?? "Unknown type"}
                            </p>
                          </div>
                          <span className="inline-flex items-center rounded-full border border-slate-700 px-2 py-0.5 text-[11px] font-semibold text-slate-200">
                            {formatConfidence(column.confidence)}
                          </span>
                        </div>
                        <p className="mt-2 text-[11px] text-slate-400">
                          Role: <span className="text-slate-100">{column.role ?? "n/a"}</span>
                        </p>
                        {column.notes ? (
                          <p className="text-[11px] text-slate-400">Notes: {column.notes}</p>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
}
