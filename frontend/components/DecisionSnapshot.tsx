"use client";

import { useMemo, useState } from "react";

import type { CourseOfAction, DecisionDataset, MissionDecision, ReportTemplateId } from "@/lib/api";

interface DecisionSnapshotProps {
  decisions: DecisionDataset;
  templateId?: ReportTemplateId;
}

function RiskBadge({ level }: { level?: CourseOfAction["risk_level"] }) {
  if (!level) return null;
  const classes =
    level === "low"
      ? "border-emerald-300 bg-emerald-100 text-emerald-800"
      : level === "medium"
        ? "border-amber-300 bg-amber-100 text-amber-800"
        : level === "high"
          ? "border-orange-300 bg-orange-100 text-orange-800"
          : "border-red-300 bg-red-100 text-red-800";
  return <span className={`inline-flex items-center rounded-full border px-2 text-[10px] font-semibold ${classes}`}>{level.toUpperCase()}</span>;
}

function PolicyBadge({ alignment }: { alignment?: CourseOfAction["policy_alignment"] }) {
  if (!alignment) return null;
  const meta = {
    compliant: { label: "Policy compliant", classes: "border-emerald-200 bg-emerald-50 text-emerald-700" },
    waiver_required: { label: "Waiver required", classes: "border-amber-200 bg-amber-50 text-amber-700" },
    conflicts: { label: "Policy conflict", classes: "border-red-200 bg-red-50 text-red-700" },
  }[alignment];
  if (!meta) return null;
  return <span className={`inline-flex items-center rounded-full border px-2 text-[10px] font-semibold ${meta.classes}`}>{meta.label}</span>;
}

function BlindSpotSeverityDot({ impact }: { impact: "low" | "medium" | "high" }) {
  const dots = impact === "high" ? "●●●" : impact === "medium" ? "●●" : "●";
  const color = impact === "high" ? "text-red-500" : impact === "medium" ? "text-amber-500" : "text-slate-400";
  return <span className={`mr-1 font-semibold ${color}`}>{dots}</span>;
}

export default function DecisionSnapshot({ decisions }: DecisionSnapshotProps) {
  const { decisions: missionDecisions = [], courses_of_action = [], blind_spots = [], policy_checks = [], system_confidence } = decisions;

  const coasByDecisionId = useMemo(() => {
    const map: Record<string, CourseOfAction[]> = {};
    for (const coa of courses_of_action) {
      if (!coa.decision_id) continue;
      if (!map[coa.decision_id]) {
        map[coa.decision_id] = [];
      }
      map[coa.decision_id].push(coa);
    }
    return map;
  }, [courses_of_action]);

  const [expandedDecisionIds, setExpandedDecisionIds] = useState<Set<string>>(new Set());

  const toggleDecision = (id: string) => {
    setExpandedDecisionIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const policyCounts = useMemo(() => {
    return policy_checks.reduce(
      (acc, check) => {
        if (check.outcome === "fail") acc.fail += 1;
        else if (check.outcome === "waiver") acc.waiver += 1;
        else if (check.outcome === "pass") acc.pass += 1;
        return acc;
      },
      { pass: 0, fail: 0, waiver: 0 },
    );
  }, [policy_checks]);

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-slate-100">Decision snapshot</h3>
        {typeof system_confidence === "number" ? (
          <span className="text-xs text-slate-500">System confidence: {(system_confidence * 100).toFixed(0)}%</span>
        ) : null}
      </div>

      <div className="space-y-3">
        {missionDecisions.slice(0, 3).map((decision: MissionDecision) => {
          const coasForDecision = coasByDecisionId[decision.id] ?? [];
          const recommended = coasForDecision.find((coa) => coa.id === decision.recommended_coa_id) ?? coasForDecision[0];
          const isExpanded = expandedDecisionIds.has(decision.id);
          return (
            <div key={decision.id} className="rounded-xl border border-slate-800/60 bg-slate-900/40 p-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-100">{decision.question}</p>
                  {decision.rationale ? <p className="text-xs text-slate-400">{decision.rationale}</p> : null}
                  {recommended ? (
                    <div className="mt-1 text-xs text-slate-300">
                      Recommended: <span className="font-semibold text-slate-100">{recommended.label}</span>
                      <div className="mt-1 flex flex-wrap gap-1">
                        <RiskBadge level={recommended.risk_level} />
                        <PolicyBadge alignment={recommended.policy_alignment} />
                      </div>
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="text-[11px] font-semibold text-indigo-300 hover:text-indigo-200"
                  onClick={() => toggleDecision(decision.id)}
                >
                  {isExpanded ? "Hide COAs" : "Show COAs"}
                </button>
              </div>
              {isExpanded && coasForDecision.length ? (
                <div className="mt-3 space-y-2 border-t border-slate-800/60 pt-3">
                  {coasForDecision.map((coa) => (
                    <div key={coa.id} className="space-y-1 rounded-lg border border-slate-800 bg-slate-950/40 p-2">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="text-xs font-semibold text-slate-100">{coa.label}</div>
                        <div className="flex flex-wrap gap-1">
                          <RiskBadge level={coa.risk_level} />
                          <PolicyBadge alignment={coa.policy_alignment} />
                        </div>
                      </div>
                      {coa.summary ? <p className="text-xs text-slate-300">{coa.summary}</p> : null}
                      {(coa.pros?.length || coa.cons?.length) ? (
                        <div className="grid gap-2 text-[11px] text-slate-200 md:grid-cols-2">
                          {coa.pros?.length ? (
                            <div>
                              <p className="font-semibold text-emerald-300">Pros</p>
                              <ul className="mt-1 list-disc pl-4">
                                {coa.pros.map((pro, idx) => (
                                  <li key={idx}>{pro}</li>
                                ))}
                              </ul>
                            </div>
                          ) : null}
                          {coa.cons?.length ? (
                            <div>
                              <p className="font-semibold text-rose-300">Cons</p>
                              <ul className="mt-1 list-disc pl-4">
                                {coa.cons.map((con, idx) => (
                                  <li key={idx}>{con}</li>
                                ))}
                              </ul>
                            </div>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          );
        })}
        {missionDecisions.length === 0 ? <p className="text-xs text-slate-500">No explicit decisions were generated for this report.</p> : null}
      </div>

      {blind_spots.length ? (
        <div className="space-y-1 rounded-xl border border-slate-800/60 bg-slate-900/30 p-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Blind spots</div>
          <ul className="space-y-1 text-xs text-slate-200">
            {blind_spots.slice(0, 6).map((spot) => (
              <li key={spot.id} className="flex items-start gap-1">
                <BlindSpotSeverityDot impact={spot.impact} />
                <span>
                  {spot.description}
                  {spot.mitigation ? <span className="text-[11px] text-slate-400"> — Mitigation: {spot.mitigation}</span> : null}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {policy_checks.length ? (
        <div className="rounded-xl border border-slate-800/60 bg-slate-900/30 p-3 text-xs text-slate-200">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">Policy & legal checks</div>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="rounded-full bg-emerald-200/20 px-2 py-0.5 text-emerald-200">Pass: {policyCounts.pass}</span>
            <span className="rounded-full bg-amber-200/20 px-2 py-0.5 text-amber-200">Waiver: {policyCounts.waiver}</span>
            <span className="rounded-full bg-rose-200/20 px-2 py-0.5 text-rose-200">Fail: {policyCounts.fail}</span>
          </div>
        </div>
      ) : null}
    </section>
  );
}
