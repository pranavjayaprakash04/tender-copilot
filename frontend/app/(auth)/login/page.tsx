"use client";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirectTo") || "/tenders";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) throw signInError;
      router.push(redirectTo);
      router.refresh();
    } catch (err: any) {
      setError(err.message || "Login failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setError(null);
    setGoogleLoading(true);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${window.location.origin}/auth/callback?redirectTo=${redirectTo}`,
        },
      });
      if (error) throw error;
    } catch (err: any) {
      setError(err.message || "Google sign-in failed.");
      setGoogleLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "#020B18", fontFamily: "'Mona Sans', 'Inter', sans-serif" }}
    >
      <div className="max-w-md w-full">

        {/* Logo + Brand */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <img src="/logo-icon.png" alt="TenderCopilot" style={{ width: 48, height: 48 }} />
            <h1 className="text-3xl font-bold" style={{ color: "#FFFFFF" }}>
              Tender<span style={{ color: "#1E5EFF" }}>Copilot</span>
            </h1>
          </div>
          <div style={{ width: 48, height: 2, background: "#00C6B3", margin: "0 auto 10px" }} />
          <p className="text-sm" style={{ color: "#7B9CC8" }}>
            AI-powered tender intelligence for Indian MSMEs
          </p>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-8 shadow-2xl"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(30,94,255,0.2)" }}
        >
          <h2 className="text-xl font-semibold mb-6" style={{ color: "#F1F5F9" }}>
            Sign in to your account
          </h2>

          {error && (
            <div
              className="mb-4 px-4 py-3 rounded-lg text-sm"
              style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", color: "#FCA5A5" }}
            >
              {error}
            </div>
          )}

          {/* Google Sign In */}
          <button
            onClick={handleGoogleLogin}
            disabled={googleLoading || loading}
            className="w-full py-3 rounded-lg text-sm font-semibold mb-5 flex items-center justify-center gap-3 transition-all"
            style={{
              background: "rgba(255,255,255,0.07)",
              border: "1px solid rgba(255,255,255,0.15)",
              color: "#F1F5F9",
              cursor: googleLoading ? "not-allowed" : "pointer",
              opacity: googleLoading ? 0.7 : 1,
            }}
          >
            {googleLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Connecting…
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                </svg>
                Continue with Google
              </>
            )}
          </button>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-5">
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
            <span style={{ color: "#475569", fontSize: 12 }}>or sign in with email</span>
            <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.08)" }} />
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>
                Email Address
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                autoComplete="email"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#F1F5F9",
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#F1F5F9",
                }}
              />
            </div>
            <button
              type="submit"
              disabled={loading || googleLoading}
              className="w-full py-3 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: loading ? "rgba(30,94,255,0.5)" : "#1E5EFF",
                color: "#FFFFFF",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                  Signing in…
                </span>
              ) : "Sign In"}
            </button>
          </form>

          <p className="text-center text-sm mt-6" style={{ color: "#64748B" }}>
            Don&apos;t have an account?{" "}
            <Link href="/register" className="font-medium" style={{ color: "#00C6B3" }}>
              Create account
            </Link>
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-xs mt-6" style={{ color: "#1E3A6E" }}>
          Pynevera Technologies Pvt Ltd · Coimbatore
        </p>
      </div>
    </div>
  );
}
