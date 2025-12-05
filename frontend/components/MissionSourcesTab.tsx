"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";

import {
  deleteMissionSourceDocument,
  fetchMissionSourceDocuments,
  ingestMissionDocumentUrl,
  uploadMissionSourceFile,
  type Mission,
  type MissionSourceDocument,
} from "@/lib/api";
import { formatIntLabel, listIntOptions } from "@/lib/policy";

interface MissionSourcesTabProps {
  missionId: number;
  mission: Mission;
}

function KgImpact({
  nodesBefore,
  nodesAfter,
  edgesBefore,
  edgesAfter,
  status,
}: {
  nodesBefore?: number | null;
  nodesAfter?: number | null;
  edgesBefore?: number | null;
  edgesAfter?: number | null;
  status?: string | null;
}) {
  if (status?.toUpperCase() === "FAILED") {
    return <span className="text-xs text-rose-300">Failed</span>;
  }
  if (status?.toUpperCase() === "PENDING" || status?.toUpperCase() === "RUNNING") {
    return <span className="text-xs text-slate-400">Pending…</span>;
  }
  if (
    nodesBefore == null ||
    nodesAfter == null ||
    edgesBefore == null ||
    edgesAfter == null
  ) {
    return <span className="text-xs text-slate-500">No metrics</span>;
  }
  const nodeDelta = nodesAfter - nodesBefore;
  const edgeDelta = edgesAfter - edgesBefore;
  const nodeText = nodeDelta >= 0 ? `+${nodeDelta}` : `${nodeDelta}`;
  const edgeText = edgeDelta >= 0 ? `+${edgeDelta}` : `${edgeDelta}`;
  return (
    <span className="text-xs font-mono text-slate-100">
      KG: {nodeText} nodes / {edgeText} edges
    </span>
  );
}

const STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-amber-500/20 text-amber-300 border border-amber-400/40",
  INGESTED: "bg-emerald-500/20 text-emerald-200 border border-emerald-400/40",
  FAILED: "bg-rose-500/20 text-rose-200 border border-rose-400/40",
};

const INGEST_STATUS_STYLES: Record<string, string> = {
  PENDING: "bg-slate-700/60 border border-slate-500 text-slate-100",
  RUNNING: "bg-indigo-500/20 border border-indigo-400 text-indigo-200",
  SUCCESS: "bg-emerald-500/20 border border-emerald-400 text-emerald-100",
  FAILED: "bg-rose-500/20 border border-rose-400 text-rose-100",
};

type MissionSourceRow = MissionSourceDocument & {
  mission_document_id?: string | number | null;
  mission_document?: { id?: string | number | null } | null;
  document_id?: string | number | null;
  document?: { id?: string | number | null } | null;
};

function resolveMissionSourceId(row: MissionSourceRow): string | null {
  const candidates: Array<string | number | null | undefined> = [
    row.mission_document_id,
    row.mission_document?.id,
    row.document_id,
    row.document?.id,
    row.id,
  ];

  for (const raw of candidates) {
    if (raw == null) {
      continue;
    }

    if (typeof raw === "number") {
      if (Number.isFinite(raw)) {
        return String(Math.trunc(raw));
      }
      continue;
    }

    const trimmed = String(raw).trim();
    if (!trimmed || trimmed.toLowerCase() === "nan") {
      continue;
    }

    const numericValue = Number(trimmed);
    if (Number.isFinite(numericValue) && !Number.isNaN(numericValue)) {
      return String(Math.trunc(numericValue));
    }

    return trimmed;
  }

  return null;
}

export default function MissionSourcesTab({ missionId, mission }: MissionSourcesTabProps) {
  const intOptions = useMemo(() => listIntOptions(), []);
  const { data, error, isLoading, mutate } = useSWR(["mission-sources", missionId], () =>
    fetchMissionSourceDocuments(missionId),
  );
  const documents: MissionSourceRow[] = (data ?? []) as MissionSourceRow[];

  const [file, setFile] = useState<File | null>(null);
  const [fileTitle, setFileTitle] = useState("");
  const [filePrimaryInt, setFilePrimaryInt] = useState("");
  const [fileInts, setFileInts] = useState<string[]>([]);
  const [fileError, setFileError] = useState<string | null>(null);
  const [fileSubmitting, setFileSubmitting] = useState(false);

  const [urlValue, setUrlValue] = useState("");
  const [urlTitle, setUrlTitle] = useState("");
  const [urlPrimaryInt, setUrlPrimaryInt] = useState("");
  const [urlInts, setUrlInts] = useState<string[]>([]);
  const [urlError, setUrlError] = useState<string | null>(null);
  const [urlSubmitting, setUrlSubmitting] = useState(false);

  const [deletingDocumentId, setDeletingDocumentId] = useState<string | null>(null);

  async function handleDeleteDocument(doc: MissionSourceRow) {
    const documentId = resolveMissionSourceId(doc);
    if (!documentId) {
      console.error("Cannot delete mission document – unresolved ID", doc);
      alert("Unable to determine document ID for deletion.");
      return;
    }

    console.log("Deleting doc with ID:", documentId, doc);

    const confirmed = window.confirm("Delete this source file? This cannot be undone.");
    if (!confirmed) {
      return;
    }

    setDeletingDocumentId(documentId);
    try {
      await deleteMissionSourceDocument(missionId, documentId);
      await mutate();
    } catch (err) {
      console.error("Failed to delete mission document", err);
      alert("Failed to delete document. Please try again.");
    } finally {
      setDeletingDocumentId(null);
    }
  }

  const namespaceReady = Boolean(mission.kg_namespace);
  const ingestedCount = documents.filter((doc) => doc.status === "INGESTED").length;
  const failedCount = documents.filter((doc) => doc.status === "FAILED").length;
  const latestDoc = documents[0];

  const lastUpdatedLabel = latestDoc
    ? new Date(latestDoc.created_at).toLocaleString()
    : "No ingests yet";

  const effectiveStatus = !namespaceReady
    ? "Namespace pending"
    : ingestedCount > 0
      ? "Ready"
      : documents.length > 0
        ? "Awaiting ingest"
        : "No sources";

  async function handleFileSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setFileError("Select a file to upload.");
      return;
    }
    setFileSubmitting(true);
    setFileError(null);
    try {
      await uploadMissionSourceFile(missionId, {
        file,
        title: fileTitle.trim() || undefined,
        primary_int: filePrimaryInt || undefined,
        int_types: fileInts,
      });
      setFile(null);
      setFileTitle("");
      setFilePrimaryInt("");
      setFileInts([]);
      mutate();
    } catch (err) {
      console.error("Mission file upload failed", err);
      setFileError(err instanceof Error ? err.message : "Failed to upload file");
    } finally {
      setFileSubmitting(false);
    }
  }

  async function handleUrlSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!urlValue.trim()) {
      setUrlError("Provide a valid URL.");
      return;
    }
    setUrlSubmitting(true);
    setUrlError(null);
    try {
      await ingestMissionDocumentUrl(missionId, {
        url: urlValue.trim(),
        title: urlTitle.trim() || undefined,
        primary_int: urlPrimaryInt || undefined,
        int_types: urlInts,
      });
      setUrlValue("");
      setUrlTitle("");
      setUrlPrimaryInt("");
      setUrlInts([]);
      mutate();
    } catch (err) {
      console.error("Mission URL ingest failed", err);
      setUrlError(err instanceof Error ? err.message : "Failed to ingest URL");
    } finally {
      setUrlSubmitting(false);
    }
  }

  const toggleIntSelection = (value: string, setter: (next: string[]) => void, current: string[]) => {
    setter(current.includes(value) ? current.filter((code) => code !== value) : [...current, value]);
  };

  return (
    <div className="space-y-8">
      <section className="grid gap-6 xl:grid-cols-3">
        <div className="card space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold">KG health</h3>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                namespaceReady ? "bg-emerald-500/20 text-emerald-200" : "bg-amber-500/20 text-amber-200"
              }`}
            >
              {effectiveStatus}
            </span>
          </div>
          <dl className="grid gap-2 text-sm text-slate-300">
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Namespace</dt>
              <dd className="font-mono text-xs text-slate-200">
                {mission.kg_namespace ?? "mission-<pending>"}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Ingested</dt>
              <dd>{ingestedCount}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Failed</dt>
              <dd className={failedCount ? "text-rose-300" : undefined}>{failedCount}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-400">Last ingest</dt>
              <dd>{lastUpdatedLabel}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">
            Mission authority {mission.primary_authority ?? "(unknown)"} with INT lanes:
            {" "}
            {mission.int_types?.length ? mission.int_types.map((code) => formatIntLabel(code)).join(", ") : "None specified"}
          </p>
        </div>

        <form onSubmit={handleFileSubmit} className="card space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold">Upload file</h3>
            <p className="text-sm text-slate-400">
              Drop PDFs, text, or other intel. Files are ingested directly into this mission’s KG namespace.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="source-file-input">
              File
            </label>
            <input
              id="source-file-input"
              type="file"
              className="block w-full cursor-pointer rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              onChange={(event) => {
                const nextFile = event.target.files?.[0] ?? null;
                setFile(nextFile);
              }}
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="source-file-title">
              Title (optional)
            </label>
            <input
              id="source-file-title"
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={fileTitle}
              onChange={(event) => setFileTitle(event.target.value)}
              placeholder="SIGINT intercept summary"
            />
          </div>
          {renderIntControls({
            primaryInt: filePrimaryInt,
            selectedInts: fileInts,
            onPrimaryChange: setFilePrimaryInt,
            onToggle: (code) => toggleIntSelection(code, setFileInts, fileInts),
            intOptions,
          })}
          {fileError && <p className="text-sm text-rose-300">{fileError}</p>}
          <button
            type="submit"
            disabled={fileSubmitting}
            className="inline-flex items-center justify-center rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {fileSubmitting ? "Uploading…" : "Upload file"}
          </button>
        </form>

        <form onSubmit={handleUrlSubmit} className="card space-y-4">
          <div className="space-y-1">
            <h3 className="text-lg font-semibold">Ingest URL or feed</h3>
            <p className="text-sm text-slate-400">
              Fetch open source intel (OSINT) directly into the KG. Provide the canonical URL and optional overrides.
            </p>
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="source-url-input">
              URL
            </label>
            <input
              id="source-url-input"
              type="url"
              required
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={urlValue}
              onChange={(event) => setUrlValue(event.target.value)}
              placeholder="https://example.com/article"
            />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="source-url-title">
              Title (optional)
            </label>
            <input
              id="source-url-title"
              className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
              value={urlTitle}
              onChange={(event) => setUrlTitle(event.target.value)}
              placeholder="Daily patrol report"
            />
          </div>
          {renderIntControls({
            primaryInt: urlPrimaryInt,
            selectedInts: urlInts,
            onPrimaryChange: setUrlPrimaryInt,
            onToggle: (code) => toggleIntSelection(code, setUrlInts, urlInts),
            intOptions,
          })}
          {urlError && <p className="text-sm text-rose-300">{urlError}</p>}
          <button
            type="submit"
            disabled={urlSubmitting}
            className="inline-flex items-center justify-center rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {urlSubmitting ? "Ingesting…" : "Ingest URL"}
          </button>
        </form>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold">Source ingest status</h3>
          {isLoading && <span className="text-xs text-slate-400">Loading…</span>}
        </div>
        {error && (
          <div className="rounded border border-rose-800 bg-rose-950/40 p-3 text-sm text-rose-100">
            Failed to load mission sources. {error instanceof Error ? error.message : "Unknown error"}
          </div>
        )}
        {documents.length === 0 && !isLoading ? (
          <div className="rounded border border-dashed border-slate-700 bg-slate-950/30 p-6 text-center text-sm text-slate-400">
            No source documents yet. Upload a file or ingest a URL to seed the mission KG.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/40">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-900/70 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-3 text-left">Title</th>
                  <th className="px-4 py-3 text-left">Source</th>
                  <th className="px-4 py-3 text-left">INT Tags</th>
                  <th className="px-4 py-3 text-left">Document</th>
                  <th className="px-4 py-3 text-left">Ingest job</th>
                  <th className="px-4 py-3 text-left">KG impact</th>
                  <th className="px-4 py-3 text-left">Timestamp</th>
                  <th className="px-4 py-3 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((doc, index) => {
                  const resolvedId = resolveMissionSourceId(doc);
                  const isDeleting = resolvedId ? deletingDocumentId === resolvedId : false;
                  const rowKey = resolvedId ?? doc.id ?? doc.document_id ?? doc.document?.id ?? `row-${index}`;
                  return (
                    <tr key={rowKey} className="border-t border-slate-800 text-slate-100">
                    <td className="px-4 py-3">
                      <div className="font-semibold">
                        {doc.title || doc.original_path || `Doc ${doc.id}`}
                      </div>
                      {doc.aggregator_doc_id && (
                        <div className="text-xs text-slate-500">Agg ID: {doc.aggregator_doc_id}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      <span className="rounded-full border border-slate-700 px-2 py-0.5 text-xs">
                        {doc.source_type.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        {doc.primary_int && (
                          <span className="rounded-full border border-slate-600 bg-slate-900/60 px-2 py-0.5 text-xs text-cyan-200">
                            {formatIntLabel(doc.primary_int)}
                          </span>
                        )}
                        {doc.int_types
                          .filter((code) => code !== doc.primary_int)
                          .map((code) => (
                            <span
                              key={code}
                              className="rounded-full border border-slate-700 bg-slate-900/40 px-2 py-0.5 text-xs text-slate-200"
                            >
                              {formatIntLabel(code)}
                            </span>
                          ))}
                        {doc.primary_int === undefined && doc.int_types.length === 0 && (
                          <span className="text-xs text-slate-500">None</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-3">
                      <IngestStatusBadge status={doc.ingest_status} />
                      {doc.ingest_error && (
                        <p className="mt-1 text-xs text-rose-300">{doc.ingest_error}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-200">
                      <KgImpact
                        nodesBefore={doc.kg_nodes_before}
                        nodesAfter={doc.kg_nodes_after}
                        edgesBefore={doc.kg_edges_before}
                        edgesAfter={doc.kg_edges_after}
                        status={doc.ingest_status}
                      />
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {new Date(doc.created_at).toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="rounded border border-rose-500/60 px-3 py-1 text-xs font-semibold text-rose-200 transition hover:bg-rose-600/10 disabled:opacity-50"
                        onClick={() => handleDeleteDocument(doc)}
                        disabled={!resolvedId || isDeleting}
                      >
                        {isDeleting ? "Deleting…" : "Delete"}
                      </button>
                    </td>
                  </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

interface IntControlProps {
  primaryInt: string;
  selectedInts: string[];
  onPrimaryChange: (value: string) => void;
  onToggle: (code: string) => void;
  intOptions: ReturnType<typeof listIntOptions>;
}

function renderIntControls({
  primaryInt,
  selectedInts,
  onPrimaryChange,
  onToggle,
  intOptions,
}: IntControlProps) {
  return (
    <div className="space-y-3">
      <div className="space-y-2">
        <label className="text-sm font-medium" htmlFor="primary-int-select">
          Primary INT (optional)
        </label>
        <select
          id="primary-int-select"
          value={primaryInt}
          onChange={(event) => onPrimaryChange(event.target.value)}
          className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        >
          <option value="">None</option>
          {intOptions.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <p className="text-sm font-medium">INT tags</p>
        <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
          {intOptions.map((option) => {
            const checked = selectedInts.includes(option.code);
            return (
              <label
                key={option.code}
                className={`inline-flex cursor-pointer items-center gap-2 rounded border px-2 py-1 transition ${
                  checked ? "border-cyan-400 bg-cyan-900/30" : "border-slate-700 bg-slate-950"
                }`}
              >
                <input
                  type="checkbox"
                  className="h-3 w-3"
                  checked={checked}
                  onChange={() => onToggle(option.code)}
                />
                <span>{option.label}</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const normalized = status?.toUpperCase?.() ?? "";
  const style = STATUS_STYLES[normalized] ?? "bg-slate-800 text-slate-200 border border-slate-700";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}>
      {normalized || "UNKNOWN"}
    </span>
  );
}

function IngestStatusBadge({ status }: { status?: string | null }) {
  const normalized = status?.toUpperCase?.() ?? "";
  const style = normalized ? INGEST_STATUS_STYLES[normalized] : "bg-slate-800 text-slate-200 border border-dashed border-slate-600";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${style}`}>
      {normalized || "NOT SCHEDULED"}
    </span>
  );
}
