"use client";

import { useMemo, useState } from "react";

import MissionAuthorityHistory from "@/components/MissionAuthorityHistory";
import PolicyFootprint from "@/components/PolicyFootprint";
import { useMission } from "@/context/MissionContext";
import type { Mission } from "@/lib/api";
import { pivotMissionAuthority } from "@/lib/api";
import {
  formatAuthorityLabel,
  getAllowedPivots,
  getAuthorityMeta,
  normalizeAuthorityId,
  type AuthorityId,
  type AuthorityPivotRule,
} from "@/lib/authorityPolicy";

interface MissionDetailProps {
  mission: Mission;
}

function formatDate(value: string) {
  return new Date(value).toLocaleString();
}

export default function MissionDetail({ mission }: MissionDetailProps) {
  const { refreshMission } = useMission();
  const [pivotModalOpen, setPivotModalOpen] = useState(false);

  const primaryAuthorityId = useMemo(
    () => normalizeAuthorityId(mission.primary_authority ?? undefined),
    [mission.primary_authority],
  );
  const allowedPivots = useMemo<AuthorityPivotRule[]>(() => {
    if (!primaryAuthorityId) return [];
    return getAllowedPivots(primaryAuthorityId);
  }, [primaryAuthorityId]);

  const primaryAuthorityLabel = formatAuthorityLabel(mission.primary_authority ?? "");
  const authorityMeta = primaryAuthorityId ? getAuthorityMeta(primaryAuthorityId) : null;

  return (
    <div className="space-y-4">
      <div className="card space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Mission</p>
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-2xl font-semibold text-cyan-100">{mission.name}</h2>
            {allowedPivots.length > 0 && (
              <button
                type="button"
                onClick={() => setPivotModalOpen(true)}
                className="inline-flex items-center gap-2 rounded-lg border border-cyan-500/50 bg-cyan-500/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-wide text-cyan-200 transition hover:bg-cyan-500/20"
              >
                Pivot authority
              </button>
            )}
          </div>
        </div>
        {mission.description && (
          <p className="text-sm leading-relaxed text-slate-300">{mission.description}</p>
        )}
        <PolicyFootprint mission={mission} layout="stacked" />
        {allowedPivots.length > 0 ? (
          <p className="text-xs text-slate-400">
            {primaryAuthorityLabel} can pivot to {allowedPivots.length} authority
            {allowedPivots.length > 1 ? " lanes" : " lane"}. Pivots are audited and require solid justification.
          </p>
        ) : (
          <p className="text-xs text-slate-500">
            No policy-approved pivots are currently available for this authority lane.
          </p>
        )}
        <div className="text-xs text-slate-500">
          <span>Created: {formatDate(mission.created_at)}</span>
          <span className="mx-2">•</span>
          <span>Updated: {formatDate(mission.updated_at)}</span>
        </div>
      </div>

      <MissionAuthorityHistory mission={mission} />

      {pivotModalOpen && primaryAuthorityId && allowedPivots.length > 0 && (
        <PivotAuthorityModal
          missionId={mission.id}
          currentAuthorityLabel={primaryAuthorityLabel}
          currentAuthorityDescription={authorityMeta?.description ?? ""}
          allowedPivots={allowedPivots}
          onClose={() => setPivotModalOpen(false)}
          onPivotSuccess={() => {
            refreshMission();
            setPivotModalOpen(false);
          }}
        />
      )}
    </div>
  );
}

interface PivotAuthorityModalProps {
  missionId: number;
  currentAuthorityLabel: string;
  currentAuthorityDescription?: string;
  allowedPivots: AuthorityPivotRule[];
  onClose: () => void;
  onPivotSuccess: () => void;
}

function PivotAuthorityModal({
  missionId,
  currentAuthorityLabel,
  currentAuthorityDescription,
  allowedPivots,
  onClose,
  onPivotSuccess,
}: PivotAuthorityModalProps) {
  const [targetAuthority, setTargetAuthority] = useState<AuthorityId>(allowedPivots[0]!.to);
  const [justification, setJustification] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedRule = allowedPivots.find((rule) => rule.to === targetAuthority) ?? allowedPivots[0];
  const targetLabel = formatAuthorityLabel(selectedRule?.to);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!targetAuthority) {
      setError("Select a target authority.");
      return;
    }
    if (justification.trim().length < 10) {
      setError("Justification must be at least 10 characters.");
      return;
    }

    try {
      setSubmitting(true);
      setError(null);
      await pivotMissionAuthority(missionId, {
        target_authority: targetAuthority,
        justification: justification.trim(),
      });
      onPivotSuccess();
      setJustification("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to pivot authority.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 p-4">
      <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-100 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-slate-400">Pivot authority</p>
            <h3 className="text-xl font-semibold">{currentAuthorityLabel}</h3>
            {currentAuthorityDescription && (
              <p className="mt-1 text-sm text-slate-400">{currentAuthorityDescription}</p>
            )}
          </div>
          <button
            type="button"
            className="text-slate-400 transition hover:text-slate-200"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div className="space-y-2">
            <label htmlFor="pivot-target" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              Target authority lane
            </label>
            <select
              id="pivot-target"
              value={targetAuthority}
              onChange={(event) => setTargetAuthority(event.target.value as AuthorityId)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm focus:border-cyan-400 focus:outline-none"
            >
              {allowedPivots.map((rule) => (
                <option key={rule.to} value={rule.to}>
                  {formatAuthorityLabel(rule.to)}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">Justification</label>
            <textarea
              rows={4}
              value={justification}
              onChange={(event) => setJustification(event.target.value)}
              placeholder="Explain why this mission must pivot lanes, referencing policy triggers."
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:border-cyan-400 focus:outline-none"
              minLength={10}
              required
            />
            <p className="text-xs text-slate-500">
              Policy reminder: pivots must cite concrete triggers, commander guidance, and risk mitigations.
              Document the oversight chain and any legal approvals in this justification block.
            </p>
          </div>

          {selectedRule?.conditions?.length ? (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-xs text-amber-100">
              <p className="font-semibold text-amber-200">Conditions for {targetLabel}</p>
              <ul className="mt-2 list-inside list-disc space-y-1">
                {selectedRule.conditions.map((condition, idx) => (
                  <li key={`${selectedRule.to}-condition-${idx}`}>{condition}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {error && <p className="text-sm text-rose-300">{error}</p>}

          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              className="rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={submitting}
            >
              {submitting ? "Submitting…" : `Pivot to ${targetLabel}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
