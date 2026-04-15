export function AboutSettings() {
  return (
    <div>
      <div className="mb-6">
        <h2 className="text-xl font-semibold text-white">About</h2>
        <p className="text-sm text-gray-400 mt-1">System information</p>
      </div>
      <div className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
        <Field label="Version" value="0.2.0-alpha" />
        <Field label="Stack" value="FastAPI + React + LangGraph + Supabase + pgvector" />
        <Field label="VLM" value="Qwen-VL via DashScope" />
        <Field label="RAG" value="pymupdf4llm + text-embedding-v4 + pgvector + hybrid search" />
        <Field label="Templates" value="15 Indonesian document templates + custom" />
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 mb-1.5">{label}</label>
      <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg px-3 py-2.5 text-sm text-gray-300">
        {value || "\u2014"}
      </div>
    </div>
  );
}
