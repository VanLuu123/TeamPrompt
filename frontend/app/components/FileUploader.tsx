"use client";
import { useState, useRef } from "react";
import { Upload, File, X, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";

export default function FileUploader({
  onFilesSelected,
}: {
  onFilesSelected: (files: FileList | null) => void;
}) {
  const [fileNames, setFileNames] = useState<string[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const allowedTypes = [".pdf", ".txt", ".html", ".md", ".docx", ".doc"];
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      if (validateFiles(files)) {
        setFileNames(Array.from(files).map((file) => file.name));
        onFilesSelected(files);
      } else {
        e.target.value = "";
      }
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      if (validateFiles(e.dataTransfer.files)) {
        setFileNames(Array.from(e.dataTransfer.files).map((file) => file.name));
        onFilesSelected(e.dataTransfer.files);
        if (inputRef.current) inputRef.current.files = e.dataTransfer.files;
      }
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
    const newFileNames = [...fileNames];
    newFileNames.splice(index, 1);
    setFileNames(newFileNames);

    // Reset the file input if all files are removed
    if (newFileNames.length === 0) {
      if (inputRef.current) inputRef.current.value = "";
      onFilesSelected(null);
    }
  };

  const handleBrowse = () => {
    inputRef.current?.click();
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
          <Button type="button" onClick={handleBrowse} className="mt-2">
            Browse Files
          </Button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-red-600 bg-red-50 p-3 rounded-md">
          <AlertCircle className="h-5 w-5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {fileNames.length > 0 && (
        <div className="rounded-md bg-gray-50 border border-gray-200 p-4 text-sm">
          <p className="font-medium text-gray-700 mb-2">Selected Files:</p>
          <ul className="space-y-2">
            {fileNames.map((name, idx) => (
              <li
                key={idx}
                className="flex items-center justify-between p-2 bg-white rounded border border-gray-200"
              >
                <div className="flex items-center gap-2">
                  <File className="h-4 w-4 text-blue-500" />
                  <span className="truncate max-w-[250px]">{name}</span>
                </div>
                <button
                  onClick={() => removeFile(idx)}
                  className="text-gray-400 hover:text-red-500 focus:outline-none"
                >
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
