"use client";

import { useState, useEffect } from "react";
import FileUploader from "./components/FileUploader";
import ChatBox from "./components/ChatBox";
import {
  Search,
  History,
  Settings,
  ChevronDown,
  CheckCircle,
  AlertCircle,
} from "lucide-react";

interface UploadedFile {
  name: string;
  status: "uploading" | "success" | "error";
  chunks?: number;
  error?: string;
  docId?: string;
}

export default function Home() {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isSticky, setIsSticky] = useState(false);
  const [backendStatus, setBackendStatus] = useState<
    "checking" | "healthy" | "unhealthy"
  >("checking");

  // Handle scroll for sticky header effect
  useEffect(() => {
    const handleScroll = () => {
      setIsSticky(window.scrollY > 10);
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Check backend health on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      try {
        const response = await fetch("https://localhost:8000/health");
        if (response.ok) {
          const data = await response.json();
          setBackendStatus(data.status === "healthy" ? "healthy" : "unhealthy");
        } else {
          setBackendStatus("unhealthy");
        }
      } catch (error) {
        console.error("Backend health check failed:", error);
        setBackendStatus("unhealthy");
      }
    };

    checkBackendHealth();
  }, []);

  const handleFilesUploaded = (results: UploadedFile[]) => {
    setUploadedFiles((prev) => [...prev, ...results]);
  };

  const hasSuccessfulUploads = uploadedFiles.some(
    (file) => file.status === "success"
  );
  const totalChunks = uploadedFiles
    .filter((file) => file.status === "success")
    .reduce((sum, file) => sum + (file.chunks || 0), 0);

  const getStatusIcon = () => {
    switch (backendStatus) {
      case "checking":
        return (
          <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case "healthy":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "unhealthy":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusText = () => {
    switch (backendStatus) {
      case "checking":
        return "Checking backend...";
      case "healthy":
        return "Backend ready";
      case "unhealthy":
        return "Backend unavailable";
    }
  };

  return (
    <div className="bg-white min-h-screen">
      <div
        className={`sticky top-0 z-10 bg-white transition-shadow duration-300 ${
          isSticky ? "shadow-md" : ""
        }`}
      >
        <div className="max-w-5xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-8">
            <h2 className="text-xl font-bold text-gray-900">Document Chat</h2>
            <nav className="hidden md:flex space-x-1">
              <button className="px-3 py-2 text-sm font-medium text-blue-600 border-b-2 border-blue-600">
                Chat
              </button>
              <button className="px-3 py-2 text-sm font-medium text-gray-600 hover:text-gray-900">
                Documents
              </button>
            </nav>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex items-center gap-2 text-xs">
              {getStatusIcon()}
              <span
                className={`${
                  backendStatus === "healthy"
                    ? "text-green-600"
                    : backendStatus === "unhealthy"
                    ? "text-red-600"
                    : "text-blue-600"
                }`}
              >
                {getStatusText()}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <button className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100">
                <Search className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100">
                <History className="h-5 w-5" />
              </button>
              <button className="p-2 text-gray-500 hover:text-gray-700 rounded-full hover:bg-gray-100">
                <Settings className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <main className="max-w-5xl mx-auto p-6 space-y-8">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-2/3">
            <div className="mb-6">
              <h1 className="text-3xl font-extrabold text-gray-900 mb-2">
                TeamPrompt Assistant
              </h1>
              <p className="text-gray-600">
                Upload your documents and start chatting about them.
              </p>
              {hasSuccessfulUploads && (
                <div className="mt-2 text-sm text-green-600">
                  ✓ {uploadedFiles.filter((f) => f.status === "success").length}{" "}
                  document(s) processed ({totalChunks} chunks ready for search)
                </div>
              )}
            </div>

            <ChatBox hasDocuments={hasSuccessfulUploads} />
          </div>

          <div className="w-full md:w-1/3 space-y-6">
            <FileUploader onFilesUploaded={handleFilesUploaded} />

            {uploadedFiles.length > 0 && (
              <div className="rounded-xl border border-gray-200 shadow-sm p-4 bg-white">
                <h3 className="font-medium text-gray-800 mb-3">
                  Document Status
                </h3>
                <div className="space-y-2">
                  {uploadedFiles.map((file, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm"
                    >
                      <span className="truncate max-w-[150px]">
                        {file.name}
                      </span>
                      <div className="flex items-center gap-2">
                        {file.status === "success" && (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-green-600">
                              {file.chunks} chunks
                            </span>
                          </>
                        )}
                        {file.status === "error" && (
                          <AlertCircle className="h-4 w-4 text-red-500" />
                        )}
                        {file.status === "uploading" && (
                          <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-xl border border-gray-200 shadow-sm p-4 bg-white">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-medium text-gray-800">Recent Chats</h3>
                <button className="text-sm text-blue-600 hover:text-blue-800">
                  View all
                </button>
              </div>

              <div className="space-y-2">
                {[
                  "Q4 Sales Report Analysis",
                  "Marketing Strategy 2025",
                  "Product Roadmap Discussion",
                ].map((chat, idx) => (
                  <button
                    key={idx}
                    className="w-full flex items-center justify-between p-2 text-left rounded hover:bg-gray-50"
                  >
                    <span className="text-sm text-gray-700 truncate">
                      {chat}
                    </span>
                    <ChevronDown className="h-4 w-4 text-gray-400" />
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
