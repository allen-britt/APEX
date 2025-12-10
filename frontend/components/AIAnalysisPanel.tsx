"use client";

import { useMemo, useState } from "react";

import type { Document, GenericAnalysisResult, FollowUpQuestion } from "@/lib/api";
import { runGenericAnalysis } from "@/lib/api";

interface AIAnalysisPanelProps {
  missionId: number;
  documents: Document[];
  profile?: "humint" | "generic";
}

export default function AIAnalysisPanel({ missionId, documents, profile = "humint" }: AIAnalysisPanelProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [result, setResult] = useState<GenericAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasDocuments = documents.length > 0;
  const formDisabled = !hasDocuments || loading;
  const runDisabled = !hasDocuments || selectedIds.length === 0 || loading;

  function toggleDocument(id: number) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((value) => value !== id) : [...prev, id]));
  }

  function selectAll() {
    if (!hasDocuments) return;
    setSelectedIds(documents.map((doc) => doc.id));
  }

  function clearSelection() {
    setSelectedIds([]);
  }

  async function handleRunAnalysis() {
    if (selectedIds.length === 0) return;
    setLoading(true);
    setError(null);
    try {
      const payload = await runGenericAnalysis({
        mission_id: missionId,
        document_ids: selectedIds,
        profile,
      });
      setResult(payload);
    } catch (err) {
      console.error("generic-analysis: failed", err);
      const message = err instanceof Error ? err.message : "Analysis failed. Please try again.";
      setError(message);
    } finally {
      setLoading(false);
    }
  }

  const selectionSummary = useMemo(() => {
    if (selectedIds.length === 0) return "No documents selected";
    if (selectedIds.length === 1) return `1 document selected`;
    return `${selectedIds.length} documents selected`;
  }, [selectedIds.length]);

  return (
    <section className="space-y-4 rounded-3xl border border-emerald-500/30 bg-slate-950/30 p-5 text-slate-100 shadow-[0_20px_45px_rgba(0,0,0,0.45)]">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300/80">AI Fusion</p>
          <h3 className="text-2xl font-semibold">Mission document analysis</h3>
          <p className="text-sm text-slate-400">Select mission documents and ask the LLM for a HUMINT-style summary.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-300">
          <button
            type="button"
            onClick={selectAll}
            disabled={formDisabled}
            className="rounded border border-emerald-400/50 px-2 py-1 font-semibold uppercase tracking-wide text-emerald-200 transition hover:bg-emerald-400/10 disabled:opacity-50"
          >
            Select all
          </button>
          <button
            type="button"
            onClick={clearSelection}
            disabled={formDisabled || selectedIds.length === 0}
            className="rounded border border-slate-700 px-2 py-1 font-semibold uppercase tracking-wide text-slate-300 transition hover:bg-slate-800/60 disabled:opacity-50"
          >
            Clear
          </button>
        </div>
      </header>

      {!hasDocuments && (
        <p className="text-sm text-slate-400">Add documents to this mission to enable AI analysis.</p>
      )}

      {hasDocuments && (
        <div className="max-h-56 overflow-auto rounded-2xl border border-slate-800/80 bg-slate-950/40">
          <ul className="divide-y divide-slate-800/80 text-sm">
            {documents.map((doc) => (
              <li key={doc.id} className="flex items-start gap-3 px-4 py-3">
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900 text-emerald-400 focus:ring-emerald-500"
                  checked={selectedIds.includes(doc.id)}
                  onChange={() => toggleDocument(doc.id)}
                  disabled={formDisabled}
                />
                <div>
                  <p className="font-semibold text-slate-100">{doc.title || `Document #${doc.id}`}</p>
                  <p className="text-xs text-slate-500">ID: {doc.id}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <p className="text-xs uppercase tracking-wide text-slate-400">{selectionSummary}</p>
        <button
          type="button"
          onClick={handleRunAnalysis}
          disabled={runDisabled}
          className="rounded-xl border border-emerald-400/70 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200 transition hover:bg-emerald-500/20 disabled:opacity-50"
        >
          {loading ? "Running analysis…" : "Run AI Analysis"}
        </button>
        {error && <p className="text-xs text-rose-300">{error}</p>}
      </div>

      {result ? <AnalysisResult result={result} /> : null}
    </section>
  );
}

function AnalysisResult({ result }: { result: GenericAnalysisResult }) {
  return (
    <div className="space-y-5 rounded-2xl border border-slate-800/80 bg-slate-950/40 p-4">
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-400">Profile</p>
        <p className="text-sm font-semibold text-emerald-200">{result.profile}</p>
      </div>
      <TextBlock title="Summary" content={result.summary} />
      <ListBlock title="Key entities" items={result.key_entities} emptyLabel="No entities" />
      <ListBlock title="Key events" items={result.key_events} emptyLabel="No events" />
      <ListBlock title="Contradictions" items={result.contradictions} emptyLabel="No contradictions" />
      <ListBlock title="Gaps" items={result.gaps} emptyLabel="No gaps" />
      <FollowUpList questions={result.follow_up_questions} />
      <TextBlock title="Decision note" content={result.decision_note} />
    </div>
  );
}

function TextBlock({ title, content }: { title: string; content: string }) {
  return (
    <div>
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h4>
      <p className="mt-2 text-sm text-slate-200">{content || "No content returned."}</p>
    </div>
  );
}

function ListBlock({
  title,
  items,
  emptyLabel,
}: {
  title: string;
  items: string[];
  emptyLabel: string;
}) {
  return (
    <div>
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">{title}</h4>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">{emptyLabel}</p>
      ) : (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function FollowUpList({ questions }: { questions: FollowUpQuestion[] }) {
  return (
    <div>
      <h4 className="text-sm font-semibold uppercase tracking-wide text-slate-400">Follow-up questions</h4>
      {questions.length === 0 ? (
        <p className="mt-2 text-sm text-slate-500">No follow-ups</p>
      ) : (
        <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-200">
          {questions.map((q, index) => (
            <li key={`${q.target}-${index}`}>
              <span className="font-semibold text-emerald-200">{q.target}:</span> {q.question}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
