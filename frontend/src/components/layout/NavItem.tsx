import { Link, useLocation } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

interface NavItemProps {
  icon: LucideIcon;
  label: string;
  to: string;
  collapsed?: boolean;
}

export function NavItem({ icon: Icon, label, to, collapsed = false }: NavItemProps) {
  const location = useLocation();
  const isActive = location.pathname === to || location.pathname.startsWith(to + "/");

  return (
    <Link
      to={to}
      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors relative ${
        isActive
          ? "bg-white/5 text-white"
          : "text-gray-400 hover:text-white hover:bg-white/5"
      }`}
      title={collapsed ? label : undefined}
    >
      {isActive && (
        <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-indigo-500 rounded-r" />
      )}
      <Icon className="w-4 h-4 flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </Link>
  );
}
