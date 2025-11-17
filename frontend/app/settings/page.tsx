import { ModelSelector } from "@/components/ModelSelector";
import {
  fetchActiveModelInfo,
  fetchAvailableModels,
  type AvailableModelsResponse,
} from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  let available: AvailableModelsResponse | null = null;
  let activeModel = "";
  let error: string | null = null;

  try {
    const [availableResp, activeResp] = await Promise.all([
      fetchAvailableModels(),
      fetchActiveModelInfo(),
    ]);
    available = availableResp;
    activeModel = activeResp.active_model;
  } catch (err) {
    console.error("Failed to load settings", err);
    error = "Unable to load model settings. Ensure the backend is running.";
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-cyan-100">Settings</h1>
        <p className="text-sm text-slate-400">Manage APEX runtime preferences.</p>
      </div>

      <section className="space-y-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
        <div>
          <h2 className="text-xl font-semibold">Language model</h2>
          <p className="text-sm text-slate-400">
            Select which underlying LLM model APEX should use for analysis.
          </p>
        </div>
        {error && <p className="text-sm text-rose-300">{error}</p>}
        {!error && available && available.models.length > 0 && (
          <ModelSelector models={available.models} activeModel={activeModel} />
        )}
        {!error && available && available.models.length === 0 && (
          <p className="text-sm text-slate-400">
            No models discovered. Install an Ollama model or configure one manually.
          </p>
        )}
      </section>
    </div>
  );
}
