import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SEC Filing Intelligence Copilot",
  description: "Cited research workflows over public SEC filings."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

