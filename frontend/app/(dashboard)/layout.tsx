"use client";
import React, { createContext, useContext, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

// ── Language Context ──────────────────────────────────────────────────────────
interface LangCtx { lang: "en" | "ta"; toggle: () => void; t: (en: string, ta: string) => string; }
const LangContext = createContext<LangCtx>({ lang: "en", toggle: () => {}, t: (en) => en });
export function useLang() { return useContext(LangContext); }

// ── Nav translations ──────────────────────────────────────────────────────────
const NAV = [
  { href: "/tenders", en: "Tenders",  ta: "டெண்டர்கள்" },
  { href: "/bids",    en: "Bids",     ta: "ஒப்பந்தங்கள்" },
  { href: "/vault",   en: "Vault",    ta: "கோப்பகம்" },
  { href: "/alerts",  en: "Alerts",   ta: "விழிப்பூட்டல்கள்" },
  { href: "/profile", en: "Profile",  ta: "சுயவிவரம்" },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [lang, setLang] = useState<"en" | "ta">("en");
  const toggle = () => setLang(l => l === "en" ? "ta" : "en");
  const t = (en: string, ta: string) => lang === "ta" ? ta : en;

  return (
    <LangContext.Provider value={{ lang, toggle, t }}>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-xl font-semibold text-gray-900">
                    {t("Tender Copilot", "டெண்டர் கோபைலட்")}
                  </h1>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  {NAV.map(({ href, en, ta }) => {
                    const isActive = pathname === href || pathname.startsWith(href + "/");
                    return (
                      <Link key={href} href={href}
                        className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                          isActive
                            ? "border-indigo-500 text-gray-900"
                            : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                        }`}>
                        {lang === "ta" ? ta : en}
                      </Link>
                    );
                  })}
                </div>
              </div>

              {/* Language toggle */}
              <div className="flex items-center">
                <button
                  onClick={toggle}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-gray-200 hover:border-indigo-400 hover:text-indigo-600 transition-colors bg-white"
                >
                  {lang === "en" ? (
                    <><span>🇮🇳</span><span>தமிழ்</span></>
                  ) : (
                    <><span>🇬🇧</span><span>English</span></>
                  )}
                </button>
              </div>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </div>
    </LangContext.Provider>
  );
}
