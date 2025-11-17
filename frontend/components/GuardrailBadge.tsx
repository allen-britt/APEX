interface GuardrailBadgeProps {
  status: string;
  issues?: string[] | null;
}

const STATUS_STYLES: Record<string, string> = {
  ok: "bg-emerald-900/40 text-emerald-300 border-emerald-700",
  warning: "bg-amber-900/40 text-amber-300 border-amber-700",
  blocked: "bg-rose-900/40 text-rose-300 border-rose-700",
};

export default function GuardrailBadge({ status, issues }: GuardrailBadgeProps) {
  const normalized = status?.toLowerCase() ?? "ok";
  const style = STATUS_STYLES[normalized] ?? STATUS_STYLES.ok;

  return (
    <div className="space-y-2">
      <span className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${style}`}>
        Guardrail: {status.toUpperCase()}
      </span>
      {issues && issues.length > 0 && (
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-300">
          {issues.map((issue, index) => (
            <li key={`${issue}-${index}`}>{issue}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
