"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState, useTransition } from "react";
import type { ForceGraphMethods } from "react-force-graph-2d";
import { usePathname } from "next/navigation";
import useSWR from "swr";

import {
  fetchMissionKgGraph,
  fetchMissionKgSummary,
  fetchMissionKgNeighborhood,
  fetchMissionKgLinkSuggestions,
  type KgGraphPayload,
  type KgLinkSuggestion,
  type KgNeighborhoodPayload,
  type MissionKgSummary,
} from "@/lib/api";

const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d"),
  {
    ssr: false,
    loading: () => <p className="text-sm text-slate-400">Loading visualization…</p>,
  },
);

type InternalGraphNode = {
  id: string;
  label: string;
  raw: Record<string, unknown>;
  val: number;
  color: string;
  legendKey: string;
};

type InternalGraphLink = {
  id: string;
  source: string;
  target: string;
  label: string;
  raw: Record<string, unknown>;
};

interface EntitiesEventsViewProps {
  missionId: number;
}

type GraphMode = "overview" | "entities" | "comms";

const legendPalette = [
  {
    key: "entities",
    label: "People & Entities",
    color: "#22d3ee",
    matcher: /(person|people|agent|entity|org|team|unit)/i,
  },
  {
    key: "comms",
    label: "Comms & Signals",
    color: "#fbbf24",
    matcher: /(comms|call|message|signal|radio|link)/i,
  },
  {
    key: "infrastructure",
    label: "Assets & Infrastructure",
    color: "#a78bfa",
    matcher: /(facility|site|location|asset|device|infrastructure)/i,
  },
];

const defaultLegend = {
  key: "context",
  label: "Context Nodes",
  color: "#94a3b8",
};

export default function EntitiesEventsView({ missionId }: EntitiesEventsViewProps) {
  const [isPending, startTransition] = useTransition();
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [graphMode, setGraphMode] = useState<GraphMode>("overview");
  const [graphLimits, setGraphLimits] = useState({ limitNodes: 200, limitEdges: 400 });
  const [neighborhoodHops, setNeighborhoodHops] = useState(2);
  const [graphViewport, setGraphViewport] = useState({ width: 0, height: 0 });
  const fgRef = useRef<ForceGraphMethods | null>(null);
  const graphContainerRef = useRef<HTMLDivElement | null>(null);
  const pathname = usePathname();

  const {
    data: summary,
    error: summaryError,
    isLoading: summaryLoading,
    mutate: refreshSummary,
  } = useSWR<MissionKgSummary>(["mission-kg-summary", missionId], () => fetchMissionKgSummary(missionId), {
    revalidateOnFocus: false,
  });

  const {
    data: graph,
    error: graphError,
    isLoading: graphLoading,
    mutate: refreshGraph,
  } = useSWR<KgGraphPayload>(["mission-kg-graph", missionId, graphLimits.limitNodes, graphLimits.limitEdges], () => fetchMissionKgGraph(missionId, {
    limitNodes: graphLimits.limitNodes,
    limitEdges: graphLimits.limitEdges,
  }), {
    revalidateOnFocus: false,
  });

  const {
    data: suggestionsData,
    error: suggestionsError,
    isLoading: suggestionsLoading,
  } = useSWR(["mission-kg-suggestions", missionId], () => fetchMissionKgLinkSuggestions(missionId, { limit: 20 }), {
    revalidateOnFocus: false,
  });

  const {
    data: neighborhood,
    error: neighborhoodError,
    isLoading: neighborhoodLoading,
  } = useSWR<KgNeighborhoodPayload>(
    selectedNodeId ? ["mission-kg-neighborhood", missionId, selectedNodeId, neighborhoodHops] : null,
    () => fetchMissionKgNeighborhood(missionId, selectedNodeId!, { hops: neighborhoodHops }),
    { revalidateOnFocus: false },
  );

  const handleRefresh = useCallback(() => {
    startTransition(() => {
      void Promise.all([refreshSummary(), refreshGraph()]);
    });
  }, [refreshGraph, refreshSummary]);

  const graphData = useMemo(() => {
    const rawNodes = (graph?.nodes ?? []) as Array<Record<string, any>>;
    const rawEdges = (graph?.edges ?? []) as Array<Record<string, any>>;

    const nodes: InternalGraphNode[] = rawNodes.map((node, index) => {
      const id = String(node.node_id ?? node.id ?? node.node_key ?? index);
      const valCandidate = Number(node.weight ?? node.count ?? 1);
      const label = String(node.label ?? node.type ?? "Node");
      const paletteEntry = legendPalette.find((entry) => entry.matcher.test(label)) ?? defaultLegend;
      return {
        id,
        label,
        raw: node,
        val: Number.isFinite(valCandidate) ? valCandidate : 1,
        color: paletteEntry.color,
        legendKey: paletteEntry.key,
      };
    });

    const links: InternalGraphLink[] = rawEdges
      .map((edge, index) => {
        const source = edge.src ?? edge.source ?? edge.from ?? edge.node_a;
        const target = edge.dst ?? edge.target ?? edge.to ?? edge.node_b;
        if (!source || !target) {
          return null;
        }
        return {
          id: String(edge.edge_id ?? `${source}-${target}-${index}`),
          source: String(source),
          target: String(target),
          label: String(edge.label ?? edge.relation ?? edge.reason ?? "Link"),
          raw: edge,
        };
      })
      .filter((link): link is InternalGraphLink => Boolean(link));

    return { nodes, links };
  }, [graph]);

  const filteredGraphData = useMemo(() => {
    if (graphMode === "overview") {
      return graphData;
    }

    const modePredicate = (node: InternalGraphNode) => {
      if (graphMode === "entities") {
        return /person|facility|org|entity/i.test(node.label);
      }
      if (graphMode === "comms") {
        return /comms|call|message|signal|link/i.test(node.label);
      }
      return true;
    };

    const nodes = graphData.nodes.filter(modePredicate);
    const nodeIds = new Set(nodes.map((node) => node.id));
    const links = graphData.links.filter(
      (link) => nodeIds.has(String(link.source)) && nodeIds.has(String(link.target)),
    );

    return { nodes, links };
  }, [graphData, graphMode]);

  useEffect(() => {
    if (!graphContainerRef.current) {
      return undefined;
    }
    const updateSize = () => {
      const rect = graphContainerRef.current?.getBoundingClientRect();
      if (rect) {
        setGraphViewport({ width: rect.width, height: rect.height });
      }
    };
    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(graphContainerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (fgRef.current && filteredGraphData.nodes.length > 0) {
      fgRef.current.zoomToFit?.(400, 40);
    }
  }, [filteredGraphData]);

  useEffect(() => {
    if (filteredGraphData.nodes.length === 0) {
      if (selectedNodeId !== null) {
        setSelectedNodeId(null);
      }
      return;
    }

    const selectedStillExists = filteredGraphData.nodes.some((node) => node.id === selectedNodeId);
    if (!selectedNodeId || !selectedStillExists) {
      setSelectedNodeId(filteredGraphData.nodes[0].id);
    }
  }, [filteredGraphData, selectedNodeId]);

  const selectedNode = useMemo(
    () => graphData.nodes.find((node) => node.id === selectedNodeId) ?? null,
    [graphData, selectedNodeId],
  );

  const neighborNodes = useMemo(() => {
    const nodes = (neighborhood?.nodes ?? []) as Array<Record<string, any>>;
    return nodes.slice(0, 6).map((node, index) => ({
      id: String(node.node_id ?? node.id ?? node.node_key ?? index),
      label: String(node.label ?? node.type ?? "Node"),
    }));
  }, [neighborhood]);

  const suggestionList = useMemo(() => (
    (suggestionsData?.suggestions ?? []) as KgLinkSuggestion[]
  ).slice(0, 8), [suggestionsData]);

  const summaryState = {
    loading: summaryLoading,
    error: summaryError,
  };
  const graphState = {
    loading: graphLoading,
    error: graphError,
  };

  const legendEntries = [...legendPalette, defaultLegend];

  const nodeRenderer = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const size = Math.max(4, Math.log((node?.val ?? 1) + 1) * 3);
    const label = String(node.label ?? "Node");
    const fontSize = Math.max(10, (size + 4) / globalScale * 6);
    const color = node.color ?? "#22d3ee";

    ctx.save();
    ctx.shadowBlur = 12;
    ctx.shadowColor = color;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI, false);
    ctx.fill();
    ctx.shadowBlur = 0;

    ctx.font = `${fontSize}px 'Inter', sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const textWidth = ctx.measureText(label).width + 12;
    const textHeight = fontSize + 6;
    const textY = (node.y ?? 0) - size - textHeight / 2 - 4;
    const textX = node.x ?? 0;

    ctx.fillStyle = "rgba(2, 6, 23, 0.85)";
    ctx.fillRect(textX - textWidth / 2, textY - textHeight / 2, textWidth, textHeight);
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.strokeRect(textX - textWidth / 2, textY - textHeight / 2, textWidth, textHeight);

    ctx.fillStyle = "#e2e8f0";
    ctx.fillText(label, textX, textY);
    ctx.restore();
  }, []);

  const downloadGraphSnapshot = useCallback(() => {
    const payload = {
      fetched_at: new Date().toISOString(),
      mission_id: missionId,
      mode: graphMode,
      graph: filteredGraphData,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `mission-${missionId}-kg-${graphMode}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [filteredGraphData, graphMode, missionId]);

  const shareGraphLink = useCallback(async () => {
    const shareUrl = `${window.location.origin}${pathname}?mission=${missionId}&mode=${graphMode}`;
    try {
      await navigator.clipboard?.writeText(shareUrl);
      alert("Share link copied to clipboard");
    } catch (error) {
      console.warn("Failed to copy share link", error);
      alert("Unable to copy share link");
    }
  }, [graphMode, missionId, pathname]);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-lg font-semibold">Knowledge Graph</p>
          <p className="text-sm text-slate-400">
            Live mission namespace data served from AggreGator. Refresh to pull the latest extraction bundles.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="inline-flex rounded-full border border-slate-700 bg-slate-900/60 p-1 text-xs">
            {[{ key: "overview", label: "Overview" }, { key: "entities", label: "Entities" }, { key: "comms", label: "Comms" }].map((mode) => {
              const active = graphMode === mode.key;
              return (
                <button
                  key={mode.key}
                  type="button"
                  onClick={() => setGraphMode(mode.key as GraphMode)}
                  className={`rounded-full px-3 py-1 font-semibold transition ${
                    active
                      ? "bg-emerald-400/20 text-emerald-200 shadow-[0_0_12px_rgba(34,211,238,0.35)]"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {mode.label}
                </button>
              );
            })}
          </div>
          <button
            type="button"
            disabled={isPending}
            onClick={handleRefresh}
            className="rounded border border-emerald-500/70 px-4 py-1.5 text-xs font-semibold text-emerald-100 transition hover:bg-emerald-500/10 disabled:opacity-60"
          >
            {isPending ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </header>

      {(summaryState.error || graphState.error) && (
        <div className="rounded border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">
          Failed to load KG data. Ensure AggreGator is reachable and retry.
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        <section className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold">Summary</h3>
            <p className="text-sm text-slate-500">Node/edge totals plus the most prevalent labels.</p>
          </div>
          {summaryState.loading && !summary ? (
            <p className="text-sm text-slate-400">Loading mission graph summary…</p>
          ) : summary ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Nodes</p>
                  <p className="text-2xl font-semibold text-emerald-300">{summary.nodes.toLocaleString()}</p>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">Edges</p>
                  <p className="text-2xl font-semibold text-cyan-300">{summary.edges.toLocaleString()}</p>
                </div>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Top labels</p>
                {summary.top_labels.length === 0 ? (
                  <p className="text-sm text-slate-400">No labeled nodes reported yet.</p>
                ) : (
                  <ul className="mt-2 divide-y divide-slate-800 rounded-lg border border-slate-800 bg-slate-900/50">
                    {summary.top_labels.map((entry) => (
                      <li key={entry.label} className="flex items-center justify-between px-3 py-2 text-sm">
                        <span className="font-medium text-slate-100">{entry.label}</span>
                        <span className="text-slate-400">{entry.count}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">No summary available yet.</p>
          )}
        </section>

        <section className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold">Node details</h3>
            <p className="text-sm text-slate-500">Click a node to inspect metadata and nearby actors.</p>
          </div>
          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <p className="text-lg font-semibold text-cyan-200">{selectedNode.label}</p>
                <p className="text-xs text-slate-500">{String((selectedNode.raw as any)?.node_key ?? selectedNode.id)}</p>
              </div>
              {renderProps((selectedNode.raw as any)?.props_json ?? selectedNode.raw)}
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Neighborhood</p>
                {neighborhoodLoading ? (
                  <p className="text-sm text-slate-400">Loading neighborhood…</p>
                ) : neighborhoodError ? (
                  <p className="text-sm text-rose-300">Failed to load neighborhood.</p>
                ) : neighborNodes.length === 0 ? (
                  <p className="text-sm text-slate-400">No nearby nodes reported.</p>
                ) : (
                  <ul className="mt-2 space-y-1 text-sm">
                    {neighborNodes.map((neighbor) => (
                      <li key={neighbor.id} className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/40 px-2 py-1">
                        <span className="text-slate-100">{neighbor.label}</span>
                        <button
                          type="button"
                          className="text-xs text-emerald-300 hover:text-emerald-200"
                          onClick={() => setSelectedNodeId(neighbor.id)}
                        >
                          Inspect
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-400">No node selected yet.</p>
          )}
        </section>

        <section className="card space-y-4">
          <div>
            <h3 className="text-base font-semibold">Link suggestions</h3>
            <p className="text-sm text-slate-500">Auto-detected duplicates and potential merges from AggreGator.</p>
          </div>
          {suggestionsLoading && !suggestionList.length ? (
            <p className="text-sm text-slate-400">Fetching suggestions…</p>
          ) : suggestionsError ? (
            <p className="text-sm text-rose-300">Failed to load link suggestions.</p>
          ) : suggestionList.length === 0 ? (
            <p className="text-sm text-slate-400">AggreGator has no link suggestions right now.</p>
          ) : (
            <ul className="space-y-2 text-sm">
              {suggestionList.map((suggestion, index) => (
                <li key={`${suggestion.src}-${suggestion.dst}-${index}`} className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                  <p className="font-semibold text-slate-100">
                    {String(suggestion.src ?? "?")} ↔ {String(suggestion.dst ?? "?")}
                  </p>
                  {suggestion.reason && (
                    <p className="text-xs text-slate-400">{suggestion.reason}</p>
                  )}
                  {typeof suggestion.confidence === "number" && (
                    <p className="text-xs text-emerald-300">Confidence: {(suggestion.confidence * 100).toFixed(1)}%</p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section className="card space-y-4">
        <div>
          <h3 className="text-base font-semibold">Interactive visualization</h3>
          <p className="text-sm text-slate-500">Force-directed layout sampled from the mission namespace.</p>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-800/60 bg-slate-950/60 px-4 py-3 text-xs text-slate-300">
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex flex-col gap-1">
              <span className="uppercase tracking-wide text-[10px] text-slate-500">Node sample</span>
              <input
                type="range"
                min={50}
                max={600}
                step={50}
                value={graphLimits.limitNodes}
                onChange={(event) =>
                  setGraphLimits((prev) => ({ ...prev, limitNodes: Number(event.target.value) }))
                }
                className="accent-emerald-400"
              />
              <span className="text-[11px] text-slate-400">{graphLimits.limitNodes} nodes</span>
            </label>
            <label className="flex flex-col gap-1">
              <span className="uppercase tracking-wide text-[10px] text-slate-500">Edge sample</span>
              <input
                type="range"
                min={100}
                max={800}
                step={50}
                value={graphLimits.limitEdges}
                onChange={(event) =>
                  setGraphLimits((prev) => ({ ...prev, limitEdges: Number(event.target.value) }))
                }
                className="accent-cyan-400"
              />
              <span className="text-[11px] text-slate-400">{graphLimits.limitEdges} edges</span>
            </label>
          </div>
          <div className="flex flex-col gap-2">
            <span className="uppercase tracking-wide text-[10px] text-slate-500">Neighborhood hops</span>
            <div className="inline-flex rounded-full border border-slate-700 bg-slate-900/60 p-1">
              {[1, 2, 3].map((hop) => (
                <button
                  key={hop}
                  type="button"
                  onClick={() => setNeighborhoodHops(hop)}
                  className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                    hop === neighborhoodHops
                      ? "bg-cyan-400/20 text-cyan-200"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {hop} hop{hop > 1 ? "s" : ""}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {legendEntries.map((entry) => (
            <div key={entry.key} className="flex items-center gap-2 text-xs text-slate-400">
              <span
                className="h-3 w-3 rounded-full"
                style={{ backgroundColor: entry.color, boxShadow: `0 0 12px ${entry.color}` }}
              />
              <span>{entry.label}</span>
            </div>
          ))}
        </div>
        <div
          ref={graphContainerRef}
          className="relative h-[420px] w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-950/80"
        >
          {graphState.loading && filteredGraphData.nodes.length === 0 ? (
            <p className="text-sm text-slate-400">Rendering graph…</p>
          ) : filteredGraphData.nodes.length === 0 ? (
            <p className="text-sm text-slate-400">No graph snapshot available.</p>
          ) : (
            <ForceGraph2D
              ref={fgRef as any}
              graphData={filteredGraphData}
              width={graphViewport.width || undefined}
              height={graphViewport.height || undefined}
              nodeLabel={(node: any) => node.label}
              linkLabel={(link: any) => link.label}
              nodeAutoColorBy={undefined}
              cooldownTicks={80}
              backgroundColor="#020617"
              nodeRelSize={6}
              linkDirectionalArrowLength={4}
              linkDirectionalParticles={1}
              linkDirectionalParticleSpeed={0.005}
              nodeCanvasObject={nodeRenderer}
              nodeCanvasObjectMode={() => "replace"}
              linkColor={() => "rgba(148,163,184,0.35)"}
              linkWidth={() => 1}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.25}
              enableZoomInteraction
              enablePanInteraction
              onNodeClick={(node: any) => {
                if (node?.id) {
                  setSelectedNodeId(String(node.id));
                }
              }}
              enableNodeDrag={false}
            />
          )}
          <div className="pointer-events-auto absolute bottom-4 right-4 flex flex-col gap-3">
            <button
              type="button"
              onClick={downloadGraphSnapshot}
              className="rounded-full bg-emerald-500/80 px-5 py-2 text-xs font-semibold uppercase tracking-wide text-slate-900 shadow-[0_12px_30px_rgba(16,185,129,0.45)] hover:bg-emerald-400"
            >
              Export JSON
            </button>
            <button
              type="button"
              onClick={shareGraphLink}
              className="rounded-full border border-cyan-400/70 bg-slate-900/60 px-5 py-2 text-xs font-semibold uppercase tracking-wide text-cyan-200 shadow-[0_12px_25px_rgba(6,182,212,0.35)] hover:bg-slate-900/80"
            >
              Share Snapshot
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}

function renderProps(props: unknown) {
  if (!props) {
    return null;
  }

  const value = typeof props === "string" ? props : JSON.stringify(props, null, 2);
  return (
    <pre className="mt-2 max-h-40 overflow-auto rounded bg-slate-900/60 p-2 text-xs text-slate-300 whitespace-pre-wrap">
      {value}
    </pre>
  );
}
