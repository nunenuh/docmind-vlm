import { useState } from "react";
import { FileText } from "lucide-react";
import { Navigate } from "react-router-dom";
import { login, signup } from "@/lib/auth";
import { useAuthStore } from "@/stores/auth-store";

export function LoginPage() {
  const { accessToken, isLoading, setAuth } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (!isLoading && accessToken) {
    return <Navigate to="/dashboard" replace />;
  }

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);

    try {
      if (isSignUp) {
        const session = await signup(email, password);
        setAuth(session);
        setMessage("Account created!");
      } else {
        const session = await login(email, password);
        setAuth(session);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <FileText className="w-8 h-8 text-blue-400" />
            <span className="text-2xl font-bold text-white">DocMind-VLM</span>
          </div>
          <p className="text-gray-400">
            {isSignUp ? "Create an account" : "Sign in to get started"}
          </p>
        </div>

        <form onSubmit={handleEmailAuth} className="space-y-3 mb-4">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg py-3 px-4 focus:outline-none focus:border-blue-500 placeholder-gray-500"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg py-3 px-4 focus:outline-none focus:border-blue-500 placeholder-gray-500"
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          {message && <p className="text-green-400 text-sm">{message}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 disabled:cursor-not-allowed text-white font-medium py-3 px-4 rounded-lg transition-colors"
          >
            {submitting ? "..." : isSignUp ? "Create Account" : "Sign In"}
          </button>
        </form>

        <button
          onClick={() => { setIsSignUp(!isSignUp); setError(""); setMessage(""); }}
          className="w-full text-sm text-gray-400 hover:text-white transition-colors mb-6"
        >
          {isSignUp ? "Already have an account? Sign in" : "Don't have an account? Create one"}
        </button>

        <p className="text-center text-sm text-gray-600 mt-6">
          By signing in, you agree to our terms of service.
        </p>
      </div>
    </div>
  );
}
