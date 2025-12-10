"use client";

import { useState } from "react";
import Link from "next/link";

import MissionDetail from "@/components/MissionDetail";
import DocumentForm from "@/components/DocumentForm";
import DocumentList from "@/components/DocumentList";
import AgentSummary from "@/components/AgentSummary";
import GuardrailBadge from "@/components/GuardrailBadge";
import RunAnalysisButton from "@/components/RunAnalysisButtonWrapper";
import MissionDatasetList from "@/components/MissionDatasetList";
import MissionDatasetForm from "@/components/MissionDatasetForm";
import GapsPriorities from "@/components/GapsPriorities";
import GapAnalysisPanel from "@/components/GapAnalysisPanel";
import TemplateReportPanel from "@/components/TemplateReportPanel";
import TemplateReportGenerator from "@/components/TemplateReportGenerator";
import EntitiesEventsView from "@/components/EntitiesEventsView";
import MissionSourcesTab from "@/components/MissionSourcesTab";
import HumintAnalysisPanel from "@/components/HumintAnalysisPanel";
import AIAnalysisPanel from "@/components/AIAnalysisPanel";
import { MissionProvider, useMission } from "@/context/MissionContext";

import type {
  AgentRun,
  Document,
  GapAnalysisResponse,
  Mission,
  MissionDataset,
} from "@/lib/api";

interface MissionTabsProps {
  mission: Mission;
  missionId: number;
  documents: Document[];
  runs: AgentRun[];
  datasets: MissionDataset[];
  gapAnalysis: GapAnalysisResponse;
}

type TabKey = "overview" | "data" | "sources" | "analysis" | "reports";

const tabs: { key: TabKey; label: string }[] = [
  { key: "overview", label: "Overview" },
  { key: "data", label: "Data" },
  { key: "sources", label: "Sources" },
  { key: "analysis", label: "Analysis" },
  { key: "reports", label: "Reports" },
];

export default function MissionTabs(props: MissionTabsProps) {
  const { mission } = props;

  return (
    <MissionProvider initialMission={mission}>
      <MissionTabsInner {...props} />
    </MissionProvider>
  );
}

interface MissionTabsInnerProps extends Omit<MissionTabsProps, "mission"> {}

function MissionTabsInner({ missionId, documents, runs, datasets, gapAnalysis }: MissionTabsInnerProps) {
  const { mission, latestRun } = useMission();
  const [activeTab, setActiveTab] = useState<TabKey>("overview");

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2 border-b border-slate-800">
        {tabs.map((tab) => {
          const active = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`rounded-t-md px-3 py-2 text-sm font-medium transition ${
                active
                  ? "border border-b-slate-950 border-emerald-400/70 bg-slate-900 text-slate-100"
                  : "border border-transparent text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      <div>{renderContent()}</div>
    </div>
  );

  function renderContent() {
    switch (activeTab) {
      case "overview":
        return (
          <div className="space-y-6">
            <MissionDetail mission={mission} />

            <section className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div className="card space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xl font-semibold">Agent</h3>
                    <RunAnalysisButton missionId={missionId} />
                  </div>
                  <p className="text-sm text-slate-400">
                    Run an APEX analysis to extract entities, events, and next steps.
                  </p>
                </div>
                <AgentSummary />
              </div>

              <div className="card space-y-3">
                <h3 className="text-xl font-semibold">Guardrail status</h3>
                <GuardrailBadge
                  status={latestRun?.guardrail_status ?? "ok"}
                  issues={latestRun?.guardrail_issues ?? []}
                />
              </div>
            </section>
          </div>
        );

      case "data":
        return (
          <div className="space-y-8">
            <section className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xl font-semibold">Documents</h3>
                <div className="flex items-center gap-3 text-sm text-slate-400">
                  <span>{documents.length} files</span>
                  <Link
                    href={`/missions/${missionId}/report`}
                    className="rounded border border-slate-600 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:bg-slate-800"
                  >
                    View report
                  </Link>
                </div>
              </div>
              <p className="text-sm text-slate-400">
                Manage manually entered documents used during analysis. Source ingestion is now handled in the
                dedicated Sources tab.
              </p>
              <div className="grid gap-6 lg:grid-cols-2">
                <DocumentForm missionId={missionId} onCreated={() => undefined} />
                <div className="card space-y-4">
                  <div>
                    <h4 className="text-lg font-semibold">Mission document library</h4>
                    <p className="text-sm text-slate-400">
                      HUMINT IIR Evaluation uses the documents added here.
                    </p>
                  </div>
                  <DocumentList missionId={missionId} documents={documents} />
                </div>
              </div>
            </section>

            <section className="space-y-4">
              <h3 className="text-xl font-semibold">Mission datasets</h3>
              <div className="grid gap-6 lg:grid-cols-2">
                <MissionDatasetList missionId={missionId} datasets={datasets} />
                <MissionDatasetForm missionId={missionId} />
              </div>
            </section>
          </div>
        );

      case "sources":
        return <MissionSourcesTab missionId={missionId} mission={mission} />;

      case "analysis":
        return renderAnalysisSurface();

      case "reports":
        return (
          <div className="space-y-6">
            <TemplateReportPanel
              missionId={missionId}
              mission={mission}
              guardrailStatus={latestRun?.guardrail_status}
              guardrailIssues={latestRun?.guardrail_issues ?? []}
            />
            <TemplateReportGenerator
              missionId={missionId}
              mission={mission}
              guardrailStatus={latestRun?.guardrail_status}
              guardrailIssues={latestRun?.guardrail_issues ?? []}
            />
          </div>
        );

      default:
        return null;
    }
  }

  function renderAnalysisSurface() {
    const kgNamespace = mission.kg_namespace ?? `mission-${missionId}`;
    const gapCounts = {
      missing: gapAnalysis?.missing_data?.length ?? 0,
      conflicts: gapAnalysis?.conflicts?.length ?? 0,
      quality: gapAnalysis?.quality_findings?.length ?? 0,
    };
    const totalGapAlerts = gapCounts.missing + gapCounts.conflicts + gapCounts.quality;
    const lastRunLabel = latestRun
      ? new Date(latestRun.created_at).toLocaleString()
      : "No agent cycle yet";
    const recentRuns = runs.slice(0, 3);

    return (
      <div className="space-y-6">
        <div className="overflow-hidden rounded-3xl border border-indigo-900/40 bg-gradient-to-r from-[#070b16] via-[#0b1430] to-[#081120] p-6 text-slate-100 shadow-[0_12px_60px_rgba(5,8,20,0.45)]">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="space-y-3">
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-emerald-300/80">Mission analysis</p>
              <h3 className="text-3xl font-semibold text-white">{mission.name}</h3>
              <p className="text-sm text-slate-300">
                Live namespace: <span className="font-mono text-emerald-200">{kgNamespace}</span>
              </p>
              <div className="flex flex-wrap gap-2">
                {(mission.int_types ?? []).map((code) => (
                  <span
                    key={code}
                    className="rounded-full border border-emerald-400/40 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-emerald-200"
                  >
                    {code}
                  </span>
                ))}
              </div>
            </div>
            <div className="grid min-w-[260px] gap-4 sm:grid-cols-2">
              {[{
                label: "Gap alerts",
                value: totalGapAlerts,
                accent: "text-amber-300",
              },
                {
                  label: "Datasets onboarded",
                  value: datasets.length,
                  accent: "text-cyan-300",
                },
                {
                  label: "Agent runs",
                  value: runs.length,
                  accent: "text-emerald-300",
                },
                {
                  label: "Threat findings",
                  value: gapAnalysis?.high_value_unknowns?.length ?? 0,
                  accent: "text-fuchsia-300",
                },
              ].map((metric) => (
                <div
                  key={metric.label}
                  className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 backdrop-blur"
                >
                  <p className="text-xs uppercase tracking-wide text-slate-200/80">{metric.label}</p>
                  <p className={`text-2xl font-semibold ${metric.accent}`}>{metric.value}</p>
                </div>
              ))}
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-slate-200 backdrop-blur">
              <p className="text-xs uppercase tracking-wide text-slate-300/80">Last agent cycle</p>
              <p className="mt-1 font-semibold text-white">{lastRunLabel}</p>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[minmax(320px,360px)_minmax(0,1fr)]">
          <div className="space-y-6">
            <section className="rounded-2xl border border-slate-800/60 bg-[#050912]/80 p-1 shadow-[0_20px_45px_rgba(0,0,0,0.45)]">
              <GapsPriorities missionId={missionId} initialData={gapAnalysis} />
            </section>

            <section className="rounded-2xl border border-slate-800/60 bg-[#050912]/80 p-1 shadow-[0_20px_45px_rgba(0,0,0,0.45)]">
              <GapAnalysisPanel missionId={missionId} />
            </section>

            <section className="rounded-2xl border border-slate-800/70 bg-[#070d1b]/90 p-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-100">Gap signals</h3>
                <span className="text-xs uppercase tracking-wider text-slate-400">Live telemetry</span>
              </div>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-300">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Missing data</dt>
                  <dd className="text-2xl font-semibold text-amber-300">{gapCounts.missing}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Conflicts</dt>
                  <dd className="text-2xl font-semibold text-rose-300">{gapCounts.conflicts}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Quality</dt>
                  <dd className="text-2xl font-semibold text-fuchsia-300">{gapCounts.quality}</dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">Datasets</dt>
                  <dd className="text-2xl font-semibold text-cyan-300">{datasets.length}</dd>
                </div>
              </dl>
            </section>

            <section className="rounded-2xl border border-slate-800/70 bg-[#070d1b]/90 p-5">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-slate-100">Operational log</h3>
                <span className="text-xs text-slate-400">Newest first</span>
              </div>
              {recentRuns.length === 0 ? (
                <p className="mt-3 text-sm text-slate-400">No agent runs executed yet.</p>
              ) : (
                <ul className="mt-4 space-y-3 text-sm">
                  {recentRuns.map((run) => (
                    <li
                      key={run.id}
                      className="rounded-xl border border-slate-800/60 bg-slate-950/60 px-3 py-2 text-slate-200"
                    >
                      <p className="font-semibold text-emerald-200">Run #{run.id}</p>
                      <p className="text-xs text-slate-400">{new Date(run.created_at).toLocaleString()}</p>
                      <p className="text-xs uppercase tracking-wide text-slate-500">Status: {run.status}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <div className="rounded-3xl border border-slate-800/50 bg-[#04070f]/80 p-4 shadow-[0_35px_65px_rgba(2,4,11,0.75)] lg:p-6 space-y-6">
            <EntitiesEventsView missionId={missionId} />
            <AIAnalysisPanel missionId={missionId} documents={documents} />
            <HumintAnalysisPanel missionId={missionId} documents={documents} />
          </div>
        </div>
      </div>
    );
  }
}
