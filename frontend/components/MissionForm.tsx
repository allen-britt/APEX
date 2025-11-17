"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createMission } from "@/lib/api";

export default function MissionForm() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!name.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      await createMission({ name: name.trim(), description: description.trim() || undefined });
      setName("");
      setDescription("");
      router.refresh();
    } catch (err) {
      console.error("Failed to create mission", err);
      setError("Failed to create mission. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div>
        <h2 className="text-lg font-semibold">Create Mission</h2>
        <p className="text-sm text-slate-400">Draft a new operation brief to analyze.</p>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="mission-name">
          Name
        </label>
        <input
          id="mission-name"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Operation Sentinel"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="mission-description">
          Description
        </label>
        <textarea
          id="mission-description"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          rows={3}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Short objective overview"
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={!name.trim() || submitting}
        className="inline-flex items-center justify-center rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Creating..." : "Create Mission"}
      </button>
    </form>
  );
}
