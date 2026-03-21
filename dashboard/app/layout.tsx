import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";
import { ToastProvider } from "@/components/ui/Toast";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Agentary",
  description: "Autonomous research & intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <ToastProvider>
          <div className="flex min-h-screen bg-gray-950">
            <Nav />
            <main className="flex-1 ml-64">{children}</main>
          </div>
        </ToastProvider>
      </body>
    </html>
  );
}
