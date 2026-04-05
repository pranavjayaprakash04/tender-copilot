"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface LanguageContextType {
  language: "en" | "ta";
  setLanguage: (lang: "en" | "ta") => void;
  t: (en: string, ta: string) => string;
  isTamil: boolean;
}

const LanguageContext = createContext<LanguageContextType>({
  language: "en",
  setLanguage: () => {},
  t: (en) => en,
  isTamil: false,
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<"en" | "ta">("en");

  const t = (en: string, ta: string) => language === "ta" ? ta : en;

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t, isTamil: language === "ta" }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}

export function LanguageToggle() {
  const { language, setLanguage } = useLanguage();
  return (
    <button
      onClick={() => setLanguage(language === "en" ? "ta" : "en")}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-gray-200 hover:border-gray-400 transition-colors bg-white"
      title="Toggle language"
    >
      <span>{language === "en" ? "🇮🇳" : "🇬🇧"}</span>
      <span className="text-gray-700">{language === "en" ? "தமிழ்" : "English"}</span>
    </button>
  );
}
