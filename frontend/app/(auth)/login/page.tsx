"use client";
import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";

const STABLE_URL = "https://tender-copilot-sable.vercel.app";

function TenderCopilotLogo({ size = 48 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
      <polygon points="24,2 44,13 44,35 24,46 4,35 4,13" fill="#0F172A" stroke="#3B82F6" strokeWidth="1.5"/>
      <rect x="14" y="13" width="14" height="18" rx="2" fill="none" stroke="#94A3B8" strokeWidth="1.2"/>
      <line x1="17" y1="18" x2="25" y2="18" stroke="#94A3B8" strokeWidth="1.2" strokeLinecap="round"/>
      <line x1="17" y1="21.5" x2="25" y2="21.5" stroke="#94A3B8" strokeWidth="1.2" strokeLinecap="round"/>
      <line x1="17" y1="25" x2="22" y2="25" stroke="#94A3B8" strokeWidth="1.2" strokeLinecap="round"/>
      <path d="M26 27 L34 20" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round"/>
      <path d="M30 20 L34 20 L34 24" stroke="#3B82F6" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx="36" cy="10" r="2" fill="#14B8A6" opacity="0.8"/>
      <circle cx="12" cy="10" r="2" fill="#14B8A6" opacity="0.8"/>
      <circle cx="12" cy="38" r="2" fill="#14B8A6" opacity="0.8"/>
    </svg>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  // Safe redirectTo — never send to /register or /login after auth
  const rawRedirect = searchParams.get("redirectTo") || "/tenders";
  const blocked = ["/register", "/login", "/auth"];
  const redirectTo = blocked.some(b => rawRedirect.startsWith(b)) ? "/tenders" : rawRedirect;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wrongUrl, setWrongUrl] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const isWrong =
        window.location.hostname !== new URL(STABLE_URL).hostname &&
        window.location.hostname !== "localhost";
      setWrongUrl(isWrong);
    }
    if (searchParams.get("error") === "auth_failed") {
      setError("Sign-in failed. Please try again or use email/password.");
    }
  }, [searchParams]);

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
    if (wrongUrl) {
      window.location.href = `${STABLE_URL}/login`;
      return;
    }
    setGoogleLoading(true);
    setError(null);
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: `${STABLE_URL}/auth/callback?redirectTo=${redirectTo}`,
        },
      });
      if (error) throw error;
    } catch (err: any) {
      setError("Google sign-in is not available. Please use email/password.");
      setGoogleLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-4"
      style={{
        background: "#020B18",
        fontFamily: "'Mona Sans', 'Inter', sans-serif",
        backgroundImage:
          "radial-gradient(ellipse at 20% 50%, rgba(59,130,246,0.06) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(20,184,166,0.04) 0%, transparent 50%)",
      }}
    >
      <div className="max-w-md w-full">
        {wrongUrl && (
          <div
            className="mb-4 px-4 py-3 rounded-lg text-sm text-center"
            style={{
              background: "rgba(245,158,11,0.12)",
              border: "1px solid rgba(245,158,11,0.3)",
              color: "#FCD34D",
            }}
          >
            ⚠️ You're on an old URL.{" "}
            <a href={STABLE_URL} style={{ color: "#FBBF24", fontWeight: 600, textDecoration: "underline" }}>
              Click here to use the correct link →
            </a>
          </div>
        )}

        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-3">
            <TenderCopilotLogo size={48} />
            <div className="text-left">
              <h1 className="text-3xl font-bold leading-none">
                <span style={{ color: "#F1F5F9" }}>Tender</span>
                <span style={{ color: "#3B82F6" }}>Copilot</span>
              </h1>
              <div style={{ height: "2px", background: "linear-gradient(90deg, #3B82F6, #14B8A6)", borderRadius: "2px", marginTop: "3px" }} />
            </div>
          </div>
          <p className="text-sm" style={{ color: "#64748B" }}>
            AI-powered tender intelligence for Indian MSMEs
          </p>
        </div>

        <div
          className="rounded-2xl p-8 shadow-2xl"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(59,130,246,0.15)",
            backdropFilter: "blur(12px)",
          }}
        >
          <h2 className="text-xl font-semibold mb-6" style={{ color: "#F1F5F9" }}>
            Sign in to your account
          </h2>

          {error && (
            <div
              className="mb-4 px-4 py-3 rounded-lg text-sm"
              style={{ background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.25)", color: "#FCA5A5" }}
            >
              {error}
            </div>
          )}

          <button
            onClick={handleGoogleLogin}
            disabled={googleLoading}
            className="w-full flex items-center justify-center gap-3 py-2.5 rounded-lg text-sm font-medium mb-4 transition-all"
            style={{
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              color: "#F1F5F9",
              cursor: googleLoading ? "not-allowed" : "pointer",
              opacity: googleLoading ? 0.6 : 1,
            }}
          >
            {googleLoading ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Redirecting to Google…
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 48 48">
                  <path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.2l6.7-6.7C35.7 2.5 30.2 0 24 0 14.8 0 6.9 5.4 3 13.3l7.8 6C12.7 13.1 17.9 9.5 24 9.5z"/>
                  <path fill="#4285F4" d="M46.5 24.5c0-1.6-.1-3.1-.4-4.5H24v8.5h12.7c-.6 3-2.3 5.5-4.8 7.2l7.5 5.8C43.5 37.5 46.5 31.5 46.5 24.5z"/>
                  <path fill="#FBBC05" d="M10.8 28.7A14.8 14.8 0 0 1 9.5 24c0-1.6.3-3.2.8-4.7L2.5 13.3A23.9 23.9 0 0 0 0 24c0 3.9.9 7.5 2.5 10.7l8.3-6z"/>
                  <path fill="#34A853" d="M24 48c6.2 0 11.4-2 15.2-5.5l-7.5-5.8c-2 1.4-4.6 2.2-7.7 2.2-6.1 0-11.3-3.6-13.2-9.2l-8.3 6C6.9 42.6 14.8 48 24 48z"/>
                </svg>
                Continue with Google
              </>
            )}
          </button>

          <div className="flex items-center gap-3 mb-4">
            <div style={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.08)" }} />
            <span className="text-xs" style={{ color: "#475569" }}>or sign in with email</span>
            <div style={{ flex: 1, height: "1px", background: "rgba(255,255,255,0.08)" }} />
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>Email Address</label>
              <input
                type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com" autoComplete="email"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#F1F5F9" }}
              />
            </div>
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>Password</label>
              <input
                type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••" autoComplete="current-password"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none"
                style={{ background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)", color: "#F1F5F9" }}
              />
            </div>
            <button
              type="submit" disabled={loading}
              className="w-full py-3 rounded-lg text-sm font-semibold"
              style={{ background: loading ? "rgba(59,130,246,0.5)" : "#3B82F6", color: "#fff", cursor: loading ? "not-allowed" : "pointer" }}
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

          <p className="text-center text-sm mt-6" style={{ color: "#475569" }}>
            Don&apos;t have an account?{" "}
            <Link href="/register" style={{ color: "#3B82F6", fontWeight: 500 }}>Create account</Link>
          </p>
        </div>

        <p className="text-center text-xs mt-6" style={{ color: "#334155" }}>
          Pynevera Technologies Pvt Ltd · Coimbatore
        </p>
      </div>
    </div>
  );
}
