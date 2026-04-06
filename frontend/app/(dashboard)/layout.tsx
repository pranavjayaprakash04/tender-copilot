"use client";
import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LanguageProvider, LanguageToggle, useLang } from "@/src/components/LanguageContext";

export { useLang };

const NAV = [
  { href: "/tenders", en: "Tenders",  ta: "டெண்டர்கள்" },
  { href: "/bids",    en: "Bids",     ta: "ஒப்பந்தங்கள்" },
  { href: "/vault",   en: "Vault",    ta: "கோப்பகம்" },
  { href: "/alerts",  en: "Alerts",   ta: "விழிப்பூட்டல்கள்" },
  { href: "/profile", en: "Profile",  ta: "சுயவிவரம்" },
];

function NavBar() {
  const pathname = usePathname();
  const { lang, t } = useLang();
  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center gap-2">
              <img src="/logo-icon.png" alt="TenderCopilot" className="h-8 w-8" />
              <span className="text-xl font-semibold text-gray-900">
                {t("Tender Copilot", "டெண்டர் கோபைலட்")}
              </span>
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
          <div className="flex items-center">
            <LanguageToggle />
          </div>
        </div>
      </div>
    </nav>
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
