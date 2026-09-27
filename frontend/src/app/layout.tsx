import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

// Reuse the font bundled with the pinned Next.js version; no network request.
const geistSans = localFont({
  src: "../../node_modules/next/dist/next-devtools/server/font/geist-latin.woff2",
  variable: "--font-geist-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "LexProof — Evidence before confidence",
  description:
    "Verify AI legal claims against primary law. Trace every verdict to authoritative legal evidence with LexProof.",
  icons: { icon: "/icon.svg" },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
