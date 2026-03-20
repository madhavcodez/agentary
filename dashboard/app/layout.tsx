import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import AuthProvider from "@/components/AuthProvider";
import AuthGate from "@/components/AuthGate";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SecretAIRY Dashboard",
  description: "AI-powered job matching and career intelligence dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <AuthProvider>
          <AuthGate>{children}</AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}
