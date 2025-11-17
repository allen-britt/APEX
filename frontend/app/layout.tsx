import Link from "next/link";
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Project APEX",
  description: "Mission intelligence console",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100">
        <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
            <Link href="/" className="text-xl font-semibold text-cyan-200 hover:text-cyan-100">
              Project APEX
            </Link>
            <nav className="flex items-center gap-4 text-sm text-slate-400">
              <Link href="/" className="hover:text-cyan-200">
                Missions
              </Link>
              <Link href="/settings" className="hover:text-cyan-200">
                Settings
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
