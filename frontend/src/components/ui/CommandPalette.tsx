import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import { FileText, FolderOpen, Settings, Search, MessageSquare, Plus, Home } from "lucide-react";
import { useDocuments } from "@/hooks/useDocuments";
import { useProjects } from "@/hooks/useProjects";

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { data: docsData } = useDocuments(1, 10);
  const { data: projData } = useProjects(1, 10);

  const documents = docsData?.items ?? [];
  const projects = projData?.items ?? [];

  // Toggle with Cmd+K or Ctrl+K
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const runCommand = useCallback(
    (command: () => void) => {
      setOpen(false);
      command();
    },
    [],
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100]">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={() => setOpen(false)}
      />

      {/* Dialog */}
      <div className="absolute top-[20%] left-1/2 -translate-x-1/2 w-full max-w-lg">
        <Command
          className="bg-[#12121a] border border-[#2a2a3a] rounded-2xl shadow-2xl overflow-hidden"
          label="Search commands"
        >
          <div className="flex items-center gap-3 px-4 border-b border-[#1e1e2e]">
            <Search className="w-4 h-4 text-gray-500 flex-shrink-0" />
            <Command.Input
              placeholder="Search documents, projects, or type a command..."
              className="w-full bg-transparent py-4 text-sm text-white placeholder-gray-500 outline-none"
              autoFocus
            />
            <kbd className="text-xs text-gray-600 bg-white/5 px-1.5 py-0.5 rounded border border-[#2a2a3a] font-mono">
              ESC
            </kbd>
          </div>

          <Command.List className="max-h-80 overflow-y-auto p-2">
            <Command.Empty className="py-8 text-center text-sm text-gray-500">
              No results found.
            </Command.Empty>

            {/* Navigation */}
            <Command.Group heading="Navigation" className="mb-2">
              <PaletteItem
                icon={<Home className="w-4 h-4" />}
                label="Dashboard"
                onSelect={() => runCommand(() => navigate("/dashboard"))}
              />
              <PaletteItem
                icon={<FolderOpen className="w-4 h-4" />}
                label="Projects"
                onSelect={() => runCommand(() => navigate("/projects"))}
              />
              <PaletteItem
                icon={<Settings className="w-4 h-4" />}
                label="Settings"
                onSelect={() => runCommand(() => navigate("/settings"))}
              />
            </Command.Group>

            {/* Actions */}
            <Command.Group heading="Actions" className="mb-2">
              <PaletteItem
                icon={<Plus className="w-4 h-4" />}
                label="New Project"
                shortcut="N"
                onSelect={() => runCommand(() => navigate("/projects"))}
              />
            </Command.Group>

            {/* Recent Documents */}
            {documents.length > 0 && (
              <Command.Group heading="Documents" className="mb-2">
                {documents.slice(0, 5).map((doc) => (
                  <PaletteItem
                    key={doc.id}
                    icon={<FileText className="w-4 h-4" />}
                    label={doc.filename}
                    subtitle={`${doc.file_type.toUpperCase()} · ${doc.status}`}
                    onSelect={() => runCommand(() => navigate(`/workspace/${doc.id}`))}
                  />
                ))}
              </Command.Group>
            )}

            {/* Recent Projects */}
            {projects.length > 0 && (
              <Command.Group heading="Projects" className="mb-2">
                {projects.slice(0, 5).map((proj) => (
                  <PaletteItem
                    key={proj.id}
                    icon={<FolderOpen className="w-4 h-4" />}
                    label={proj.name}
                    subtitle={proj.description || "No description"}
                    onSelect={() => runCommand(() => navigate(`/projects/${proj.id}`))}
                  />
                ))}
              </Command.Group>
            )}
          </Command.List>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-[#1e1e2e] text-xs text-gray-600">
            <span>Type to search</span>
            <div className="flex items-center gap-2">
              <span className="flex items-center gap-1">
                <kbd className="bg-white/5 px-1 rounded border border-[#2a2a3a]">↑↓</kbd>
                navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="bg-white/5 px-1 rounded border border-[#2a2a3a]">↵</kbd>
                open
              </span>
            </div>
          </div>
        </Command>
      </div>
    </div>
  );
}

function PaletteItem({
  icon,
  label,
  subtitle,
  shortcut,
  onSelect,
}: {
  icon: React.ReactNode;
  label: string;
  subtitle?: string;
  shortcut?: string;
  onSelect: () => void;
}) {
  return (
    <Command.Item
      onSelect={onSelect}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-gray-300 cursor-pointer data-[selected=true]:bg-white/5 data-[selected=true]:text-white transition-colors"
    >
      <span className="text-gray-500 flex-shrink-0">{icon}</span>
      <div className="flex-1 min-w-0">
        <span className="truncate block">{label}</span>
        {subtitle && (
          <span className="text-xs text-gray-600 truncate block">{subtitle}</span>
        )}
      </div>
      {shortcut && (
        <kbd className="text-xs text-gray-600 bg-white/5 px-1.5 py-0.5 rounded border border-[#2a2a3a] font-mono ml-auto">
          {shortcut}
        </kbd>
      )}
    </Command.Item>
  );
}
