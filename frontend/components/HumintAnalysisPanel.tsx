"use client";

import { useEffect, useMemo, useState } from "react";

import {
  analyzeHumintIir,
  type Document,
  type HumintIirAnalysisResult,
} from "@/lib/api";

interface HumintAnalysisPanelProps {
  missionId: number;
  documents: Document[];
}

export default function HumintAnalysisPanel({ missionId, documents }: HumintAnalysisPanelProps) {
  const missionDocuments = documents ?? [];
  const hasDocuments = missionDocuments.length > 0;
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(
    missionDocuments.length ? missionDocuments[0]!.id : null,
  );
  const [analysis, setAnalysis] = useState<HumintIirAnalysisResult | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedDocument = useMemo(
    () => missionDocuments.find((doc) => doc.id === selectedDocumentId) ?? null,
    [missionDocuments, selectedDocumentId],
  );

  useEffect(() => {
    if (!hasDocuments) {
      setSelectedDocumentId(null);
      return;
    }
    if (!selectedDocumentId || !missionDocuments.some((doc) => doc.id === selectedDocumentId)) {
      setSelectedDocumentId(missionDocuments[0].id);
    }
  }, [hasDocuments, missionDocuments, selectedDocumentId]);

  const parsedFieldsEntries = useMemo(() => {
    if (!analysis?.parsed_fields) return [];
    return Object.entries(analysis.parsed_fields).filter(([, value]) => {
      if (Array.isArray(value)) {
        return value.length > 0;
      }
      return value !== null && value !== undefined && String(value).trim() !== "";
    });
  }, [analysis]);

  async function handleRunAnalysis() {
    if (!selectedDocumentId) return;
    setIsRunning(true);
    setError(null);
    try {
      const result = await analyzeHumintIir(missionId, selectedDocumentId);
      setAnalysis(result);
    } catch (err) {
      console.error("Failed to analyze HUMINT IIR", err);
      setError("Analysis failed. Please try again.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="rounded-3xl border border-slate-800/60 bg-slate-950/40 p-6 text-slate-100 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300/80">UNCLASS HUMINT Analysis</p>
          <h3 className="text-2xl font-semibold">IIR Evaluation</h3>
          <p className="text-sm text-slate-400">Select a mission document and run DIA-style HUMINT parsing.</p>
        </div>
        <div className="space-y-2 text-sm text-slate-200">
          <label className="block text-xs uppercase tracking-wide text-slate-400">
            HUMINT document
            <select
              className="mt-1 w-64 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 disabled:opacity-60"
              value={selectedDocumentId ?? ""}
              onChange={(event) => setSelectedDocumentId(event.target.value ? Number(event.target.value) : null)}
              disabled={!hasDocuments}
            >
              {!hasDocuments && <option value="">No documents</option>}
              {missionDocuments.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.title || `Document #${doc.id}`}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={!hasDocuments || !selectedDocumentId || isRunning}
            className="w-full rounded-lg border border-emerald-400/60 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/20 disabled:opacity-50"
          >
            {isRunning ? "Running analysis…" : "Run HUMINT Analysis"}
          </button>
          {!hasDocuments && (
            <p className="text-xs text-slate-500">No mission documents available for HUMINT analysis. Add a document to this mission first.</p>
          )}
          {hasDocuments && !selectedDocument && (
            <p className="text-xs text-slate-500">Select a HUMINT IIR document to analyze.</p>
          )}
          {selectedDocument && (
            <p className="text-xs text-slate-500">
              Targeting: <span className="text-slate-300">{selectedDocument.title || `Document #${selectedDocument.id}`}</span>
            </p>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-rose-700 bg-rose-950/40 px-4 py-2 text-sm text-rose-200">
          {error}
        </div>
      )}

      {analysis && (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-300">Parsed Fields</h4>
            {parsedFieldsEntries.length === 0 ? (
              <p className="mt-3 text-sm text-slate-400">No structured fields returned.</p>
            ) : (
              <dl className="mt-3 space-y-2 text-sm">
                {parsedFieldsEntries.map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-slate-800/60 bg-slate-900/50 px-3 py-2">
                    <dt className="text-xs uppercase tracking-wide text-slate-500">{key.replace(/_/g, " ")}</dt>
                    <dd className="text-slate-100">
                      {Array.isArray(value) ? value.join(", ") : String(value)}
                    </dd>
                  </div>
                ))}
              </dl>
            )}
            <div className="mt-4 text-xs text-slate-500">
              Evidence documents: {analysis.evidence_document_ids.join(", ") || "None"}
            </div>
          </div>

          <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
            <InsightList title="Key insights" emptyLabel="No insights" items={analysis.key_insights.map((item) => (
              <div key={item.title} className="space-y-1">
                <p className="font-semibold text-slate-100">{item.title}</p>
                <p className="text-sm text-slate-300">{item.detail}</p>
                <p className="text-xs text-slate-500">Confidence {Math.round(item.confidence * 100)}%</p>
              </div>
            ))} />
            <InsightList title="Contradictions" emptyLabel="No contradictions" items={analysis.contradictions.map((text) => (
              <p key={text} className="text-sm text-slate-300">{text}</p>
            ))} />
            <InsightList title="Gaps" emptyLabel="No gaps" items={analysis.gaps.map((gap) => (
              <div key={gap.title} className="space-y-1">
                <p className="font-semibold text-slate-100">{gap.title}</p>
                <p className="text-sm text-slate-300">{gap.description}</p>
                <p className="text-xs text-slate-500">Priority {gap.priority}{gap.suggested_collection ? ` • ${gap.suggested_collection}` : ""}</p>
              </div>
            ))} />
            <InsightList title="Follow-ups" emptyLabel="No follow-ups" items={analysis.followups.map((item) => (
              <div key={item.question} className="space-y-1">
                <p className="font-semibold text-slate-100">{item.question}</p>
                <p className="text-sm text-slate-300">{item.rationale}</p>
                <p className="text-xs text-slate-500">Priority {item.priority}</p>
              </div>
            ))} />
          </div>
        </div>
      )}
    </section>
  );
}

interface InsightListProps {
  title: string;
  emptyLabel: string;
  items: React.ReactNode[];
}

function InsightList({ title, emptyLabel, items }: InsightListProps) {
  return (
    <div className="rounded-2xl border border-slate-900/60 bg-slate-950/50 p-4">
      <h5 className="text-sm font-semibold uppercase tracking-wide text-slate-300">{title}</h5>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyLabel}</p>
      ) : (
        <div className="mt-3 space-y-3 text-sm text-slate-200">
          {items.map((content, idx) => (
            <div key={idx} className="rounded-xl border border-slate-800/60 bg-slate-900/40 px-3 py-2">
              {content}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
