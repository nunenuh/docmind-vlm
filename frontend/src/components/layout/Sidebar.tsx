import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  FolderOpen,
  LayoutTemplate,
  Bot,
  BarChart3,
  Settings,
  LogOut,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import { signOut } from "@/lib/supabase";
import { useAuthStore } from "@/stores/auth-store";
import { NavItem } from "./NavItem";

export function Sidebar() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const [collapsed, setCollapsed] = useState(false);

  const handleSignOut = async () => {
    await signOut();
    navigate("/");
  };

  const email = user?.email ?? "";
  const initial = email ? email[0].toUpperCase() : "?";

  return (
    <aside
      className={`flex flex-col bg-[#12121a] border-r border-[#1e1e2e] transition-all duration-200 flex-shrink-0 ${
        collapsed ? "w-16" : "w-64"
      }`}
    >
      {/* Logo */}
      <div className={`flex items-center gap-2 py-5 ${collapsed ? "px-4 justify-center" : "px-4"}`}>
        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center flex-shrink-0">
          <FileText className="w-4 h-4 text-white" />
        </div>
        {!collapsed && (
          <span className="font-semibold text-white text-sm">DocMind</span>
        )}
      </div>

      {/* Search */}
      {!collapsed && (
        <div className="px-3 mb-4">
          <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-500 bg-white/5 rounded-lg border border-transparent hover:border-[#2a2a3a] transition-colors">
            <Search className="w-4 h-4 flex-shrink-0" />
            <span>Search...</span>
            <kbd className="ml-auto text-xs bg-white/10 px-1.5 py-0.5 rounded font-mono">
              {"\u2318"}K
            </kbd>
          </button>
        </div>
      )}

      {collapsed && (
        <div className="px-3 mb-4 flex justify-center">
          <button className="p-2 text-gray-500 hover:text-gray-300 rounded-lg hover:bg-white/5 transition-colors">
            <Search className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-3">
        {!collapsed && (
          <div className="text-xs font-medium text-gray-500 uppercase tracking-wider px-3 mb-2">
            Main
          </div>
        )}
        <div className="space-y-1">
          <NavItem icon={BarChart3} label="Dashboard" to="/dashboard" collapsed={collapsed} />
          <NavItem icon={FolderOpen} label="Projects" to="/projects" collapsed={collapsed} />
          <NavItem icon={FileText} label="Documents" to="/documents" collapsed={collapsed} />
          <NavItem icon={LayoutTemplate} label="Templates" to="/templates" collapsed={collapsed} />
          <NavItem icon={Bot} label="Personas" to="/personas" collapsed={collapsed} />
        </div>
      </nav>

      {/* Bottom section */}
      <div className="px-3 py-4 border-t border-[#1e1e2e]">
        <div className="space-y-1">
          <NavItem icon={Settings} label="Settings" to="/settings" collapsed={collapsed} />
        </div>

        {/* Profile */}
        <div className={`mt-3 flex items-center gap-3 px-3 py-2 ${collapsed ? "justify-center" : ""}`}>
          <div className="w-8 h-8 rounded-full bg-indigo-600/20 flex items-center justify-center text-indigo-400 text-xs font-medium flex-shrink-0">
            {initial}
          </div>
          {!collapsed && (
            <>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-white truncate">{email}</div>
              </div>
              <button
                onClick={handleSignOut}
                className="text-gray-500 hover:text-gray-300 transition-colors"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          )}
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className={`mt-2 w-full flex items-center justify-center gap-2 px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 rounded-lg hover:bg-white/5 transition-colors ${
            collapsed ? "" : ""
          }`}
          title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {collapsed ? (
            <PanelLeftOpen className="w-4 h-4" />
          ) : (
            <>
              <PanelLeftClose className="w-4 h-4" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
