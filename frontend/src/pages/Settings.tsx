import { NavLink, Outlet, Navigate, useLocation } from "react-router-dom";
import { Key, Book, ArrowLeft, User, Palette, Info } from "lucide-react";

const SIDEBAR_ITEMS = [
  { to: "/settings/api-keys", label: "API Keys", icon: Key },
  { to: "/settings/api-reference", label: "API Reference", icon: Book },
  { to: "/settings/profile", label: "Profile", icon: User },
  { to: "/settings/preferences", label: "Preferences", icon: Palette },
  { to: "/settings/about", label: "About", icon: Info },
];

export function Settings() {
  const location = useLocation();

  // Redirect bare /settings to /settings/api-keys
  if (location.pathname === "/settings") {
    return <Navigate to="/settings/api-keys" replace />;
  }

  return (
    <div className="max-w-6xl mx-auto px-6 py-8">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <NavLink
          to="/dashboard"
          className="p-1.5 text-gray-500 hover:text-gray-300 rounded-lg hover:bg-white/5 transition-colors"
          title="Back to Dashboard"
        >
          <ArrowLeft className="w-5 h-5" />
        </NavLink>
        <div>
          <h1 className="text-xl font-bold text-white">Settings</h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Manage your account, API keys, and preferences
          </p>
        </div>
      </div>

      {/* Layout: sidebar + content */}
      <div className="flex gap-6">
        {/* Sidebar nav */}
        <nav className="w-52 flex-shrink-0">
          <div className="space-y-1">
            {SIDEBAR_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 text-sm font-medium rounded-lg transition-colors ${
                    isActive
                      ? "bg-indigo-600/10 text-indigo-400"
                      : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
                  }`
                }
              >
                <item.icon className="w-4 h-4" />
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
