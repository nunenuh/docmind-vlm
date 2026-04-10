import { SCOPE_DEFINITIONS, SCOPE_MODULES } from "@/data/scopes";
import type { TokenScope } from "@/types/api-token";

interface ScopeCheckboxGridProps {
  selectedScopes: string[];
  onChange: (scopes: string[]) => void;
}

export function ScopeCheckboxGrid({ selectedScopes, onChange }: ScopeCheckboxGridProps) {
  const allNonAdminScopes = SCOPE_DEFINITIONS
    .filter((s) => s.scope !== "admin:*")
    .map((s) => s.scope);

  const isAdminSelected = selectedScopes.includes("admin:*");

  const handleToggleScope = (scope: TokenScope) => {
    if (scope === "admin:*") {
      if (isAdminSelected) {
        onChange([]);
      } else {
        onChange(["admin:*", ...allNonAdminScopes]);
      }
      return;
    }
    const next = selectedScopes.includes(scope)
      ? selectedScopes.filter((s) => s !== scope && s !== "admin:*")
      : [...selectedScopes, scope];
    onChange(next);
  };

  const groupedByModule = SCOPE_MODULES.map((mod) => ({
    module: mod,
    scopes: SCOPE_DEFINITIONS.filter((s) => s.module === mod),
  }));

  return (
    <div className="space-y-4">
      {groupedByModule.map(({ module, scopes }) => (
        <div key={module}>
          <h4 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
            {module}
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {scopes.map((scopeInfo) => {
              const checked =
                selectedScopes.includes(scopeInfo.scope) || isAdminSelected;
              return (
                <label
                  key={scopeInfo.scope}
                  className="flex items-start gap-2.5 px-3 py-2 rounded-lg bg-[#0a0a0f] border border-[#1e1e2e] hover:border-gray-700 cursor-pointer transition-colors group"
                  title={scopeInfo.description}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => handleToggleScope(scopeInfo.scope)}
                    disabled={scopeInfo.scope !== "admin:*" && isAdminSelected}
                    className="mt-0.5 w-4 h-4 rounded border-gray-600 bg-gray-800 text-indigo-600 focus:ring-indigo-500 focus:ring-offset-0"
                  />
                  <div className="min-w-0">
                    <span className="text-sm text-white block">{scopeInfo.label}</span>
                    <span className="text-xs text-gray-500 block leading-tight">
                      {scopeInfo.description}
                    </span>
                  </div>
                </label>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
