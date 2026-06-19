import type { Metadata } from "next";
import { Fraunces, Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

// Display: Fraunces — high-contrast editorial serif for headlines and big numbers
const fraunces = Fraunces({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "900"],
  style: ["normal", "italic"],
  variable: "--font-fraunces",
  display: "swap",
});

// Body / UI: Inter
const inter = Inter({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

// Data / codes: IBM Plex Mono — financial-grade monospace
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-plex",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Liquidity Lens — Working Capital Diagnostic",
  description:
    "A working-capital diagnostic for GCC distributors. Where cash is trapped, why, and what to release first.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`h-full ${fraunces.variable} ${inter.variable} ${plexMono.variable}`}
    >
      <body className="min-h-full antialiased">{children}</body>
    </html>
  );
}
