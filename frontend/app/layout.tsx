import type { Metadata } from "next";
import "./globals.css";
import { Inter } from "next/font/google";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "TeamPrompt AI Assistant",
  description: "Internal AI chatbot for document & knowledge access",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-white text-gray-900`}>
        <header className="bg-blue-600 text-white shadow-md py-4 px-6 md:px-10">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold">TeamPrompt 🧠</h1>
                <p className="text-sm text-blue-100">
                  Your internal document chat assistant
                </p>
              </div>
              <div className="hidden md:flex space-x-1">
                <button className="px-3 py-1 text-sm bg-blue-700 rounded-md">
                  Dashboard
                </button>
                <button className="px-3 py-1 text-sm hover:bg-blue-700 rounded-md">
                  Help
                </button>
                <button className="px-3 py-1 text-sm hover:bg-blue-700 rounded-md">
                  Account
                </button>
              </div>
            </div>
          </div>
        </header>
        <main>{children}</main>
        <footer className="text-center text-sm text-gray-400 mt-16 py-8 border-t border-gray-100">
          <div className="max-w-5xl mx-auto px-6">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <div className="mb-4 md:mb-0">
                © {new Date().getFullYear()} TeamPrompt. All rights reserved.
              </div>
              <div className="flex space-x-6">
                <a href="#" className="text-gray-500 hover:text-blue-600">
                  Privacy Policy
                </a>
                <a href="#" className="text-gray-500 hover:text-blue-600">
                  Terms of Service
                </a>
                <a href="#" className="text-gray-500 hover:text-blue-600">
                  Contact
                </a>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
