"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";

import { deleteMission } from "@/lib/api";

interface MissionActionsProps {
  missionId: number;
  missionName: string;
}

export function MissionActions({ missionId, missionName }: MissionActionsProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleDelete = async () => {
    const confirmed = window.confirm(
      `Delete mission "${missionName}"? This will remove all related documents and analysis.`,
    );
    if (!confirmed) return;

    await deleteMission(missionId);
    startTransition(() => {
      router.refresh();
    });
  };

  return (
    <button
      type="button"
      onClick={handleDelete}
      disabled={isPending}
      className="text-xs font-medium text-rose-400 transition hover:text-rose-200 disabled:opacity-50"
    >
      {isPending ? "Deleting…" : "Delete"}
    </button>
  );
}
