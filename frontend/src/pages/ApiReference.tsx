import { Shield, Key } from "lucide-react";
import { EndpointTable } from "@/components/settings/EndpointTable";
import { CodeExamples } from "@/components/settings/CodeExamples";

export function ApiReference() {
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-white">API Reference</h2>
        <p className="text-sm text-gray-400 mt-1">
          Learn how to authenticate and use the DocMind API
        </p>
      </div>

      {/* Authentication section */}
      <section className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6 space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-5 h-5 text-indigo-400" />
          <h3 className="text-lg font-semibold text-white">Authentication</h3>
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">
          The DocMind API supports two authentication methods:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Key className="w-4 h-4 text-indigo-400" />
              <h4 className="text-sm font-medium text-white">API Key (recommended)</h4>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Best for server-to-server integrations, CI/CD pipelines, and scripts.
              Each key has scoped permissions.
            </p>
            <pre className="bg-[#12121a] border border-[#1e1e2e] rounded px-3 py-2 text-xs text-gray-300 font-mono">
              Authorization: Bearer dm_live_xxxx
            </pre>
          </div>

          <div className="bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-4 h-4 text-emerald-400" />
              <h4 className="text-sm font-medium text-white">JWT Session Token</h4>
            </div>
            <p className="text-xs text-gray-400 mb-3">
              Used by the web app. Obtained via the login endpoint.
              Has full access for the authenticated user.
            </p>
            <pre className="bg-[#12121a] border border-[#1e1e2e] rounded px-3 py-2 text-xs text-gray-300 font-mono">
              Authorization: Bearer eyJhbGci...
            </pre>
          </div>
        </div>

        <div className="bg-indigo-500/5 border border-indigo-500/10 rounded-lg px-4 py-3">
          <p className="text-xs text-gray-400">
            <span className="text-indigo-400 font-medium">Scoped access: </span>
            API keys are restricted to the scopes you assign when creating them.
            A key with <code className="text-indigo-300">documents:read</code> scope
            can only read documents -- it cannot create or delete them.
          </p>
        </div>
      </section>

      {/* Endpoints section */}
      <section className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Endpoints</h3>
        <EndpointTable />
      </section>

      {/* Code Examples section */}
      <section className="bg-[#12121a] border border-[#1e1e2e] rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Code Examples</h3>
        <CodeExamples />
      </section>
    </div>
  );
}
