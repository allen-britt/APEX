"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { createMissionDataset } from "@/lib/api";

interface MissionDatasetFormProps {
  missionId: number;
  onCreated?: () => void;
}

const defaultJson = `{
  "rows": [
    { "id": 1, "value": 42 }
  ]
}`;

export default function MissionDatasetForm({ missionId, onCreated }: MissionDatasetFormProps) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [jsonSource, setJsonSource] = useState(defaultJson);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim() || !jsonSource.trim()) return;

    let parsed: unknown;
    try {
      parsed = JSON.parse(jsonSource);
    } catch (err) {
      console.error("Invalid JSON for dataset", err);
      setError("Sources must be valid JSON.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await createMissionDataset(missionId, {
        name: name.trim(),
        sources: [
          {
            type: "json_inline",
            data: parsed,
          },
        ],
      });
      setName("");
      setJsonSource(defaultJson);
      onCreated?.();
      router.refresh();
    } catch (err) {
      console.error("Failed to create mission dataset", err);
      setError("Could not create dataset. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Create dataset</h3>
        <p className="text-sm text-slate-400">
          Paste JSON data for a single inline source. AggreGator will profile it automatically.
        </p>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="dataset-name">
          Name
        </label>
        <input
          id="dataset-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Sensor snapshot"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="dataset-source">
          JSON source (inline)
        </label>
        <textarea
          id="dataset-source"
          value={jsonSource}
          onChange={(event) => setJsonSource(event.target.value)}
          rows={8}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-mono focus:border-cyan-500 focus:outline-none"
          required
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={!name.trim() || !jsonSource.trim() || submitting}
        className="inline-flex items-center justify-center rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Profiling…" : "Create dataset"}
      </button>
    </form>
  );
}
