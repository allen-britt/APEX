  "use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import DecisionContextPanel from "@/components/DecisionContextPanel";
import GuardrailBadge from "@/components/GuardrailBadge";
import { TemplateReportDebugPanel } from "@/components/TemplateReportDebugPanel";
import { TEMPLATE_DEFINITIONS, TEMPLATE_DEFINITION_MAP } from "@/components/templateDefinitions";
import type {
  AgentRun,
  DecisionDataset,
  Mission,
  ReportTemplate,
  ReportTemplateSection,
  TemplateReportRecord,
  TemplateReportResponse,
} from "@/lib/api";
import {
  fetchMissionReportTemplates,
  fetchTemplateReportHistory,
  generateTemplateReport,
  type ReportTemplateId,
} from "@/lib/api";
import { describeAuthority, formatIntLabel } from "@/lib/policy";

type TemplateReportVariant = "compact" | "full";

interface TemplateReportGeneratorProps {
  missionId: number;
  variant?: TemplateReportVariant;
  mission?: Mission;
  guardrailStatus?: string;
  guardrailIssues?: string[];
}

interface ReportContextPanelProps {
  guardrailStatus?: string;
  guardrailIssues?: string[];
  kgSummary?: string | null;
  latestRunTimestamp?: string;
}

function ReportContextPanel({ guardrailStatus, guardrailIssues = [], kgSummary, latestRunTimestamp }: ReportContextPanelProps) {
  if (!guardrailStatus && !kgSummary && !latestRunTimestamp) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-2xl border border-slate-800 bg-slate-950/40 p-4 text-xs text-slate-300">
      <p className="text-[10px] uppercase tracking-wide text-slate-500">Report context</p>
      {guardrailStatus ? (
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-slate-400">Guardrail posture</span>
          <GuardrailBadge status={guardrailStatus} issues={guardrailIssues} />
        </div>
      ) : null}
      {kgSummary ? (
        <div>
          <span className="text-[11px] text-slate-400">KG snapshot summary</span>
          <p className="text-slate-200">{kgSummary}</p>
        </div>
      ) : null}
      {latestRunTimestamp ? (
        <p className="text-[11px] text-slate-500">Latest agent run synced: {new Date(latestRunTimestamp).toLocaleString()}</p>
      ) : null}
    </div>
  );
}

export default function TemplateReportGenerator({
  missionId,
  variant = "compact",
  mission,
  guardrailStatus,
  guardrailIssues,
}: TemplateReportGeneratorProps) {
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const defaultTemplateId = TEMPLATE_DEFINITIONS[0]?.id ?? "";
  const [selectedTemplate, setSelectedTemplate] = useState<ReportTemplateId>(defaultTemplateId);
  const [result, setResult] = useState<TemplateReportResponse | null>(null);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDismissed, setErrorDismissed] = useState(false);
  const [copyState, setCopyState] = useState<"idle" | "success" | "error">("idle");
  const [history, setHistory] = useState<TemplateReportRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [persistOutput, setPersistOutput] = useState(variant === "full");
  const [lastRequestPayload, setLastRequestPayload] = useState<Record<string, unknown> | null>(null);
  const showDebugPanel = process.env.NEXT_PUBLIC_SHOW_REPORT_DEBUG === "true";

  const isFullLayout = variant === "full";

  const primaryDescription = isFullLayout
    ? "Select a template to synthesize mission context, datasets, and gaps into a structured brief."
    : "Use templated reports to brief stakeholders.";

  useEffect(() => {
    let mounted = true;
    async function loadTemplates() {
      try {
        const data = await fetchMissionReportTemplates(missionId);
        if (!mounted) return;
        setTemplates(data);
        if (data.length) {
          setSelectedTemplate(data[0].template_id);
        }
      } catch (err) {
        console.error("Failed to load templates", err);
        if (mounted) {
          setError("Failed to load templates");
        }
      } finally {
        if (mounted) {
          setLoadingTemplates(false);
        }
      }
    }
    loadTemplates();
    return () => {
      mounted = false;
    };
  }, [missionId]);

  useEffect(() => {
    let mounted = true;
    async function loadHistory() {
      try {
        setHistoryLoading(true);
        const data = await fetchTemplateReportHistory(missionId);
        if (!mounted) return;
        setHistory(data);
      } catch (err) {
        console.error("Failed to load template history", err);
      } finally {
        if (mounted) {
          setHistoryLoading(false);
        }
      }
    }
    loadHistory();
    return () => {
      mounted = false;
    };
  }, [missionId]);

  async function refreshHistory() {
    try {
      setHistoryLoading(true);
      const data = await fetchTemplateReportHistory(missionId);
      setHistory(data);
    } catch (err) {
      console.error("Failed to refresh template history", err);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleGenerate() {
    if (!selectedTemplate) return;
    setGenerating(true);
    setError(null);
    const requestPayload = { missionId, templateId: selectedTemplate, persist: persistOutput };
    setLastRequestPayload(requestPayload);
    try {
      setResult(null);
      const data = await generateTemplateReport(missionId, selectedTemplate, {
        persist: persistOutput,
      });
      setResult(data);
      if (persistOutput) {
        refreshHistory();
      }
    } catch (err) {
      console.error("Failed to generate template report", err);
      const message = err instanceof Error ? err.message : "Failed to generate report. Please try again.";
      setError(message || "Failed to generate report. Please try again.");
    } finally {
      setGenerating(false);
    }
  }

  const containerClasses = isFullLayout
    ? "space-y-5 rounded-2xl border border-slate-700 bg-slate-950/50 p-6 shadow-inner"
    : "space-y-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4";

  const controlLayout = isFullLayout
    ? "flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
    : "flex flex-wrap items-center justify-between gap-3";

  const labelClass = isFullLayout ? "text-2xl font-semibold" : "text-lg font-semibold";
  const helperClass = isFullLayout ? "text-sm text-slate-400" : "text-xs text-slate-400";
  const authorityMeta = mission?.primary_authority ? describeAuthority(mission.primary_authority) : undefined;
  const authorityLabel = authorityMeta?.label ?? mission?.primary_authority ?? "Authority pending";
  const intLabels = mission?.int_types?.map((code) => formatIntLabel(code)) ?? [];

  const metadataGuardrailStatus = typeof result?.metadata?.guardrail_status === "string" ? result.metadata.guardrail_status : undefined;
  const metadataGuardrailIssues = Array.isArray(result?.metadata?.guardrail_issues)
    ? (result?.metadata?.guardrail_issues as string[])
    : undefined;
  const metadataKgSummary = typeof result?.metadata?.kg_snapshot_summary === "string" ? result.metadata.kg_snapshot_summary : null;
  const metadataLatestRun = (result?.metadata?.latest_agent_run as AgentRun | null | undefined) ?? null;
  const metadataDecisions = result?.metadata?.decisions as DecisionDataset | undefined;
  const metadataGuardrail = result?.metadata?.guardrail;

  const htmlContent = typeof result?.html === "string" && result.html.trim().length ? (result.html as string) : null;
  const markdownContent = typeof result?.markdown === "string" ? (result.markdown as string) : null;
  const resolvedSections = useMemo<ReportTemplateSection[]>(() => {
    if (!Array.isArray(result?.sections)) {
      return [];
    }
    return result.sections;
  }, [result?.sections]);

  const effectiveGuardrailStatus = metadataGuardrailStatus ?? guardrailStatus;
  const effectiveGuardrailIssues = metadataGuardrailIssues ?? guardrailIssues ?? [];

  const guardrailSummary = (() => {
    const normalized = (effectiveGuardrailStatus ?? "OK").toLowerCase();
    if (["blocked", "warning", "review"].includes(normalized)) {
      return "Guardrails detected high-risk content. Review carefully before sharing.";
    }
    if (normalized === "caution") {
      return "Guardrails note moderate risk; ensure human validation.";
    }
    return "Guardrails report no blocking issues for this mission.";
  })();

  const templateSelect = (
    <div className="flex w-full flex-col gap-2 md:grid md:grid-cols-2">
      {templates.map((tpl) => {
        const definition = TEMPLATE_DEFINITION_MAP[tpl.template_id];
        const label = definition?.label ?? tpl.name ?? tpl.template_id;
        const description = definition?.description ?? tpl.description ?? "";
        const isSelected = tpl.template_id === selectedTemplate;
        const baseClasses =
          "w-full rounded-xl border p-3 text-left text-sm transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400";
        const stateClasses = isSelected
          ? "border-indigo-400/70 bg-slate-900/70 ring-2 ring-indigo-400/40"
          : "border-slate-800 bg-slate-950/40 hover:border-slate-700";
        return (
          <button
            key={tpl.template_id}
            type="button"
            className={`${baseClasses} ${stateClasses}`}
            aria-pressed={isSelected}
            onClick={() => setSelectedTemplate(tpl.template_id)}
            disabled={generating}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-slate-100">{label}</span>
              {isSelected ? (
                <span className="text-[10px] uppercase tracking-wide text-indigo-300">Selected</span>
              ) : null}
            </div>
            {description ? <p className="mt-1 text-xs text-slate-400">{description}</p> : null}
            {tpl.mission_domains?.length ? (
              <p className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">
                Domains: {tpl.mission_domains.join(", ")}
              </p>
            ) : null}
          </button>
        );
      })}
    </div>
  );

  const generateButton = (
    <button
      type="button"
      onClick={handleGenerate}
      disabled={generating || !selectedTemplate}
      className="rounded border border-indigo-400 px-3 py-1 text-sm font-semibold text-indigo-100 transition hover:bg-indigo-500/20 disabled:opacity-60"
    >
      {generating ? "Generating…" : "Generate"}
    </button>
  );

  const metadataTimestamp = (() => {
    const iso =
      (result?.metadata?.generated_at as string) ??
      result?.metadata?.generatedAt ??
      (result?.metadata?.stored_at as string);
    if (typeof iso === "string") {
      const date = new Date(iso);
      if (!Number.isNaN(date.getTime())) {
        return date.toLocaleString();
      }
    }
    return result ? new Date().toLocaleString() : null;
  })();

  const buildMarkdown = () => {
    if (!result) return "";
    if (markdownContent?.trim()) {
      return markdownContent.trim();
    }
    const sections = resolvedSections.length
      ? resolvedSections
          .map((section: ReportTemplateSection, index: number) => `## ${index + 1}. ${section.title}\n${section.content.trim() || "_No content_"}`)
          .join("\n\n")
      : htmlContent || JSON.stringify({ html: result.html, sections: result.sections }, null, 2);
    const header = `# ${result.template_name}\n${metadataTimestamp ? `Generated ${metadataTimestamp}` : ""}`.trim();
    return `${header}\n\n${sections}`.trim();
  };

  async function handleCopy() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(buildMarkdown());
      setCopyState("success");
      setTimeout(() => setCopyState("idle"), 2500);
    } catch (err) {
      console.error("Failed to copy report", err);
      setCopyState("error");
      setTimeout(() => setCopyState("idle"), 2500);
    }
  }

  function handleDownload() {
    if (!result) return;
    const markdown = buildMarkdown();
    const blob = new Blob([markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${result.template_id || "intel-report"}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  const persistToggle = (
    <label className="flex items-center gap-2 text-xs text-slate-400">
      <input
        type="checkbox"
        className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-indigo-500"
        checked={persistOutput}
        onChange={(event) => setPersistOutput(event.target.checked)}
      />
      Save to history
    </label>
  );

  const handleLoadRecord = useCallback(
    (record: TemplateReportRecord) => {
      setResult({
        mission_id: missionId,
        template_id: record.template_id,
        template_name: record.template_name,
        html: "",
        sections: record.sections,
        metadata: {
          ...record.metadata,
          stored_at: record.stored_at,
          record_id: record.id,
        },
      });
      setSelectedTemplate(record.template_id);
      setCopyState("idle");
    },
    [missionId],
  );

  const historyList = useMemo(() => {
    if (historyLoading) {
      return <p className="text-xs text-slate-500">Loading saved reports…</p>;
    }
    if (!history.length) {
      return <p className="text-xs text-slate-500">No saved templates yet.</p>;
    }
    return (
      <ul className="space-y-2">
        {history.map((record) => (
          <li
            key={record.id}
            className="rounded-lg border border-slate-800/60 bg-slate-900/40 p-3 text-sm text-slate-300"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="font-semibold text-slate-100">{record.template_name}</p>
                <p className="text-xs text-slate-500">
                  Saved {new Date(record.stored_at).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleLoadRecord(record)}
                className="rounded border border-slate-600 px-2 py-1 text-xs font-semibold text-slate-100 hover:bg-slate-800"
              >
                Load
              </button>
            </div>
          </li>
        ))}
      </ul>
    );
  }, [handleLoadRecord, history, historyLoading]);

  return (
    <section className={containerClasses}>
      {mission && (
        <div className="rounded-xl border border-slate-800 bg-slate-950/30 p-4 text-xs text-slate-300">
          <div className="flex flex-wrap gap-3 text-[11px] uppercase tracking-wide text-slate-500">
            <span>Authority Lane</span>
            <span className="rounded-full border border-cyan-500/40 px-2 py-0.5 text-cyan-200">{authorityLabel}</span>
            {intLabels.length ? (
              <span className="rounded-full border border-emerald-500/40 px-2 py-0.5 text-emerald-200">
                INT: {intLabels.join(", ")}
              </span>
            ) : null}
            {effectiveGuardrailStatus ? (
              <span className="rounded-full border border-amber-500/40 px-2 py-0.5 text-amber-200">
                Guardrail: {effectiveGuardrailStatus.toUpperCase()}
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">{guardrailSummary}</p>
          {effectiveGuardrailIssues.length ? (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-[11px] text-amber-200">
              {effectiveGuardrailIssues.slice(0, 3).map((issue, idx) => (
                <li key={`${issue}-${idx}`}>{issue}</li>
              ))}
              {effectiveGuardrailIssues.length > 3 && (
                <li className="text-slate-500">+{effectiveGuardrailIssues.length - 3} more guardrail notes</li>
              )}
            </ul>
          ) : null}
        </div>
      )}
      <div className={controlLayout}>
        <div className="space-y-1">
          <h3 className={`${labelClass} text-slate-100`}>Generate intel product</h3>
          <p className={helperClass}>{primaryDescription}</p>
        </div>
        <div className="flex w-full flex-col gap-3">
          {templates.length ? (
            <div className="w-full">{templateSelect}</div>
          ) : (
            <span className="text-sm text-slate-400">
              {loadingTemplates ? "Loading templates…" : "No templates available"}
            </span>
          )}
          <div className="flex flex-wrap items-center gap-3 text-sm">
            {generateButton}
            {persistToggle}
          </div>
        </div>
      </div>
      {error && !errorDismissed ? (
        <div className="rounded-xl border border-rose-500/50 bg-rose-900/20 p-3 text-sm text-rose-100">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="font-semibold">Report generation failed</p>
              <p className="text-rose-100/80">{error}</p>
            </div>
            <button
              type="button"
              className="text-xs text-rose-200 hover:text-rose-50"
              onClick={() => setErrorDismissed(true)}
            >
              Dismiss
            </button>
          </div>
        </div>
      ) : null}
      {result ? (
        <div className="space-y-4">
          <div className={isFullLayout ? "text-xs uppercase tracking-wide text-slate-500" : "text-xs uppercase tracking-wide text-slate-500"}>
            {result.template_name}
            {metadataTimestamp ? ` • Generated ${metadataTimestamp}` : null}
          </div>
          <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <button
              type="button"
              onClick={handleCopy}
              className="rounded border border-slate-700 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-100 hover:bg-slate-800"
            >
              {copyState === "success" ? "Copied" : copyState === "error" ? "Copy failed" : "Copy Markdown"}
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="rounded border border-slate-700 px-2 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-100 hover:bg-slate-800"
            >
              Download .md
            </button>
          </div>
          {isFullLayout && (
            <p className="text-sm text-slate-400">
              Share or export these sections using your preferred workflow (print, copy, or paste into briefing slides).
            </p>
          )}
          {htmlContent ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-slate-200">Report content</p>
                <span className="text-xs text-slate-500">Template {result.template_id}</span>
              </div>
              <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
                <div
                  className="prose apex-report prose-slate max-w-none h-[70vh] overflow-y-auto rounded-xl bg-white p-4 text-slate-900 shadow-inner"
                  dangerouslySetInnerHTML={{ __html: htmlContent }}
                  suppressHydrationWarning
                />
              </div>
            </div>
          ) : resolvedSections.length ? (
            <div className={isFullLayout ? "space-y-6" : "space-y-4"}>
              {resolvedSections.map((section: ReportTemplateSection, index: number) => (
                <article
                  key={section.id}
                  className={
                    isFullLayout
                      ? "rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow"
                      : "rounded-lg border border-slate-800 bg-slate-900/40 p-4"
                  }
                >
                  <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-500">
                    <span>
                      Section {index + 1}: {section.id.replace(/_/g, " ")}
                    </span>
                  </div>
                  <h4 className={isFullLayout ? "mt-2 text-lg font-semibold text-slate-100" : "mt-1 text-sm font-semibold text-slate-100"}>
                    {section.title}
                  </h4>
                  <p className="mt-3 whitespace-pre-line text-sm text-slate-200">{section.content}</p>
                </article>
              ))}
            </div>
          ) : (
            <pre className="rounded-xl border border-slate-800 bg-slate-900/40 p-3 text-[11px] leading-relaxed text-slate-100">
              {JSON.stringify({ html: result.html, markdown: result.markdown, sections: result.sections }, null, 2)}
            </pre>
          )}
          <DecisionContextPanel
            templateId={result.template_id}
            decisions={metadataDecisions}
            kgSummary={metadataKgSummary}
            guardrail={metadataGuardrail}
            guardrailStatus={effectiveGuardrailStatus}
            guardrailIssues={effectiveGuardrailIssues}
          />
          <ReportContextPanel
            guardrailStatus={metadataGuardrailStatus}
            guardrailIssues={metadataGuardrailIssues}
            kgSummary={metadataKgSummary}
            latestRunTimestamp={metadataLatestRun?.created_at}
          />
          {showDebugPanel ? (
            <TemplateReportDebugPanel report={result} lastRequestPayload={lastRequestPayload} />
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-400">
          {isFullLayout
            ? "Choose a template and click Generate to populate the structured mission report."
            : "Generate a template-based summary to include in mission briefs."}
        </p>
      )}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h4 className="text-sm font-semibold text-slate-100">Saved template runs</h4>
          <button
            type="button"
            onClick={refreshHistory}
            className="text-xs text-indigo-300 hover:text-indigo-200"
          >
            Refresh
          </button>
        </div>
        <div className="mt-3">
          {historyList}
        </div>
      </div>
    </section>
  );
}
