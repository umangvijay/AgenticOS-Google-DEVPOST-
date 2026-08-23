import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AgenticOS",
  description: "Agentic OS Final UX Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen bg-background text-foreground antialiased`}>
        <div className="flex flex-col min-h-screen">
          <header className="border-b border-border bg-card/50 backdrop-blur-md sticky top-0 z-50">
            <div className="container mx-auto px-4 h-16 flex items-center justify-between">
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">AgenticOS</h1>
              <nav className="flex space-x-4">
                {/* Navigation links if needed */}
              </nav>
            </div>
          </header>
          <main className="flex-1 flex flex-col relative">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
