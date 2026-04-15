import { useEffect, useState } from "react";

const METHOD_STYLES: Record<string, string> = {
  GET: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  POST: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  PUT: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  PATCH: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  DELETE: "bg-red-500/10 text-red-400 border-red-500/20",
};

interface OpenAPIEndpoint {
  method: string;
  path: string;
  summary: string;
  tags: string[];
}

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

function parseOpenAPI(schema: Record<string, unknown>): {
  modules: string[];
  endpoints: OpenAPIEndpoint[];
} {
  const paths = (schema.paths ?? {}) as Record<string, Record<string, unknown>>;
  const endpoints: OpenAPIEndpoint[] = [];

  for (const [path, methods] of Object.entries(paths)) {
    for (const [method, detail] of Object.entries(methods)) {
      if (["get", "post", "put", "patch", "delete"].includes(method)) {
        const d = detail as Record<string, unknown>;
        endpoints.push({
          method: method.toUpperCase(),
          path,
          summary: (d.summary as string) ?? "",
          tags: (d.tags as string[]) ?? ["Other"],
        });
      }
    }
  }

  const moduleSet = new Set<string>();
  for (const ep of endpoints) {
    for (const tag of ep.tags) {
      moduleSet.add(tag);
    }
  }

  return { modules: Array.from(moduleSet), endpoints };
}

export function EndpointTable() {
  const [data, setData] = useState<{ modules: string[]; endpoints: OpenAPIEndpoint[] } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_URL || "http://localhost:8009";
    fetch(`${apiBase}/openapi.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((schema) => {
        setData(parseOpenAPI(schema));
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500 text-sm">
        Loading endpoints from API...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="text-center py-8">
        <p className="text-red-400 text-sm">Failed to load API schema: {error}</p>
        <p className="text-gray-500 text-xs mt-1">Make sure the backend is running</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {data.modules.map((mod) => {
        const endpoints = data.endpoints.filter((e) => e.tags.includes(mod));
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
                      <td className="py-2 px-4 text-gray-400 text-xs">
                        {ep.summary}
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
