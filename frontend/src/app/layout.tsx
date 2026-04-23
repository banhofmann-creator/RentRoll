import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
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
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-gray-50">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex h-14 items-center gap-8">
              <Link href="/" className="text-lg font-semibold text-gray-900">
                RentRoll
              </Link>
              <div className="flex gap-6 text-sm">
                <Link
                  href="/upload"
                  className="text-gray-600 hover:text-gray-900"
                >
                  Upload
                </Link>
                <Link
                  href="/data"
                  className="text-gray-600 hover:text-gray-900"
                >
                  Data
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
