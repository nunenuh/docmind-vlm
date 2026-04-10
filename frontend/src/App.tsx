import { useEffect } from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { queryClient } from "@/lib/query-client";
import { refreshSession } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";
import { AuthGuard } from "@/components/workspace/AuthGuard";
import { AppShell } from "@/components/layout/AppShell";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { CommandPalette } from "@/components/ui/CommandPalette";
import { LandingPage } from "@/pages/LandingPage";
import { LoginPage } from "@/pages/LoginPage";
import { Dashboard } from "@/pages/Dashboard";
import { Workspace } from "@/pages/Workspace";
import { ProjectDashboard } from "@/pages/ProjectDashboard";
import { ProjectWorkspace } from "@/pages/ProjectWorkspace";
import { Settings } from "@/pages/Settings";
import { TemplatesPage } from "@/pages/TemplatesPage";
import { PersonasPage } from "@/pages/PersonasPage";
import { AnalyticsPage } from "@/pages/AnalyticsPage";
import { ApiKeysSettings } from "@/pages/ApiKeysSettings";
import { ApiReference } from "@/pages/ApiReference";
import { ProfileSettings } from "@/pages/ProfileSettings";
import { PreferencesSettings } from "@/pages/PreferencesSettings";
import { AboutSettings } from "@/pages/AboutSettings";

function AuthProvider({ children }: { children: React.ReactNode }) {
  const { setAuth, clearAuth, setIsLoading } = useAuthStore();

  useEffect(() => {
    const storedRefreshToken = localStorage.getItem("docmind_refresh_token");
    if (storedRefreshToken) {
      refreshSession(storedRefreshToken)
        .then((session) => setAuth(session))
        .catch(() => clearAuth())
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }
  }, [setAuth, clearAuth, setIsLoading]);

  return <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ErrorBoundary>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route element={<AuthGuard />}>
                <Route element={<AppShell />}>
                  <Route path="/dashboard" element={<AnalyticsPage />} />
                  <Route path="/documents" element={<Dashboard />} />
                  <Route path="/templates" element={<TemplatesPage />} />
                  <Route path="/personas" element={<PersonasPage />} />
                  <Route path="/projects" element={<ProjectDashboard />} />
                  <Route path="/projects/:projectId" element={<ProjectWorkspace />} />
                  <Route path="/workspace/:documentId" element={<Workspace />} />
                  <Route path="/settings" element={<Settings />}>
                    <Route path="api-keys" element={<ApiKeysSettings />} />
                    <Route path="api-reference" element={<ApiReference />} />
                    <Route path="profile" element={<ProfileSettings />} />
                    <Route path="preferences" element={<PreferencesSettings />} />
                    <Route path="about" element={<AboutSettings />} />
                  </Route>
                </Route>
              </Route>
            </Routes>
            <CommandPalette />
          </BrowserRouter>
          <Toaster
            theme="dark"
            position="bottom-right"
            toastOptions={{
              style: {
                background: "#12121a",
                border: "1px solid #1e1e2e",
                color: "#e5e5e5",
              },
            }}
          />
        </ErrorBoundary>
      </AuthProvider>
    </QueryClientProvider>
  );
}
