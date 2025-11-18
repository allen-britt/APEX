import Link from "next/link";

import PrintButton from "@/components/PrintButton";
import {
  getMissionReport,
  fetchActiveModelInfo,
  type AgentRun,
  type Entity,
  type Event,
  type Document,
} from "@/lib/api";

interface MissionReportPageProps {
  params: { id: string };
  searchParams: { runId?: string };
}

function bucketInsightSections(sections: { label: string; items: string[] }[]): InsightBuckets {
  const buckets: InsightBuckets = { corroborated: [], trends: [], contradictions: [] };

  sections.forEach((section) => {
    const normalized = section.label.toLowerCase();
    if (normalized.includes("corroborated")) {
      buckets.corroborated.push(...section.items);
    } else if (normalized.includes("contradiction")) {
      buckets.contradictions.push(...section.items);
    } else if (normalized.includes("trend") || normalized.includes("hypoth")) {
      buckets.trends.push(...section.items);
    } else {
      buckets.trends.push(...section.items);
    }
  });

  return buckets;
}

type ExtendedAgentRun = AgentRun & {
  operational_estimate?: string | null;
  cross_document_insights?: string | null;
  profile?: string | null;
};

const DEFAULT_CLASSIFICATION = "UNCLASSIFIED";

interface InsightBuckets {
  corroborated: string[];
  trends: string[];
  contradictions: string[];
}

function formatDate(value: string | null | undefined, fallback = "—") {
  if (!value) return fallback;
  return new Date(value).toLocaleString();
}

function truncate(text: string | null | undefined, max = 220) {
  if (!text) return "—";
  if (text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
}

function parseInsightSections(value: string | null | undefined) {
  if (!value?.trim()) return [] as { label: string; items: string[] }[];
  const lines = value.split("\n").map((line) => line.trim()).filter(Boolean);
  const sections: { label: string; items: string[] }[] = [];
  let current = { label: "Insights", items: [] as string[] };

  const isHeading = (line: string) => line.endsWith(":") || ["Corroborated Findings", "Contradictions", "Notable Trends"].some((heading) => line.startsWith(heading));

  lines.forEach((line) => {
    if (isHeading(line)) {
      if (current.items.length) {
        sections.push(current);
      }
      const cleanLabel = line.replace(/:$/, "").trim();
      current = { label: cleanLabel, items: [] };
    } else if (/^[-*]/.test(line)) {
      current.items.push(line.replace(/^[-*]\s*/, ""));
    } else {
      current.items.push(line);
    }
  });

  if (current.items.length) {
    sections.push(current);
  }

  return sections;
}

const ENTITY_GROUPS: { key: string; label: string; matchers: RegExp }[] = [
  { key: "persons", label: "PERSONS", matchers: /(person|individual|operative|agent|commander|soldier)/i },
  { key: "locations", label: "LOCATIONS", matchers: /(location|sector|checkpoint|city|region|area|zone)/i },
  { key: "facilities", label: "FACILITIES", matchers: /(facility|base|compound|installation|hq|center)/i },
  { key: "businesses", label: "BUSINESSES", matchers: /(company|organization|firm|contractor|vendor|outlet)/i },
];

function categorizeEntity(entity: Entity) {
  const typeLabel = entity.type?.toLowerCase() ?? "";
  const group = ENTITY_GROUPS.find((entry) => entry.matchers.test(typeLabel));
  return group?.key ?? "other";
}

function summarizeEntities(entities: Entity[]) {
  const counts: Record<string, number> = {
    persons: 0,
    locations: 0,
    facilities: 0,
    businesses: 0,
    other: 0,
  };

  entities.forEach((entity) => {
    const key = categorizeEntity(entity);
    counts[key] += 1;
  });

  return counts;
}

function groupEntities(entities: Entity[]) {
  const groups: Record<string, { label: string; items: Entity[] }> = {
    persons: { label: "PERSONS", items: [] },
    locations: { label: "LOCATIONS", items: [] },
    facilities: { label: "FACILITIES", items: [] },
    businesses: { label: "BUSINESSES", items: [] },
    other: { label: "ITEMS / OTHER", items: [] },
  };

  entities.forEach((entity) => {
    const key = categorizeEntity(entity);
    groups[key].items.push(entity);
  });

  return Object.values(groups).filter((group) => group.items.length);
}

function sortEventsChronologically(events: Event[]) {
  return [...events].sort((a, b) => {
    const tsA = a.timestamp ? new Date(a.timestamp).getTime() : Number.POSITIVE_INFINITY;
    const tsB = b.timestamp ? new Date(b.timestamp).getTime() : Number.POSITIVE_INFINITY;
    return tsA - tsB;
  });
}

function guardrailBadgeClasses(score: string | undefined) {
  const normalized = (score || "").toUpperCase();
  if (normalized === "WARNING" || normalized === "REVIEW") return "bg-rose-500/20 text-rose-200 border border-rose-400";
  if (normalized === "CAUTION") return "bg-amber-500/20 text-amber-100 border border-amber-400";
  return "bg-emerald-500/15 text-emerald-100 border border-emerald-400";
}

function guardrailSummary(score: string | undefined) {
  const normalized = (score || "ok").toLowerCase();
  if (normalized === "warning" || normalized === "blocked" || normalized === "review") {
    return "Analytic guardrails detected elevated risk factors that require attention.";
  }
  if (normalized === "caution") {
    return "Guardrails flag moderate confidence; proceed with additional validation.";
  }
  return "Guardrails report no critical blockers; assessment confidence is solid.";
}

function splitIntoParagraphs(text: string | null | undefined) {
  if (!text) return [] as string[];
  const raw = text
    .split(/\n+/)
    .map((chunk) => chunk.trim())
    .filter(Boolean);
  if (raw.length > 1) {
    return raw;
  }
  const sentences = (text.match(/[^.!?]+[.!?]+/g) || [text]).map((sentence) => sentence.trim());
  const paragraphs: string[] = [];
  let buffer = "";
  sentences.forEach((sentence) => {
    buffer = buffer ? `${buffer} ${sentence}` : sentence;
    if (buffer.length > 240) {
      paragraphs.push(buffer.trim());
      buffer = "";
    }
  });
  if (buffer) paragraphs.push(buffer.trim());
  return paragraphs;
}

function parseOperationalEstimate(value: string | null | undefined) {
  const template = {
    situation: "No data provided.",
    enemy: "No data provided.",
    friendly: "No data provided.",
    assessment: "No data provided.",
    recommendations: "No data provided.",
  };

  if (!value) {
    return template;
  }

  const normalized = value.split(/\n+/);
  let current: keyof typeof template = "situation";
  normalized.forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const headingMatch = trimmed.match(/^(Situation|Enemy|Target|Friendly|Assessment|Risk|Recommendation|Course of Action)/i);
    if (headingMatch) {
      const heading = headingMatch[1].toLowerCase();
      if (heading.startsWith("situation")) current = "situation";
      else if (heading.startsWith("enemy") || heading.startsWith("target")) current = "enemy";
      else if (heading.startsWith("friendly")) current = "friendly";
      else if (heading.startsWith("assessment") || heading.startsWith("risk")) current = "assessment";
      else current = "recommendations";
      template[current] = trimmed.replace(/^[^:]+:\s*/, "").trim() || template[current];
    } else {
      template[current] = template[current] === "No data provided." ? trimmed : `${template[current]} ${trimmed}`;
    }
  });

  return template;
}

function inferAreaOfOperations(entities: Entity[]) {
  const locations = entities.filter((entity) => (entity.type || "").toLowerCase().includes("location") || (entity.type || "").toLowerCase().includes("area"));
  if (!locations.length) return "Not specified";
  return locations
    .slice(0, 3)
    .map((entity) => entity.name)
    .join(", ");
}

function extractMissionObjective(description?: string | null) {
  if (!description) return "Not specified";
  const sentence = description.split(/(?<=[.!?])\s+/)[0];
  return sentence?.trim() || "Not specified";
}

function computeMissionTimeframe(missionCreated: string, latestTimestamp: string | null | undefined) {
  const start = formatDate(missionCreated);
  const end = formatDate(latestTimestamp || missionCreated);
  return `${start} – ${end}`;
}

function formatDocumentType(doc: Document) {
  if (!doc.title) return "—";
  const typeMatch = doc.title.match(/(HUMINT|SIGINT|OSINT|IMINT|DOC)/i);
  if (typeMatch) return typeMatch[1].toUpperCase();
  const ext = doc.title.split(".").pop();
  if (ext && ext.length <= 5) {
    return ext.toUpperCase();
  }
  return "—";
}

function formatInclusionFlag(include?: boolean) {
  return include === false ? "✕" : "✓";
}

function parseNextStepRows(nextSteps: string[] | null | undefined) {
  if (!nextSteps?.length) return [] as { idx: number; task: string; notes: string }[];
  return nextSteps.map((step, index) => {
    const parts = step.split(/\s+-\s+|:\s+/);
    const task = parts[0]?.trim() || step.trim();
    const notes = parts.slice(1).join(" – ").trim();
    return {
      idx: index + 1,
      task,
      notes: notes || "—",
    };
  });
}

function formatEventSources() {
  return "Mission documents";
}

export default async function MissionReportPage({ params, searchParams }: MissionReportPageProps) {
  const missionId = Number(params.id);
  if (Number.isNaN(missionId)) {
    return <div className="text-red-400">Invalid mission id.</div>;
  }

  const runId = searchParams.runId ? Number(searchParams.runId) : undefined;

  try {
    const [report, activeModelInfo] = await Promise.all([
      getMissionReport(missionId, runId),
      fetchActiveModelInfo().catch(() => null),
    ]);

    const {
      mission,
      documents,
      run,
      entities,
      events,
      guardrail,
      gaps,
      next_steps: nextSteps,
      delta_summary: deltaSummary,
      generated_at: generatedAt,
    } = report;

    const extendedRun = run as ExtendedAgentRun | null;
    const profileLabel = extendedRun?.profile?.toUpperCase() ?? "Not specified";
    const runTimestamp = run ? formatDate(run.created_at) : "No runs executed";
    const latestRunLabel = run ? `#${run.id}` : "N/A";
    const modelLabel = activeModelInfo?.active_model;
    const sortedEvents = sortEventsChronologically(events);
    const entityCounts = summarizeEntities(entities);
    const groupedEntities = groupEntities(entities);
    const insightSections = parseInsightSections(extendedRun?.cross_document_insights);
    const insightBuckets = bucketInsightSections(insightSections);
    const infoGaps = gaps ?? [];
    const selfCheckNotes = (guardrail?.issues ?? []).filter((issue) => /self-check/i.test(issue));
    const otherGuardrailIssues = (guardrail?.issues ?? []).filter((issue) => !/self-check/i.test(issue));
    const classification = DEFAULT_CLASSIFICATION;
    const latestChrono = sortedEvents.length ? sortedEvents[sortedEvents.length - 1].timestamp : run?.created_at;
    const missionTimeframe = computeMissionTimeframe(mission.created_at, latestChrono);
    const missionObjective = extractMissionObjective(mission.description);
    const areaOfOperations = inferAreaOfOperations(entities);
    const summaryParagraphs = splitIntoParagraphs(run?.summary ?? "");
    const operationalEstimate = parseOperationalEstimate(extendedRun?.operational_estimate);
    const nextStepRows = parseNextStepRows(nextSteps);
    const guardrailStatus = guardrail?.overall_score ?? "OK";
    const guardrailSentence = guardrailSummary(guardrailStatus);

    return (
      <>
        <style>{`
          @page {
            margin: 1in;
          }
          @media print {
            body {
              background: white;
            }
            .report-page {
              padding-top: 2.5rem;
              padding-bottom: 2.5rem;
            }
            .report-banner-top,
            .report-banner-bottom {
              position: fixed;
              left: 0;
              right: 0;
              text-align: center;
              background: #020617;
              color: #f8fafc;
              padding: 0.35rem 0;
              letter-spacing: 0.3em;
              font-size: 0.65rem;
              z-index: 50;
            }
            .report-banner-top {
              top: 0;
            }
            .report-banner-bottom {
              bottom: 0;
            }
            .report-footer {
              position: fixed;
              bottom: 0.4in;
              left: 0;
              right: 0;
              text-align: center;
              font-size: 0.65rem;
              color: #475569;
            }
            .page-number::after {
              content: "Page " counter(page) " of " counter(pages);
            }
          }
        `}</style>
        <div className="report-page mx-auto max-w-4xl space-y-8 py-8 print:bg-white print:text-black">
          <div className="report-banner-top text-xs font-semibold uppercase tracking-[0.35em] text-slate-100">
            {classification}
          </div>

          <header className="rounded-xl border border-slate-800 bg-slate-950/40 p-6 shadow-inner print:border-slate-300 print:bg-white">
            <div className="flex flex-col gap-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm uppercase tracking-wide text-slate-400">Project APEX Mission Report</p>
                  <h1 className="text-3xl font-bold text-white">{mission.name}</h1>
                  <p className="text-sm text-slate-400">Mission ID #{mission.id}</p>
                </div>
                <div className="text-sm text-slate-300">
                  <p>
                    Latest analysis: <span className="font-semibold text-white">{latestRunLabel}</span>
                  </p>
                  <p>
                    Run timestamp: <span className="font-semibold text-white">{runTimestamp}</span>
                  </p>
                  <p>
                    Model / Profile: <span className="font-semibold text-white">{modelLabel ?? "—"}</span> / {profileLabel}
                  </p>
                </div>
                <div className="flex gap-3 print:hidden">
                  <Link
                    href={`/missions/${mission.id}`}
                    className="rounded border border-slate-600 px-3 py-1 text-sm font-medium text-slate-100 transition hover:bg-slate-800"
                  >
                    Back to mission
                  </Link>
                  <PrintButton className="bg-slate-900/40" />
                </div>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-4 text-xs text-slate-300">
                <p className="font-semibold uppercase tracking-wide text-slate-400">Table of Contents</p>
                <ol className="mt-2 grid gap-x-6 gap-y-1 text-[0.75rem] md:grid-cols-2">
                  {["Mission Overview", "Source Documents", "Latest Analysis", "Cross-Document Insights", "Recommended Next Steps", "Guardrails & Confidence", "Entities", "Timeline of Events"].map((item, index) => (
                    <li key={item}> {index + 1}. {item}</li>
                  ))}
                </ol>
              </div>
            </div>
          </header>

          <section id="section-1" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">1. Mission Overview</h2>
            <p className="mt-2 text-sm text-slate-300">Generated {formatDate(generatedAt)}</p>
            <div className="mt-4 space-y-3 text-sm text-slate-200">
              <p className="text-base text-slate-100">{mission.description || "No description provided."}</p>
              <ul className="list-disc space-y-1 pl-5">
                <li>
                  <span className="font-semibold">Objective:</span> {missionObjective}
                </li>
                <li>
                  <span className="font-semibold">Area of Operations:</span> {areaOfOperations}
                </li>
                <li>
                  <span className="font-semibold">Timeframe:</span> {missionTimeframe}
                </li>
              </ul>
            </div>
          </section>

          <section id="section-2" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">2. Source Documents</h2>
              <span className="text-sm text-slate-400">{documents.length} files</span>
            </div>
            <div className="mt-4 overflow-x-auto rounded-lg border border-slate-800 print:border-slate-300">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-900/60 text-slate-200 print:bg-slate-100 print:text-slate-900">
                  <tr>
                    <th className="px-4 py-2 text-left">#</th>
                    <th className="px-4 py-2 text-left">Title</th>
                    <th className="px-4 py-2 text-left">Type</th>
                    <th className="px-4 py-2 text-left">Created</th>
                    <th className="px-4 py-2 text-left">Included?</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-center text-slate-400" colSpan={5}>
                        No documents uploaded.
                      </td>
                    </tr>
                  )}
                  {documents.map((doc, index) => (
                    <tr
                      key={doc.id}
                      className={`border-t border-slate-800 print:border-slate-200 ${doc.include_in_analysis === false ? "bg-slate-900/40 text-slate-400" : "text-slate-100"}`}
                    >
                      <td className="px-4 py-2">{index + 1}</td>
                      <td className="px-4 py-2 font-medium">{doc.title || "Untitled document"}</td>
                      <td className="px-4 py-2 text-slate-400">{formatDocumentType(doc)}</td>
                      <td className="px-4 py-2 text-slate-400">{formatDate(doc.created_at)}</td>
                      <td className="px-4 py-2">{formatInclusionFlag(doc.include_in_analysis)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section id="section-3" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 space-y-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">3. Latest Analysis</h2>
            {run ? (
              <div className="space-y-6">
                <article className="space-y-3">
                  <h3 className="text-lg font-semibold text-slate-100">3.1 Summary</h3>
                  {summaryParagraphs.length ? (
                    <div className="space-y-3 text-sm text-slate-200">
                      {summaryParagraphs.map((paragraph, idx) => (
                        <p key={idx}>{paragraph}</p>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-slate-400">No summary available.</p>
                  )}
                </article>

                <article>
                  <h3 className="text-lg font-semibold text-slate-100">3.2 Operational Estimate</h3>
                  <div className="mt-3 grid gap-4 text-sm text-slate-200 md:grid-cols-2">
                    <div>
                      <p className="font-semibold">Situation</p>
                      <p className="text-slate-300">{operationalEstimate.situation}</p>
                    </div>
                    <div>
                      <p className="font-semibold">Enemy / Target</p>
                      <p className="text-slate-300">{operationalEstimate.enemy}</p>
                    </div>
                    <div>
                      <p className="font-semibold">Friendly Considerations</p>
                      <p className="text-slate-300">{operationalEstimate.friendly}</p>
                    </div>
                    <div>
                      <p className="font-semibold">Assessment & Risk</p>
                      <p className="text-slate-300">{operationalEstimate.assessment}</p>
                    </div>
                    <div className="md:col-span-2">
                      <p className="font-semibold">Recommended Course(s) of Action</p>
                      <p className="text-slate-300">{operationalEstimate.recommendations}</p>
                    </div>
                  </div>
                </article>
              </div>
            ) : (
              <p className="text-sm text-slate-400">No agent runs executed for this mission.</p>
            )}
          </section>

          <section id="section-4" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">4. Cross-Document Insights</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 print:border-slate-200">
                <p className="font-semibold text-slate-100">Corroborated Findings</p>
                {insightBuckets.corroborated.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                    {insightBuckets.corroborated.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-slate-400">No corroborated findings recorded.</p>
                )}
              </div>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 print:border-slate-200">
                <p className="font-semibold text-slate-100">Notable Trends / Hypotheses</p>
                {insightBuckets.trends.length ? (
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                    {insightBuckets.trends.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-slate-400">No notable trends recorded.</p>
                )}
              </div>
            </div>
          </section>

          <section id="section-5" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">5. Recommended Next Steps</h2>
            <div className="mt-4 overflow-x-auto rounded-lg border border-slate-800 print:border-slate-300">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-900/60 text-slate-200 print:bg-slate-100 print:text-slate-900">
                  <tr>
                    <th className="px-4 py-2 text-left">#</th>
                    <th className="px-4 py-2 text-left">Line of Effort / Task</th>
                    <th className="px-4 py-2 text-left">Notes / Purpose</th>
                  </tr>
                </thead>
                <tbody>
                  {nextStepRows.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-center text-slate-400" colSpan={3}>
                        No recommendations captured.
                      </td>
                    </tr>
                  )}
                  {nextStepRows.map((row) => (
                    <tr key={row.idx} className="border-t border-slate-800 text-slate-100 print:border-slate-200">
                      <td className="px-4 py-2">{row.idx}</td>
                      <td className="px-4 py-2 font-medium">{row.task}</td>
                      <td className="px-4 py-2 text-slate-300">{row.notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section id="section-6" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">6. Guardrails & Confidence</h2>
            <div className="mt-4 space-y-4">
              <div className="flex flex-wrap items-center gap-3">
                <span className={`inline-flex items-center rounded-full px-4 py-1 text-sm font-semibold uppercase tracking-wide ${guardrailBadgeClasses(guardrailStatus)}`}>
                  {guardrailStatus}
                </span>
                <p className="text-sm text-slate-300">{guardrailSentence}</p>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 print:border-slate-200">
                  <p className="font-semibold text-slate-100">Analytic Gaps</p>
                  {infoGaps.length ? (
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                      {infoGaps.map((gap, idx) => (
                        <li key={idx}>{gap}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400">No major gaps recorded.</p>
                  )}
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 print:border-slate-200">
                  <p className="font-semibold text-slate-100">Self-Check Notes</p>
                  {selfCheckNotes.length || otherGuardrailIssues.length ? (
                    <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
                      {[...selfCheckNotes, ...otherGuardrailIssues].map((issue, idx) => (
                        <li key={idx}>{issue.replace(/^Analytic Review:\s*/i, "").trim()}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-sm text-slate-400">No additional notes.</p>
                  )}
                </div>
              </div>
              {deltaSummary && (
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-sm text-slate-200 print:border-slate-200">
                  <p className="font-semibold text-slate-100">Delta From Previous Run</p>
                  <p className="mt-1 whitespace-pre-line text-slate-200">{deltaSummary}</p>
                </div>
              )}
            </div>
          </section>

          <section id="section-7" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <div className="flex flex-col gap-2">
              <h2 className="text-xl font-semibold">7. Entities</h2>
              <p className="text-sm text-slate-400">
                Persons: {entityCounts.persons} • Locations: {entityCounts.locations} • Facilities: {entityCounts.facilities} • Businesses: {entityCounts.businesses} • Other: {entityCounts.other}
              </p>
            </div>
            {groupedEntities.length ? (
              <div className="mt-4 space-y-6">
                {groupedEntities.map((group) => (
                  <div key={group.label}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">{group.label}</p>
                    <div className="mt-2 overflow-x-auto rounded-lg border border-slate-800 print:border-slate-300">
                      <table className="min-w-full text-sm">
                        <thead className="bg-slate-900/50 text-slate-200 print:bg-slate-100 print:text-slate-900">
                          <tr>
                            <th className="px-3 py-2 text-left">Name</th>
                            <th className="px-3 py-2 text-left">Type</th>
                            <th className="px-3 py-2 text-left">Role / Description</th>
                            <th className="px-3 py-2 text-left">Confidence</th>
                            <th className="px-3 py-2 text-left">Key Locations</th>
                          </tr>
                        </thead>
                        <tbody>
                          {group.items.map((entity) => (
                            <tr key={entity.id} className="border-t border-slate-800 text-slate-100 print:border-slate-200">
                              <td className="px-3 py-2 font-semibold">{entity.name}</td>
                              <td className="px-3 py-2 text-slate-300">{entity.type || "—"}</td>
                              <td className="px-3 py-2 text-slate-300">{entity.description || "—"}</td>
                              <td className="px-3 py-2 text-slate-400">Not provided</td>
                              <td className="px-3 py-2 text-slate-400">—</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-400">No entities extracted for this mission.</p>
            )}
          </section>

          <section id="section-8" className="rounded-xl border border-slate-800 bg-slate-950/30 p-6 print:border-slate-300 print:bg-white">
            <h2 className="text-xl font-semibold">8. Timeline of Events</h2>
            <div className="mt-4 overflow-x-auto rounded-lg border border-slate-800 print:border-slate-300">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-900/50 text-slate-200 print:bg-slate-100 print:text-slate-900">
                  <tr>
                    <th className="px-4 py-2 text-left">Date / Time</th>
                    <th className="px-4 py-2 text-left">Location</th>
                    <th className="px-4 py-2 text-left">Event</th>
                    <th className="px-4 py-2 text-left">Source(s)</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEvents.length === 0 && (
                    <tr>
                      <td className="px-4 py-6 text-center text-slate-400" colSpan={4}>
                        No events captured.
                      </td>
                    </tr>
                  )}
                  {sortedEvents.map((event) => (
                    <tr key={event.id} className="border-t border-slate-800 text-slate-100 print:border-slate-200">
                      <td className="px-4 py-2 text-slate-300">{formatDate(event.timestamp)}</td>
                      <td className="px-4 py-2 text-slate-300">{event.location || "—"}</td>
                      <td className="px-4 py-2">
                        <p className="font-semibold">{event.title}</p>
                        {event.summary && <p className="text-slate-300">{truncate(event.summary)}</p>}
                      </td>
                      <td className="px-4 py-2 text-slate-300">{formatEventSources()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <div className="report-banner-bottom text-xs font-semibold uppercase tracking-[0.35em] text-slate-100">
            {classification}
          </div>
          <div className="report-footer">
            <span className="page-number" />
          </div>
        </div>
      </>
    );
  } catch (error) {
    console.error("Failed to load report", error);
    return (
      <div className="card border border-rose-800 bg-rose-950/40 text-sm text-rose-200">
        Failed to load report. Please verify the backend is running.
      </div>
    );
  }
}
