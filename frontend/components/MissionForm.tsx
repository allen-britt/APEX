"use client";

import { FormEvent, useMemo, useState } from "react";

import { createMission, type Mission } from "@/lib/api";
import {
  describeAuthority,
  listAuthorities,
  listIntOptions,
  validateAuthorityIntSelection,
} from "@/lib/policy";

interface MissionFormProps {
  onCreated?: (mission: Mission) => void;
}

export default function MissionForm({ onCreated }: MissionFormProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [primaryAuthority, setPrimaryAuthority] = useState("");
  const [secondaryAuthorities, setSecondaryAuthorities] = useState<string[]>([]);
  const [intTypes, setIntTypes] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authorityOptions = useMemo(() => listAuthorities(), []);
  const intOptions = useMemo(() => listIntOptions(), []);
  const selectedAuthorityMeta = useMemo(
    () => describeAuthority(primaryAuthority),
    [primaryAuthority],
  );
  const intValidationErrors = useMemo(
    () => validateAuthorityIntSelection(primaryAuthority, intTypes),
    [primaryAuthority, intTypes],
  );

  const isSubmitDisabled =
    submitting ||
    !name.trim() ||
    !primaryAuthority ||
    intValidationErrors.length > 0;

  function toggleIntSelection(code: string) {
    setIntTypes((prev) => {
      if (prev.includes(code)) {
        return prev.filter((value) => value !== code);
      }
      return [...prev, code];
    });
  }

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const trimmedName = name.trim();
    const trimmedDescription = description.trim();

    if (!trimmedName || !primaryAuthority) {
      setError("Name and authority are required.");
      return;
    }
    if (intValidationErrors.length) {
      setError("Resolve policy conflicts before submitting.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const mission = await createMission({
        name: trimmedName,
        description: trimmedDescription || undefined,
        primary_authority: primaryAuthority,
        secondary_authorities: secondaryAuthorities,
        int_types: intTypes,
      });
      onCreated?.(mission);
      setName("");
      setDescription("");
      setPrimaryAuthority("");
      setSecondaryAuthorities([]);
      setIntTypes([]);
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

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="mission-authority">
          Mission Authority <span className="text-xs text-rose-300">(required)</span>
        </label>
        <select
          id="mission-authority"
          required
          value={primaryAuthority}
          onChange={(event) => setPrimaryAuthority(event.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm focus:border-cyan-500 focus:outline-none"
          title={
            selectedAuthorityMeta
              ? `${selectedAuthorityMeta.description} — ${selectedAuthorityMeta.prohibitions}`
              : "Select the governing authority lane"
          }
        >
          <option value="">Select an authority</option>
          {authorityOptions.map((authority) => (
            <option
              key={authority.code}
              value={authority.code}
              title={`${authority.description} — ${authority.prohibitions}`}
            >
              {authority.label}
            </option>
          ))}
        </select>
        {selectedAuthorityMeta && (
          <div className="rounded-lg border border-slate-700/80 bg-slate-900/80 p-3 text-sm">
            <p className="font-semibold text-slate-200">{selectedAuthorityMeta.label}</p>
            <p className="mt-1 text-slate-400">{selectedAuthorityMeta.description}</p>
            <p className="mt-2 text-xs text-amber-300">
              Guardrails: {selectedAuthorityMeta.prohibitions}
            </p>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium" htmlFor="mission-int-types">
          INT Lanes <span className="text-xs text-slate-400">(optional)</span>
        </label>
        <p className="text-xs text-slate-400">
          Pre-select any intelligence disciplines that scope this mission (optional). Tooltips describe
          policy handling requirements, and guardrails still apply if you select lanes.
        </p>
        <div id="mission-int-types" className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {intOptions.map((intOption) => {
            const checked = intTypes.includes(intOption.code);
            return (
              <label
                key={intOption.code}
                className={`flex cursor-pointer items-start gap-2 rounded-lg border px-3 py-2 text-sm transition ${{
                  true: "border-cyan-500/60 bg-slate-900",
                  false: "border-slate-700 bg-slate-900/60",
                }[String(checked) as "true" | "false"]}`}
                title={intOption.notes}
              >
                <input
                  type="checkbox"
                  className="mt-1 h-4 w-4 rounded border-slate-600 bg-slate-900 text-cyan-500 focus:ring-cyan-400"
                  checked={checked}
                  onChange={() => toggleIntSelection(intOption.code)}
                />
                <div>
                  <p className="font-medium text-slate-100">{intOption.label}</p>
                  <p className="text-xs text-slate-400">{intOption.notes}</p>
                </div>
              </label>
            );
          })}
        </div>
        {intValidationErrors.length > 0 && (
          <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-sm text-amber-100">
            <p className="font-semibold">Policy conflicts detected</p>
            <ul className="mt-2 list-inside list-disc space-y-1">
              {intValidationErrors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      <button
        type="submit"
        disabled={isSubmitDisabled}
        className="inline-flex items-center justify-center rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Creating..." : "Create Mission"}
      </button>
    </form>
  );
}
