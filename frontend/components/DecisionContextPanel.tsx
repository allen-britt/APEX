"use client";

import GuardrailBadge from "@/components/GuardrailBadge";
import type {
  CourseOfAction,
  DecisionBlindSpot,
  DecisionDataset,
  MissionDecision,
  PolicyCheck,
  ReportTemplateId,
  TemplateReportMetadata,
} from "@/lib/api";

interface DecisionContextPanelProps {
  templateId: ReportTemplateId;
  decisions?: DecisionDataset;
  kgSummary?: string | null;
  guardrail?: TemplateReportMetadata["guardrail"];
  guardrailStatus?: string;
  guardrailIssues?: string[];
}

function buildCoaLookup(courses: CourseOfAction[]): Record<string, CourseOfAction[]> {
  return courses.reduce((acc, coa) => {
    if (!acc[coa.decision_id]) {
      acc[coa.decision_id] = [];
    }
    acc[coa.decision_id].push(coa);
    return acc;
  }, {} as Record<string, CourseOfAction[]>);
}

function PolicyCheckSummary({ policyChecks }: { policyChecks: PolicyCheck[] }) {
  const failed = policyChecks.filter((check) => check.outcome === "fail");
  const waiver = policyChecks.filter((check) => check.outcome === "waiver");
  return (
    <div className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-900/40 p-3">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Policy checks</div>
      <p className="text-xs text-slate-300">
        {failed.length} failed / {waiver.length} require waiver / {policyChecks.length} total checks
      </p>
      <ul className="max-h-48 space-y-1 overflow-auto text-[11px] text-slate-400">
        {policyChecks.slice(0, 6).map((check) => (
          <li key={check.id} className="rounded border border-slate-800/70 bg-slate-950/40 p-2">
            <div className="flex flex-wrap items-center gap-2 text-[10px] uppercase tracking-wide text-slate-500">
              <span>{check.rule_name}</span>
              <span className="rounded-full border border-slate-800 px-2 py-0.5 text-[10px] text-slate-300">{check.outcome}</span>
            </div>
            <p className="text-xs text-slate-300">{check.summary}</p>
          </li>
        ))}
        {policyChecks.length > 6 ? (
          <li className="text-[11px] text-slate-500">+{policyChecks.length - 6} additional checks</li>
        ) : null}
      </ul>
    </div>
  );
}

export default function DecisionContextPanel({
  templateId,
  decisions,
  kgSummary,
  guardrail,
  guardrailStatus,
  guardrailIssues = [],
}: DecisionContextPanelProps) {
  const missionDecisions = decisions?.decisions ?? [];
  const coursesOfAction = decisions?.courses_of_action ?? [];
  const blindSpots = decisions?.blind_spots ?? [];
  const policyChecks = decisions?.policy_checks ?? [];
  const systemConfidence = decisions?.system_confidence;

  const coasByDecisionId = buildCoaLookup(coursesOfAction);
  const hasDecisionContent = Boolean(
    decisions && (missionDecisions.length || coursesOfAction.length || policyChecks.length || blindSpots.length),
  );
  const hasContextCards = Boolean(kgSummary || guardrail || guardrailStatus);
  const effectiveGuardrailStatus = guardrail?.state ?? guardrailStatus ?? "ok";
  const isCommanderDecisionSheet = templateId === "commander_decision_sheet_v1";

  if (!hasDecisionContent && !hasContextCards) {
    return null;
  }

  const severityDot = (impact: DecisionBlindSpot["impact"]) => {
    if (impact === "high") return "●●●";
    if (impact === "medium") return "●●";
    return "●";
  };

  const policySummary = (() => {
    if (!decisions?.policy_checks?.length) return null;
    return decisions.policy_checks.reduce(
      (acc, check) => {
        if (check.outcome === "pass") acc.pass += 1;
        else if (check.outcome === "fail") acc.fail += 1;
        else if (check.outcome === "waiver") acc.waiver += 1;
        return acc;
      },
      { pass: 0, fail: 0, waiver: 0 },
    );
  })();

  const contextSections: JSX.Element[] = [];

  if (kgSummary) {
    contextSections.push(
      <section key="kg" className="rounded-md border border-slate-200/60 bg-slate-50 p-3 text-xs text-slate-700">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Knowledge graph snapshot</h3>
        <p className="mt-1">{kgSummary}</p>
      </section>,
    );
  }

  if (guardrail || guardrailStatus) {
    contextSections.push(
      <section key="guardrail" className="rounded-md border border-slate-200/60 bg-slate-50 p-3 text-xs text-slate-700">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Guardrail posture</h3>
        <GuardrailBadge status={effectiveGuardrailStatus} issues={guardrailIssues} />
        {guardrail?.summary ? <p className="mt-1 text-slate-600">{guardrail.summary}</p> : null}
      </section>,
    );
  }

  if (decisions?.blind_spots?.length) {
    contextSections.push(
      <section key="blind" className="rounded-md border border-slate-200/60 bg-slate-50 p-3 text-xs text-slate-700">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Blind spots</h3>
        <ul className="mt-1 space-y-1">
          {decisions.blind_spots.map((spot) => (
            <li key={spot.id}>
              <span className="mr-1 text-[10px] text-slate-500">{severityDot(spot.impact)}</span>
              {spot.description}
              {spot.mitigation ? <span className="ml-1 text-[11px] text-slate-500">— Mitigation: {spot.mitigation}</span> : null}
            </li>
          ))}
        </ul>
      </section>,
    );
  }

  if (policySummary) {
    contextSections.push(
      <section key="policy" className="rounded-md border border-slate-200/60 bg-slate-50 p-3 text-xs text-slate-700">
        <h3 className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">Policy & legal checks</h3>
        <div className="mt-2 flex flex-wrap gap-2">
          <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] text-emerald-800">Pass: {policySummary.pass}</span>
          <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[11px] text-amber-800">Waiver: {policySummary.waiver}</span>
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] text-red-800">Fail: {policySummary.fail}</span>
        </div>
      </section>,
    );
  }

  return (
    <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-950/40 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold text-slate-100">Decision context</h3>
          {isCommanderDecisionSheet ? (
            <span className="rounded-full border border-indigo-400/60 px-2 py-0.5 text-[10px] uppercase tracking-wide text-indigo-200">
              Commander sheet
            </span>
          ) : null}
        </div>
        {typeof systemConfidence === "number" ? (
          <span className="text-xs text-slate-500">System confidence: {(systemConfidence * 100).toFixed(0)}%</span>
        ) : null}
      </div>

      {contextSections.length ? <div className="grid gap-3 md:grid-cols-2">{contextSections}</div> : null}

      {hasDecisionContent ? (
        <>
          {missionDecisions.length ? (
            <div className="space-y-3">
              {missionDecisions.map((decision: MissionDecision) => {
                const coas = coasByDecisionId[decision.id] ?? [];
                return (
                  <div key={decision.id} className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-900/40 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs uppercase tracking-wide text-slate-500">
                      <span className="text-slate-200 normal-case">{decision.question}</span>
                      <span>{decision.status}</span>
                    </div>
                    {decision.rationale ? <p className="text-xs text-slate-400">{decision.rationale}</p> : null}
                    {coas.length ? (
                      <div className="space-y-2">
                        {coas.map((coa) => {
                          const isRecommended = decision.recommended_coa_id === coa.id;
                          const isSelected = decision.selected_coa_id === coa.id;
                          return (
                            <div key={coa.id} className="space-y-1 rounded-lg border border-slate-800 bg-slate-950/40 p-3">
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex flex-wrap items-center gap-2 text-xs font-semibold text-slate-100">
                                  <span>{coa.label}</span>
                                  {isRecommended ? (
                                    <span className="rounded-full border border-emerald-500/60 px-2 py-0.5 text-[10px] uppercase text-emerald-200">
                                      Recommended
                                    </span>
                                  ) : null}
                                  {isSelected ? (
                                    <span className="rounded-full border border-indigo-400/60 px-2 py-0.5 text-[10px] uppercase text-indigo-200">
                                      Selected
                                    </span>
                                  ) : null}
                                </div>
                                <div className="inline-flex flex-wrap items-center gap-2 text-[10px] uppercase text-slate-400">
                                  <span className="rounded-full border border-slate-800 px-2 py-0.5">{coa.risk_level}</span>
                                  <span className="rounded-full border border-slate-800 px-2 py-0.5">{coa.policy_alignment}</span>
                                  {typeof coa.confidence === "number" ? (
                                    <span className="rounded-full border border-slate-800 px-2 py-0.5">
                                      Confidence: {coa.confidence.toFixed(2)}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                              <p className="text-sm text-slate-300">{coa.summary}</p>
                              {coa.pros.length ? (
                                <div className="text-xs text-emerald-200">
                                  <span className="font-semibold uppercase tracking-wide text-emerald-300">Pros: </span>
                                  <span>{coa.pros.join("; ")}</span>
                                </div>
                              ) : null}
                              {coa.cons.length ? (
                                <div className="text-xs text-rose-200">
                                  <span className="font-semibold uppercase tracking-wide text-rose-300">Cons: </span>
                                  <span>{coa.cons.join("; ")}</span>
                                </div>
                              ) : null}
                              {coa.policy_refs.length ? (
                                <div className="text-[11px] text-slate-400">
                                  <span className="font-semibold uppercase tracking-wide text-slate-500">Policy refs: </span>
                                  <span>{coa.policy_refs.join(", ")}</span>
                                </div>
                              ) : null}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500">No COAs were generated for this decision.</p>
                    )}
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-500">No decisions were synthesized for this report.</p>
          )}

          {policyChecks.length ? <PolicyCheckSummary policyChecks={policyChecks} /> : null}

          {blindSpots.length ? (
            <div className="space-y-2 rounded-xl border border-slate-800/70 bg-slate-900/40 p-3">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Blind spots</div>
              <ul className="list-disc space-y-1 pl-5 text-xs text-slate-300">
                {blindSpots.slice(0, 6).map((spot) => (
                  <li key={spot.id}>
                    {spot.description}{" "}
                    <span className="text-[10px] uppercase text-slate-500">({spot.impact})</span>
                    {spot.mitigation ? <span className="text-[11px] text-slate-400"> — {spot.mitigation}</span> : null}
                  </li>
                ))}
                {blindSpots.length > 6 ? (
                  <li className="text-[11px] text-slate-500">+{blindSpots.length - 6} additional blind spots</li>
                ) : null}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}
