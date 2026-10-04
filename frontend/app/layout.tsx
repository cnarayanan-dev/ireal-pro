import type { Metadata, Viewport } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blues Loop",
  description: "Practice blues over looping backing tracks",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <Link href="/" className="brand">
            Blues<span>Loop</span>
          </Link>
          <nav>
            <Link href="/">Library</Link>
            <Link href="/new">New chart</Link>
          </nav>
        </header>
        <main>{children}</main>
      </body>
    </html>
  );
}
