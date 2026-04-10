import { ENDPOINT_DEFINITIONS, ENDPOINT_MODULES } from "@/data/endpoints";

const METHOD_STYLES: Record<string, string> = {
  GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  POST: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  PATCH: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  DELETE: "bg-red-500/10 text-red-400 border-red-500/20",
};

function MethodBadge({ method }: { method: string }) {
  const style = METHOD_STYLES[method] ?? "bg-gray-500/10 text-gray-400 border-gray-500/20";
  return (
    <span
      className={`inline-block px-2 py-0.5 text-xs font-mono font-medium rounded border ${style}`}
    >
      {method}
    </span>
  );
}

export function EndpointTable() {
  return (
    <div className="space-y-6">
      {ENDPOINT_MODULES.map((mod) => {
        const endpoints = ENDPOINT_DEFINITIONS.filter((e) => e.module === mod);
        if (endpoints.length === 0) return null;
        return (
          <div key={mod}>
            <h3 className="text-sm font-semibold text-white mb-3">{mod}</h3>
            <div className="overflow-x-auto bg-[#0a0a0f] border border-[#1e1e2e] rounded-lg">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[#1e1e2e]">
                    <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                      Method
                    </th>
                    <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Path
                    </th>
                    <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider w-40">
                      Scope
                    </th>
                    <th className="text-left py-2.5 px-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {endpoints.map((ep, idx) => (
                    <tr
                      key={`${ep.method}-${ep.path}`}
                      className={
                        idx < endpoints.length - 1
                          ? "border-b border-[#1e1e2e]/50"
                          : ""
                      }
                    >
                      <td className="py-2 px-4">
                        <MethodBadge method={ep.method} />
                      </td>
                      <td className="py-2 px-4">
                        <code className="text-xs font-mono text-gray-300">
                          {ep.path}
                        </code>
                      </td>
                      <td className="py-2 px-4">
                        <span className="text-xs text-indigo-400">{ep.scope}</span>
                      </td>
                      <td className="py-2 px-4 text-gray-400 text-xs">
                        {ep.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        );
      })}
    </div>
  );
}
