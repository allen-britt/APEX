"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import {
  deleteDocument,
  moveDocumentToMission,
  setDocumentIncludeInAnalysis,
  type Document,
} from "@/lib/api";

interface DocumentListProps {
  missionId: number;
  documents: Document[];
}

export default function DocumentList({ missionId: _missionId, documents }: DocumentListProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [expanded, setExpanded] = useState<Record<number, boolean>>({});
  const [moveTargets, setMoveTargets] = useState<Record<number, string>>({});
  const [movingId, setMovingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [togglingId, setTogglingId] = useState<number | null>(null);

  const refresh = () =>
    startTransition(() => {
      router.refresh();
    });

  const toggleExpanded = (documentId: number) => {
    setExpanded((prev) => ({
      ...prev,
      [documentId]: !prev[documentId],
    }));
  };

  const handleDelete = async (documentId: number, title?: string | null) => {
    const label = title?.trim() || `Document ${documentId}`;
    const confirmed = window.confirm(`Delete "${label}"? This cannot be undone.`);
    if (!confirmed) return;

    setDeletingId(documentId);
    try {
      await deleteDocument(documentId);
      refresh();
    } finally {
      setDeletingId(null);
    }
  };

  const handleMove = async (documentId: number) => {
    const rawTarget = moveTargets[documentId];
    const targetId = Number(rawTarget);
    if (!rawTarget || Number.isNaN(targetId) || targetId <= 0) {
      alert("Provide a valid mission ID to move this document.");
      return;
    }

    setMovingId(documentId);
    try {
      await moveDocumentToMission(documentId, targetId);
      refresh();
    } finally {
      setMovingId(null);
    }
  };

  const handleIncludeToggle = async (documentId: number, include: boolean) => {
    setTogglingId(documentId);
    try {
      await setDocumentIncludeInAnalysis(documentId, include);
      refresh();
    } finally {
      setTogglingId(null);
    }
  };

  if (!documents.length) {
    return <p className="text-sm text-slate-400">No mission documents yet.</p>;
  }

  return (
    <div className="space-y-3">
      {documents.map((doc) => {
        const isExpanded = expanded[doc.id] ?? false;
        const include = doc.include_in_analysis ?? true;
        const preview =
          doc.content.length > 360 ? `${doc.content.slice(0, 360)}…` : doc.content;

        return (
          <div
            key={doc.id}
            className="rounded-2xl border border-slate-800 bg-slate-900/50 px-4 py-3 shadow-sm"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-1">
                <div className="text-base font-semibold text-slate-100">
                  {doc.title || `Document #${doc.id}`}
                </div>
                {doc.created_at && (
                  <p className="text-xs text-slate-500">
                    {new Date(doc.created_at).toLocaleString()}
                  </p>
                )}
                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                  <button
                    type="button"
                    onClick={() => toggleExpanded(doc.id)}
                    className="underline-offset-2 hover:underline"
                  >
                    {isExpanded ? "Collapse" : "Expand"}
                  </button>
                  <span className="text-slate-600">•</span>
                  <label className="inline-flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={include}
                      disabled={togglingId === doc.id || isPending}
                      onChange={(event) =>
                        handleIncludeToggle(doc.id, event.target.checked)
                      }
                    />
                    Include in analysis
                  </label>
                </div>
              </div>

              <div className="flex flex-col items-start gap-2 text-xs sm:items-end">
                <button
                  type="button"
                  onClick={() => handleDelete(doc.id, doc.title)}
                  disabled={deletingId === doc.id || isPending}
                  className="text-rose-400 transition hover:text-rose-200 disabled:opacity-50"
                >
                  {deletingId === doc.id ? "Deleting…" : "Delete"}
                </button>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    placeholder="Mission ID"
                    className="w-24 rounded border border-slate-700 bg-slate-950 px-2 py-1 text-xs"
                    value={moveTargets[doc.id] ?? ""}
                    onChange={(event) =>
                      setMoveTargets((prev) => ({
                        ...prev,
                        [doc.id]: event.target.value,
                      }))
                    }
                  />
                  <button
                    type="button"
                    onClick={() => handleMove(doc.id)}
                    disabled={movingId === doc.id || isPending}
                    className="rounded bg-slate-800 px-2 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-700 disabled:opacity-60"
                  >
                    {movingId === doc.id ? "Moving…" : "Move"}
                  </button>
                </div>
              </div>
            </div>

            <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950/40 p-3 text-sm text-slate-200 whitespace-pre-wrap">
              {isExpanded ? doc.content : preview}
            </div>
          </div>
        );
      })}
    </div>
  );
}
