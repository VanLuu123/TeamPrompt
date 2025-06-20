"use client";
import { useState, useRef } from "react";
import { config } from "../../config";

interface UploadedFile {
  name: string;
  status: "uploading" | "success" | "error";
  chunks?: number;
  error?: string;
  docId?: string;
}

interface FileUploaderProps {
  onFilesUploaded?: (files: UploadedFile[]) => void;
}

export default function FileUploader({ onFilesUploaded }: FileUploaderProps) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = [".pdf", ".txt", ".html", ".md", ".docx", ".csv"];
  const maxFileSize = 10 * 1024 * 1024; // 10MB

  const validateFiles = (fileList: FileList): string | null => {
    for (const file of Array.from(fileList)) {
      const extension = "." + file.name.split(".").pop()?.toLowerCase();

      if (!allowedTypes.includes(extension)) {
        return `"${file.name}" is not supported. Use: ${allowedTypes.join(
          ", "
        )}`;
      }

      if (file.size > maxFileSize) {
        return `"${file.name}" exceeds 10MB limit`;
      }
    }
    return null;
  };

  const uploadFile = async (file: File): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${config.backendUrl}/upload-document`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Upload failed (${response.status})`
        );
      }

      const data = await response.json();
      return {
        name: file.name,
        status: "success",
        chunks: data.chunks,
        docId: data.doc_id,
      };
    } catch (error) {
      return {
        name: file.name,
        status: "error",
        error: error instanceof Error ? error.message : "Upload failed",
      };
    }
  };

  const handleFileUpload = async (fileList: FileList) => {
    const validationError = validateFiles(fileList);
    if (validationError) {
      setError(validationError);
      return;
    }

    setError(null);
    setIsUploading(true);

    // Initialize files with uploading status
    const initialFiles = Array.from(fileList).map((file) => ({
      name: file.name,
      status: "uploading" as const,
    }));

    setFiles((prev) => [...prev, ...initialFiles]);

    // Upload files
    const uploadResults = await Promise.all(
      Array.from(fileList).map(uploadFile)
    );

    // Update files with results
    setFiles((prev) => {
      const newFiles = [...prev];
      uploadResults.forEach((result) => {
        const fileIndex = newFiles.findIndex(
          (f) => f.name === result.name && f.status === "uploading"
        );
        if (fileIndex >= 0) {
          newFiles[fileIndex] = result;
        }
      });
      return newFiles;
    });

    setIsUploading(false);
    onFilesUploaded?.(uploadResults);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (fileList && fileList.length > 0) {
      handleFileUpload(fileList);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);

    const fileList = e.dataTransfer.files;
    if (fileList && fileList.length > 0) {
      handleFileUpload(fileList);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAll = () => {
    setFiles([]);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  };

  const getStatusIcon = (status: UploadedFile["status"]) => {
    switch (status) {
      case "uploading":
        return (
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case "success":
        return (
          <svg
            className="w-4 h-4 text-green-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        );
      case "error":
        return (
          <svg
            className="w-4 h-4 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        );
    }
  };

  const successfulUploads = files.filter((f) => f.status === "success").length;

  return (
    <div className="border rounded-lg bg-white shadow-sm p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-800">
          Upload Documents
        </h3>
        {files.length > 0 && (
          <button
            onClick={clearAll}
            className="text-sm text-gray-500 hover:text-red-500 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      {/* Upload Area */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          dragActive
            ? "border-blue-500 bg-blue-50"
            : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
        }`}
        onClick={() => inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={allowedTypes.join(",")}
          multiple
          onChange={handleFileSelect}
          className="hidden"
          disabled={isUploading}
        />

        <div className="space-y-3">
          <div className="w-12 h-12 mx-auto bg-blue-100 rounded-full flex items-center justify-center">
            <svg
              className="w-6 h-6 text-blue-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>

          <div>
            <p className="text-gray-700">
              <span className="font-medium">Click to upload</span> or drag and
              drop
            </p>
            <p className="text-sm text-gray-500 mt-1">
              PDF, TXT, HTML, MD, DOCX, CSV (Max 10MB each)
            </p>
          </div>

          <button
            type="button"
            disabled={isUploading}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              isUploading
                ? "bg-gray-300 text-gray-500 cursor-not-allowed"
                : "bg-blue-600 text-white hover:bg-blue-700"
            }`}
          >
            {isUploading ? "Uploading..." : "Browse Files"}
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 flex items-center space-x-2">
          <svg
            className="w-5 h-5 text-red-500"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-sm text-red-700">{error}</span>
        </div>
      )}

      {/* Files List */}
      {files.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-medium text-gray-700">
              {isUploading ? "Uploading Files..." : "Files"}
            </h4>
            {successfulUploads > 0 && (
              <span className="text-sm text-green-600 bg-green-50 px-2 py-1 rounded">
                {successfulUploads} uploaded successfully
              </span>
            )}
          </div>

          <div className="space-y-2">
            {files.map((file, index) => (
              <div
                key={index}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  file.status === "success"
                    ? "bg-green-50 border-green-200"
                    : file.status === "error"
                    ? "bg-red-50 border-red-200"
                    : "bg-blue-50 border-blue-200"
                }`}
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  {getStatusIcon(file.status)}

                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    {file.status === "success" && file.chunks && (
                      <p className="text-xs text-green-600">
                        {file.chunks} chunks created
                      </p>
                    )}
                    {file.status === "error" && file.error && (
                      <p className="text-xs text-red-600">{file.error}</p>
                    )}
                  </div>
                </div>

                {file.status !== "uploading" && (
                  <button
                    onClick={() => removeFile(index)}
                    className="text-gray-400 hover:text-red-500 transition-colors p-1"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
