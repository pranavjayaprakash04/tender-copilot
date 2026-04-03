"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";
import Link from "next/link";

export default function RegisterPage() {
  const router = useRouter();
  const [companyName, setCompanyName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    try {
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            company_name: companyName,
            full_name: companyName,
          },
        },
      });

      if (signUpError) throw signUpError;

      if (data.session) {
        router.push("/profile");
        router.refresh();
      } else {
        setSuccess(true);
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div
        className="min-h-screen flex items-center justify-center px-4"
        style={{ background: "#020B18", fontFamily: "'Mona Sans', 'Inter', sans-serif" }}
      >
        <div className="max-w-md w-full text-center">
          <div
            className="rounded-2xl p-10 shadow-2xl"
            style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(212,175,55,0.2)" }}
          >
            <div className="text-5xl mb-4">📬</div>
            <h2 className="text-2xl font-bold mb-3" style={{ color: "#D4AF37" }}>
              Check your email
            </h2>
            <p className="text-sm mb-6" style={{ color: "#94A3B8" }}>
              We sent a confirmation link to <strong style={{ color: "#E2E8F0" }}>{email}</strong>.
              Click the link to activate your account.
            </p>
            <Link
              href="/login"
              className="text-sm font-medium"
              style={{ color: "#D4AF37" }}
            >
              Back to login
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: "#020B18", fontFamily: "'Mona Sans', 'Inter', sans-serif" }}
    >
      <div className="max-w-md w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2" style={{ color: "#D4AF37" }}>
            TenderCopilot
          </h1>
          <p className="text-sm" style={{ color: "#94A3B8" }}>
            Create your account and start winning tenders
          </p>
        </div>

        <div
          className="rounded-2xl p-8 shadow-2xl"
          style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(212,175,55,0.15)" }}
        >
          <h2 className="text-xl font-semibold mb-6" style={{ color: "#F1F5F9" }}>
            Create Account
          </h2>

          {error && (
            <div
              className="mb-4 px-4 py-3 rounded-lg text-sm"
              style={{ background: "rgba(239,68,68,0.15)", border: "1px solid rgba(239,68,68,0.3)", color: "#FCA5A5" }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>
                Company Name
              </label>
              <input
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="Your Company Pvt Ltd"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none transition-all"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#F1F5F9",
                }}
              />
            </div>

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
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none transition-all"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#F1F5F9",
                }}
              />
            </div>

            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: "#94A3B8" }}>
                Password <span style={{ color: "#64748B" }}>(min 6 characters)</span>
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="new-password"
                className="w-full px-4 py-2.5 rounded-lg text-sm outline-none transition-all"
                style={{
                  background: "rgba(255,255,255,0.06)",
                  border: "1px solid rgba(255,255,255,0.12)",
                  color: "#F1F5F9",
                }}
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 rounded-lg text-sm font-semibold transition-all"
              style={{
                background: loading ? "rgba(212,175,55,0.5)" : "#D4AF37",
                color: "#020B18",
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                  </svg>
                  Creating account…
                </span>
              ) : (
                "Create Account"
              )}
            </button>
          </form>

          <p className="text-center text-sm mt-6" style={{ color: "#64748B" }}>
            Already have an account?{" "}
            <Link href="/login" className="font-medium" style={{ color: "#D4AF37" }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
