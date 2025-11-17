"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

import { createDocument } from "@/lib/api";

interface DocumentFormProps {
  missionId: number;
  onCreated?: () => void;
}

export default function DocumentForm({ missionId, onCreated }: DocumentFormProps) {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!content.trim()) return;

    setSubmitting(true);
    setError(null);

    try {
      await createDocument(missionId, {
        title: title.trim() || undefined,
        content: content.trim(),
      });
      setTitle("");
      setContent("");
      onCreated?.();
      router.refresh();
    } catch (err) {
      console.error("Failed to create document", err);
      setError("Could not create document. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-4">
      <div>
        <h3 className="text-lg font-semibold">Add Mission Document</h3>
        <p className="text-sm text-slate-400">Upload intel or notes for the agent to analyze.</p>
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="doc-title">
          Title
        </label>
        <input
          id="doc-title"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Recon briefing"
        />
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="doc-content">
          Content
        </label>
        <textarea
          id="doc-content"
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          rows={6}
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Field intel..."
          required
        />
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={!content.trim() || submitting}
        className="inline-flex items-center justify-center rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Saving..." : "Save Document"}
      </button>
    </form>
  );
}
