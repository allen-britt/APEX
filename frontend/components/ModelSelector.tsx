"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import type { ModelInfo } from "@/lib/api";
import { setActiveModel } from "@/lib/api";

interface ModelSelectorProps {
  models: ModelInfo[];
  activeModel: string;
}

export function ModelSelector({ models, activeModel }: ModelSelectorProps) {
  const router = useRouter();
  const [selected, setSelected] = useState(activeModel);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const handleSave = async () => {
    setMessage(null);
    await setActiveModel(selected);
    setMessage(`Active model set to "${selected}".`);
    startTransition(() => {
      router.refresh();
    });
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-400 focus:outline-none"
        >
          {models.map((model) => (
            <option key={model.name} value={model.name}>
              {model.name}
              {model.source ? ` (${model.source})` : ""}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={handleSave}
          disabled={isPending}
          className="rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-cyan-500 disabled:opacity-60"
        >
          {isPending ? "Saving…" : "Set active"}
        </button>
      </div>
      <p className="text-xs text-slate-500">
        Current active model: <span className="text-slate-100">{activeModel}</span>
      </p>
      {message && <p className="text-xs text-emerald-400">{message}</p>}
    </div>
  );
}
