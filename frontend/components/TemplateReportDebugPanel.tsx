"use client";

import type { TemplateReportResponse } from "@/lib/api";

interface TemplateReportDebugPanelProps {
  report: TemplateReportResponse | null;
  lastRequestPayload?: unknown;
}

export function TemplateReportDebugPanel({ report, lastRequestPayload }: TemplateReportDebugPanelProps) {
  if (!report && !lastRequestPayload) {
    return null;
  }

  return (
    <div className="mt-3 rounded-md border border-slate-800 bg-slate-900 p-3 text-xs text-slate-100">
      <details>
        <summary className="cursor-pointer font-semibold">Debug (context &amp; response)</summary>
        <div className="mt-2 grid gap-3 md:grid-cols-2">
          <div className="overflow-auto rounded bg-slate-950 p-2">
            <div className="mb-1 font-semibold text-slate-300">Last request payload</div>
            <pre className="whitespace-pre-wrap break-all">
              {JSON.stringify(lastRequestPayload ?? null, null, 2)}
            </pre>
          </div>
          <div className="overflow-auto rounded bg-slate-950 p-2">
            <div className="mb-1 font-semibold text-slate-300">TemplateReportResponse</div>
            <pre className="whitespace-pre-wrap break-all">
              {JSON.stringify(report ?? null, null, 2)}
            </pre>
          </div>
        </div>
      </details>
    </div>
  );
}
