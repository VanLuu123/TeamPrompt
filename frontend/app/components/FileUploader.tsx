"use client";
import { useState, useRef } from "react";
import { Upload, File, X, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "./ui/button";

interface UploadedFile {
  name: string;
  status: "uploading" | "success" | "error";
  chunks?: number;
  error?: string;
}

export default function FileUploader({
  onFilesSelected,
  onUploadComplete,
}: {
  onFilesSelected: (files: FileList | null) => void;
  onUploadComplete?: (results: UploadedFile[]) => void;
}) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = [
    ".pdf",
    ".txt",
    ".html",
    ".md",
    ".docx",
    ".doc",
    ".csv",
  ];
  const maxFileSize = 10 * 1024 * 1024; // 10MB

  const validateFiles = (files: FileList): boolean => {
    setError(null);

    // Check if any file is not allowed type
    const invalidTypeFile = Array.from(files).find((file) => {
      const extension = "." + file.name.split(".").pop()?.toLowerCase();
      return !allowedTypes.includes(extension);
    });

    if (invalidTypeFile) {
      setError(
        `"${
          invalidTypeFile.name
        }" is not a supported file type. Please use: ${allowedTypes.join(", ")}`
      );
      return false;
    }

    // Check if any file exceeds size limit
    const oversizedFile = Array.from(files).find(
      (file) => file.size > maxFileSize
    );
    if (oversizedFile) {
      setError(`"${oversizedFile.name}" exceeds the 10MB size limit`);
      return false;
    }

    return true;
  };

  const uploadFile = async (file: File): Promise<UploadedFile> => {
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/upload-documents", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      const data = await response.json();
      return {
        name: file.name,
        status: "success",
        chunks: data.chunks_created,
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
    if (!validateFiles(fileList)) return;

    setIsUploading(true);
    setError(null);

    const initialFiles = Array.from(fileList).map((file) => ({
      name: file.name,
      status: "uploading" as const,
    }));
    setFiles(initialFiles);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files;
    if (fileList && fileList.length > 0) {
      handleFileUpload(fileList);
      onFilesSelected?.(fileList);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files);
      onFilesSelected?.(e.dataTransfer.files);
      if (inputRef.current) inputRef.current.files = e.dataTransfer.files;
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const removeFile = (index: number) => {
    const newFiles = [...files];
    newFiles.splice(index, 1);
    setFiles(newFiles);

    // Reset the file input if all files are removed
    if (newFiles.length === 0) {
      if (inputRef.current) inputRef.current.value = "";
      onFilesSelected(null);
    }
  };

  const handleBrowse = () => {
    inputRef.current?.click();
  };

  const getStatusIcon = (status: UploadedFile["status"]) => {
    switch (status) {
      case "uploading":
        return (
          <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
    }
  };

  const getStatusColor = (status: UploadedFile["status"]) => {
    switch (status) {
      case "uploading":
        return "border-blue-200 bg-blue-50";
      case "success":
        return "border-green-200 bg-green-50";
      case "error":
        return "border-red-200 bg-red-50";
    }
  };

  return (
    <div className="rounded-xl border border-gray-200 shadow-sm p-6 bg-white space-y-4">
      <h3 className="text-lg font-medium text-gray-800">Upload Documents</h3>

      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-8 transition-colors text-center
          ${
            dragActive
              ? "border-blue-500 bg-blue-50"
              : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
          }`}
      >
        <input
          ref={inputRef}
          type="file"
          accept={allowedTypes.join(",")}
          multiple
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />

        <div className="flex flex-col items-center justify-center space-y-3">
          <div className="p-3 bg-blue-50 rounded-full">
            <Upload className="h-6 w-6 text-blue-500" />
          </div>
          <div className="text-gray-700">
            <span className="font-medium">Click to upload</span> or drag and
            drop
          </div>
          <div className="text-xs text-gray-500">
            Supported formats: PDF, TXT, HTML, MD, DOCX (Max 10MB)
          </div>
          <Button
            type="button"
            onClick={handleBrowse}
            disabled={isUploading}
            className="mt-2"
          >
            {isUploading ? "Uploading..." : "Browse Files"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-md">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {files.length > 0 && (
        <div className="rounded-md bg-gray-50 border border-gray-200 p-4 text-sm">
          <p className="font-medium text-gray-700 mb-2">
            {isUploading ? "Uploading Files..." : "Uploaded Files:"}
          </p>
          <ul className="space-y-2">
            {files.map((file, idx) => (
              <li
                key={idx}
                className={`flex items-center justify-between p-2 rounded border ${getStatusColor(
                  file.status
                )}`}
              >
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  {getStatusIcon(file.status)}
                  <span className="truncate max-w-[200px]">{file.name}</span>
                  {file.status === "success" && file.chunks && (
                    <span className="text-xs text-green-600 ml-2">
                      {file.chunks} chunks
                    </span>
                  )}
                  {file.status === "error" && file.error && (
                    <span className="text-xs text-red-600 ml-2">
                      {file.error}
                    </span>
                  )}
                </div>
                {file.status !== "uploading" && (
                  <button
                    onClick={() => removeFile(idx)}
                    className="text-gray-400 hover:text-red-500 focus:outline-none ml-2"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
