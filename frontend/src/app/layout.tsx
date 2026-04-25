import type { Metadata } from "next";
import { Open_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const openSans = Open_Sans({
  variable: "--font-open-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RentRoll",
  description: "GARBE Mieterliste CSV → BVI Target Database",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${openSans.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col font-sans">
        <nav className="bg-garbe-blau">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex h-14 items-center gap-8">
              <Link
                href="/"
                className="text-lg font-semibold text-white tracking-wider uppercase"
              >
                RentRoll
              </Link>
              <div className="flex gap-6 text-sm">
                <Link
                  href="/upload"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Upload
                </Link>
                <Link
                  href="/data"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Data
                </Link>
                <Link
                  href="/inconsistencies"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Quality
                </Link>
                <Link
                  href="/transform"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Transform
                </Link>
                <Link
                  href="/master-data"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Master Data
                </Link>
                <Link
                  href="/periods"
                  className="text-garbe-blau-20 hover:text-white transition-colors"
                >
                  Periods
                </Link>
              </div>
            </div>
          </div>
        </nav>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
