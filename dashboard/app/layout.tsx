import type { Metadata } from "next";
import { Inter, Lora } from "next/font/google";
import "./globals.css";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ToastProvider } from "@/components/ui/Toast";
import { WebSocketProvider } from "@/components/WebSocketProvider";
import AuthProvider from "@/components/AuthProvider";
import AuthGate from "@/components/AuthGate";

const inter = Inter({ subsets: ["latin"] });
const lora = Lora({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
  variable: "--font-lora",
});

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
      <body className={`${inter.className} ${lora.variable}`}>
        <ToastProvider>
          <AuthProvider>
            <WebSocketProvider>
              <ErrorBoundary>
                <AuthGate>{children}</AuthGate>
              </ErrorBoundary>
            </WebSocketProvider>
          </AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
