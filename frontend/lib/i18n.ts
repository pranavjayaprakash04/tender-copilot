"use client";

// Minimal useTranslation stub — returns the key as-is.
// next-i18next requires Pages Router + serverSideTranslations which is not compatible
// with Next.js 14 App Router. Replace with next-intl if full i18n is needed.
export function useTranslation(_ns?: string) {
  return {
    t: (key: string) => key,
    i18n: { language: "en" as const },
  };
}
