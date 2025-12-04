import type { Mission } from "@/lib/api";
import { describeAuthority, formatIntLabel } from "@/lib/policy";

interface PolicyFootprintProps {
  mission: Mission;
  layout?: "stacked" | "inline";
  showSecondary?: boolean;
}

const badgeBase =
  "inline-flex items-center rounded-full border border-slate-600/60 bg-slate-900/80 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide";

export default function PolicyFootprint({ mission, layout = "stacked", showSecondary = true }: PolicyFootprintProps) {
  const primaryAuthorityCode = mission.primary_authority?.toUpperCase() ?? "";
  const authorityMeta = describeAuthority(primaryAuthorityCode);
  const authorityLabel = (authorityMeta?.label ?? primaryAuthorityCode) || "Authority pending";
  const authorityDescription = authorityMeta?.description ?? null;
  const authorityProhibitions = authorityMeta?.prohibitions ?? null;
  const intTypes = mission.int_types ?? [];
  const secondary = mission.secondary_authorities?.filter(Boolean) ?? [];

  if (layout === "inline") {
    return (
      <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
        <span className={`${badgeBase} text-cyan-200`}>{authorityLabel}</span>
        {intTypes.length ? (
          <span className="text-xs uppercase tracking-wide text-slate-500">INT:</span>
        ) : null}
        {intTypes.map((code) => (
          <span key={code} className={`${badgeBase} border-slate-700/70 text-emerald-200`}>
            {formatIntLabel(code)}
          </span>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3 text-sm text-slate-300">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs uppercase tracking-wide text-slate-500">Authority lane</span>
        <span className={`${badgeBase} text-cyan-100`}>{authorityLabel}</span>
      </div>
      {authorityDescription ? (
        <p className="text-xs text-slate-400">{authorityDescription}</p>
      ) : null}
      {authorityProhibitions ? (
        <p className="text-xs text-amber-300">Guardrail: {authorityProhibitions}</p>
      ) : null}
      {showSecondary && secondary.length ? (
        <div className="space-y-1">
          <p className="text-xs uppercase tracking-wide text-slate-500">Secondary authorities</p>
          <div className="flex flex-wrap gap-2">
            {secondary.map((code) => (
              <span key={code} className={`${badgeBase} border-slate-700/70 text-indigo-200`}>
                {code}
              </span>
            ))}
          </div>
        </div>
      ) : null}
      <div className="space-y-1">
        <p className="text-xs uppercase tracking-wide text-slate-500">INT lanes</p>
        {intTypes.length ? (
          <div className="flex flex-wrap gap-2">
            {intTypes.map((code) => (
              <span key={code} className={`${badgeBase} border-slate-700/70 text-emerald-200`}>
                {formatIntLabel(code)}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500">No INTs selected</p>
        )}
      </div>
    </div>
  );
}
