import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TenderCopilot — AI Tender Intelligence",
  description: "AI-powered government tender intelligence for Indian MSMEs",
  icons: {
    // Inline SVG favicon — no PNG file needed
    icon: "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'%3E%3Cpolygon points='24,2 44,13 44,35 24,46 4,35 4,13' fill='%230F172A' stroke='%233B82F6' stroke-width='1.5'/%3E%3Cpath d='M26 27 L34 20' stroke='%233B82F6' stroke-width='1.8' stroke-linecap='round'/%3E%3Cpath d='M30 20 L34 20 L34 24' stroke='%233B82F6' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
