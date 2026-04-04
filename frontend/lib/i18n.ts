"use client";

// Minimal useTranslation stub — returns the key as-is.
// next-i18next is incompatible with Next.js 14 App Router.
export function useTranslation(_ns?: string) {
  return {
    t: (key: string) => key,
    // typed as string (not literal "en") so comparisons like i18n.language === "ta" compile
    i18n: { language: "en" as string },
  };
}
