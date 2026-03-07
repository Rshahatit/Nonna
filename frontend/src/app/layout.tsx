import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";

export const metadata: Metadata = {
  title: "Nonna — Preserve Your Family's Stories",
  description:
    "A warm AI companion that helps elders share their stories, skills, and wisdom. Every conversation becomes a Memory Reel your family keeps forever.",
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#FFF8F0",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-nonna-cream text-nonna-dark min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
