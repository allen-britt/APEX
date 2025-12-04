"use client";

import { useEffect, useMemo, useState } from "react";

import DecisionSnapshot from "@/components/DecisionSnapshot";
import GuardrailBadge from "@/components/GuardrailBadge";
import { TEMPLATE_DEFINITION_MAP } from "@/components/templateDefinitions";
import {
  fetchMissionReportTemplates,
  generateMissionTemplateReport,
  type AgentRun,
  type Mission,
  type ReportTemplate,
  type TemplateReportResponse,
  type TemplateReportMetadata,
} from "@/lib/api";
import { describeAuthority, formatIntLabel } from "@/lib/policy";

interface TemplateReportPanelProps {
  missionId: number;
  mission?: Mission;
  guardrailStatus?: string;
  guardrailIssues?: string[];
}

export default function TemplateReportPanel({
  missionId,
  mission,
  guardrailStatus,
  guardrailIssues,
}: TemplateReportPanelProps) {
  const [templates, setTemplates] = useState<ReportTemplate[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [loadingTemplates, setLoadingTemplates] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorDismissed, setErrorDismissed] = useState(false);
  const [report, setReport] = useState<TemplateReportResponse | null>(null);

  useEffect(() => {
    let mounted = true;
    async function loadTemplates() {
      try {
        setLoadingTemplates(true);
        const data = await fetchMissionReportTemplates(missionId);
        if (!mounted) return;
        setTemplates(data);
        if (data.length) {
          setSelectedTemplate(data[0].template_id);
        }
      } catch (err) {
        console.error("Failed to load templates", err);
        if (mounted) {
          setError("Failed to load templates.");
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

  const currentTemplate = useMemo(
    () => templates.find((tpl) => tpl.template_id === selectedTemplate),
    [templates, selectedTemplate],
  );

  async function handleGenerate() {
    if (!selectedTemplate) return;
    try {
      setRunning(true);
      setError(null);
      setErrorDismissed(false);
      setReport(null);
      const result = await generateMissionTemplateReport(missionId, { template_id: selectedTemplate });
      setReport(result);
    } catch (err) {
      console.error("Failed to generate template report", err);
      const message = err instanceof Error ? err.message : "Failed to generate report. Please try again.";
      setError(message || "Failed to generate report. Please try again.");
    } finally {
      setRunning(false);
    }
  }

  const metadata = report?.metadata as TemplateReportMetadata | undefined;
  const metadataGuardrailStatus = typeof metadata?.guardrail_status === "string" ? metadata.guardrail_status : undefined;
  const metadataGuardrailIssues = Array.isArray(metadata?.guardrail_issues) ? (metadata.guardrail_issues as string[]) : undefined;
  const metadataLatestRun = (metadata?.latest_agent_run as AgentRun | null | undefined) ?? null;
  const metadataKgSummary = typeof metadata?.kg_snapshot_summary === "string" ? metadata.kg_snapshot_summary : null;
  const metadataDecisions = metadata?.decisions;

  const effectiveGuardrailStatus = metadataGuardrailStatus ?? guardrailStatus;
  const effectiveGuardrailIssues = metadataGuardrailIssues ?? guardrailIssues ?? [];

  const authorityMeta = mission?.primary_authority ? describeAuthority(mission.primary_authority) : undefined;
  const authorityLabel = authorityMeta?.label ?? mission?.primary_authority ?? "Authority pending";
  const intLabels = mission?.int_types?.map((code) => formatIntLabel(code)) ?? [];

  const guardrailSummary = (() => {
    const normalized = (effectiveGuardrailStatus ?? "ok").toLowerCase();
    if (["warning", "blocked", "review"].includes(normalized)) {
      return "Policy guardrails detected elevated risk; review outputs before release.";
    }
    if (normalized === "caution") {
      return "Guardrails show moderate risk; ensure human validation.";
    }
    return "Guardrails report no blocking issues for this mission.";
  })();

  return (
    <div className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
      {mission && (
        <div className="rounded-xl border border-slate-800/70 bg-slate-900/40 p-3 text-[11px] text-slate-300">
          <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500">
            <span>Authority Lane</span>
            <span className="rounded-full border border-cyan-500/40 px-2 py-0.5 text-cyan-200">{authorityLabel}</span>
            {intLabels.length ? (
              <span className="rounded-full border border-emerald-500/40 px-2 py-0.5 text-emerald-200">INT: {intLabels.join(", ")}</span>
            ) : null}
            {effectiveGuardrailStatus ? (
              <span className="rounded-full border border-amber-500/40 px-2 py-0.5 text-amber-200">
                Guardrail: {effectiveGuardrailStatus.toUpperCase()}
              </span>
            ) : null}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">{guardrailSummary}</p>
          {effectiveGuardrailIssues.length ? (
            <ul className="mt-1 list-disc space-y-1 pl-5 text-[11px] text-amber-200">
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
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h4 className="text-lg font-semibold text-slate-100">Template reports</h4>
          <button
            type="button"
            onClick={handleGenerate}
            disabled={!selectedTemplate || running}
            className="rounded border border-indigo-400 px-3 py-1 text-xs font-semibold text-indigo-100 transition hover:bg-indigo-500/20 disabled:opacity-60"
          >
            {running ? "Generating…" : "Generate"}
          </button>
        </div>
        {loadingTemplates ? (
          <p className="text-xs text-slate-500">Loading templates…</p>
        ) : templates.length === 0 ? (
          <p className="text-xs text-slate-500">No templates available for this mission.</p>
        ) : (
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
                  disabled={running}
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
        )}
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

      {currentTemplate ? (
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3 text-xs text-slate-300">
          <p className="font-semibold text-slate-100">{currentTemplate.name}</p>
          {currentTemplate.description ? <p className="mt-1">{currentTemplate.description}</p> : null}
          {currentTemplate.mission_domains?.length ? (
            <p className="mt-2 text-[11px] text-slate-500">Domains: {currentTemplate.mission_domains.join(", ")}</p>
          ) : null}
          {currentTemplate.sections?.length ? (
            <p className="text-[11px] text-slate-500">
              Sections: {currentTemplate.sections.join(", ")}
            </p>
          ) : null}
        </div>
      ) : null}

      {report ? (
        <>
          <ReportPreview report={report} />
          <ReportMetadataPanel
            guardrailStatus={effectiveGuardrailStatus}
            guardrailIssues={effectiveGuardrailIssues}
            kgSummary={metadataKgSummary}
            latestRunTimestamp={metadataLatestRun?.created_at}
          />
          {metadataDecisions ? <DecisionSnapshot decisions={metadataDecisions} /> : null}
        </>
      ) : null}
    </div>
  );
}

function ReportPreview({ report }: { report: TemplateReportResponse }) {
  const htmlContent = (() => {
    if (typeof report.html === "string" && report.html.trim()) {
      return report.html;
    }
    const legacyContent = (report as unknown as { content?: { html?: string } }).content;
    const legacyHtml = typeof legacyContent?.html === "string" ? legacyContent.html : null;
    return legacyHtml && legacyHtml.trim() ? legacyHtml : null;
  })();

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold text-slate-200">Report content</p>
        <span className="text-xs text-slate-500">Template {report.template_id}</span>
      </div>
      {htmlContent ? (
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-3">
          <div
            className="prose prose-slate max-w-none h-[70vh] overflow-y-auto rounded-xl bg-white p-4 text-slate-900 shadow-inner"
            dangerouslySetInnerHTML={{ __html: htmlContent }}
            suppressHydrationWarning
          />
        </div>
      ) : (
        <pre className="max-h-[300px] overflow-auto rounded-xl border border-slate-800 bg-slate-900/60 p-3 text-[11px] leading-relaxed text-slate-100">
          {JSON.stringify(
            (report as unknown as { content?: unknown }).content ?? {
              html: report.html,
              markdown: report.markdown,
              sections: report.sections,
            },
            null,
            2,
          )}
        </pre>
      )}
    </div>
  );
}

interface ReportMetadataPanelProps {
  guardrailStatus?: string;
  guardrailIssues?: string[];
  kgSummary?: string | null;
  latestRunTimestamp?: string;
}

function ReportMetadataPanel({ guardrailStatus, guardrailIssues = [], kgSummary, latestRunTimestamp }: ReportMetadataPanelProps) {
  if (!guardrailStatus && !kgSummary && !latestRunTimestamp) {
    return null;
  }

  return (
    <div className="space-y-2 rounded-xl border border-slate-800/60 bg-slate-900/40 p-3 text-xs text-slate-300">
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
        <p className="text-[11px] text-slate-500">
          Latest agent run synced: {new Date(latestRunTimestamp).toLocaleString()}
        </p>
      ) : null}
    </div>
  );
}
