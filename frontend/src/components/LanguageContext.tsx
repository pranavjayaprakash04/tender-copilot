"use client";
import { createContext, useContext, useState, ReactNode } from "react";

interface LangCtx {
  lang: "en" | "ta";
  toggle: () => void;
  t: (en: string, ta: string) => string;
  isTamil: boolean;
}

const LangContext = createContext<LangCtx>({
  lang: "en",
  toggle: () => {},
  t: (en) => en,
  isTamil: false,
});

export function useLang() { return useContext(LangContext); }

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<"en" | "ta">("en");
  const toggle = () => setLang(l => l === "en" ? "ta" : "en");
  const t = (en: string, ta: string) => lang === "ta" ? ta : en;
  return (
    <LangContext.Provider value={{ lang, toggle, t, isTamil: lang === "ta" }}>
      {children}
    </LangContext.Provider>
  );
}

export function LanguageToggle() {
  const { lang, toggle } = useLang();
  return (
    <button onClick={toggle}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-gray-200 hover:border-indigo-400 hover:text-indigo-600 transition-colors bg-white">
      {lang === "en" ? <><span>🇮🇳</span><span>தமிழ்</span></> : <><span>🇬🇧</span><span>English</span></>}
    </button>
  );
}
