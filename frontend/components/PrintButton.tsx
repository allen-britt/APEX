"use client";

interface PrintButtonProps {
  label?: string;
  className?: string;
}

export default function PrintButton({ label = "Print Report", className = "" }: PrintButtonProps) {
  return (
    <button
      type="button"
      className={[
        "rounded border border-slate-500 px-3 py-1 text-sm font-medium text-slate-100 transition hover:bg-slate-800 print:hidden",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      onClick={() => window.print()}
    >
      {label}
    </button>
  );
}
