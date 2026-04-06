"use client";
import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import LoadingSpinner from "@/src/components/LoadingSpinner";
import { LanguageProvider, LanguageToggle, useLang } from "@/src/components/LanguageContext";
export { useLang };

const NAV = [
  { href: "/tenders", en: "Tenders",  ta: "டெண்டர்கள்" },
  { href: "/bids",    en: "Bids",     ta: "ஒப்பந்தங்கள்" },
  { href: "/vault",   en: "Vault",    ta: "கோப்பகம்" },
  { href: "/alerts",  en: "Alerts",   ta: "விழிப்பூட்டல்கள்" },
  { href: "/profile", en: "Profile",  ta: "சுயவிவரம்" },
];

// Inline SVG logo — never breaks, no external file needed
function TenderCopilotIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
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

function NavBar() {
  const pathname = usePathname();
  const { lang, t } = useLang();
  const [loading, setLoading] = useState(false);
  const prevPath = React.useRef(pathname);

  useEffect(() => {
    if (prevPath.current !== pathname) {
      prevPath.current = pathname;
      setLoading(true);
      const timer = setTimeout(() => setLoading(false), 600);
      return () => clearTimeout(timer);
    }
  }, [pathname]);

  return (
    <>
      {loading && <LoadingSpinner fullScreen message="Loading..." />}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex">
              <div className="flex-shrink-0 flex items-center gap-2">
                {/* Inline SVG — replaces broken logo-icon.png */}
                <TenderCopilotIcon />
                <span className="text-xl font-semibold text-gray-900">
                  {t("Tender Copilot", "டெண்டர் கோபைலட்")}
                </span>
              </div>
              <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                {NAV.map(({ href, en, ta }) => {
                  const isActive = pathname === href || pathname.startsWith(href + "/");
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors ${
                        isActive
                          ? "border-indigo-500 text-gray-900"
                          : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                      }`}
                    >
                      {lang === "ta" ? ta : en}
                    </Link>
                  );
                })}
              </div>
            </div>
            <div className="flex items-center">
              <LanguageToggle />
            </div>
          </div>
        </div>
      </nav>
    </>
  );
}

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <LanguageProvider>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main>{children}</main>
      </div>
    </LanguageProvider>
  );
}
