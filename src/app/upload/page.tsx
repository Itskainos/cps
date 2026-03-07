"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  Upload,
  X,
  ChevronRight,
  ChevronLeft,
  AlertCircle,
  CheckCircle2,
  XCircle
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Helper to format bytes
function formatBytes(bytes: number, decimals = 2) {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

type FileStatus = "pending" | "processing" | "success" | "error";

interface ExtendedFile {
  file: File;
  status: FileStatus;
  errorMsg?: string;
}

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<ExtendedFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [globalError, setGlobalError] = useState<string | null>(null);
  
  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => {
      // Prevent duplicates by name
      const existingNames = new Set(prev.map(f => f.file.name));
      const newFiles = acceptedFiles
        .filter(f => !existingNames.has(f.name))
        .map(file => ({ file, status: "pending" as FileStatus }));
      return [...prev, ...newFiles];
    });
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "image/*": [".png", ".jpg", ".jpeg"]
    },
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const processBatch = async () => {
    if (files.length === 0) return;
    setLoading(true);
    setGlobalError(null);
    setProgress(0);

    // Reset status of any previously failed files
    setFiles(prev => prev.map(f => ({ ...f, status: f.status === "error" ? "pending" : f.status, errorMsg: undefined })));

    let batchIdToRedirect: number | null = null;
    let anyFailed = false;

    try {
      // 1. Create a new Batch
      const batchRes = await fetch("/api/checks/upload", { 
          method: "POST",
          headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!batchRes.ok) throw new Error("Failed to initialize a new batch container.");
      const { batch_id } = await batchRes.json();
      batchIdToRedirect = batch_id;

      // 2. Iterate and upload each file to extract
      for (let i = 0; i < files.length; i++) {
        // Mark current file as processing
        setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: "processing" } : f));

        const formData = new FormData();
        formData.append("file", files[i].file);

        try {
          const extractRes = await fetch(`/api/checks/extract?batch_id=${batch_id}`, {
            method: "POST",
            headers: { "Authorization": "Bearer local-dev-token" },
            body: formData,
          });

          if (!extractRes.ok) {
             const errorData = await extractRes.json().catch(() => ({ detail: "Unknown error" }));
             throw new Error(errorData.detail || `Server returned ${extractRes.status}`);
          }
          
          // Mark success
          setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: "success" } : f));
        } catch (err: unknown) {
          anyFailed = true;
          const msg = err instanceof Error ? err.message : "Extraction failed";
          // Mark error
          setFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: "error", errorMsg: msg } : f));
        }
        
        setProgress(((i + 1) / files.length) * 100);
      }

      // 3. Redirect only if everything succeeded, otherwise let them see the errors
      if (!anyFailed && batchIdToRedirect) {
        setTimeout(() => {
           router.push(`/batch/${batchIdToRedirect}`);
        }, 800);
      } else {
        setLoading(false);
      }

    } catch (err: unknown) {
      if (err instanceof Error) {
        setGlobalError(err.message || "An unexpected error occurred during batch creation.");
      } else {
        setGlobalError("An unexpected error occurred during batch creation.");
      }
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center p-6 pb-24">
      <div className="w-full max-w-2xl bg-card border border-border-custom rounded-3xl p-8 md:p-12 shadow-2xl relative overflow-hidden">
        {/* Decorative flair */}
        <div className="absolute top-[-50%] left-[-10%] w-[80%] h-[80%] bg-indigo-500/10 blur-[100px] rounded-full pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center">
            
          <div className="w-full flex justify-start mb-8">
             <Link href="/" className="flex items-center gap-2 text-slate-500 hover:text-foreground transition-colors text-sm font-medium">
                <ChevronLeft className="w-4 h-4" />
                <span>Back to Dashboard</span>
             </Link>
          </div>

          <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-6 text-indigo-500 dark:text-indigo-400">
            <Upload className="w-8 h-8" />
          </div>
          
          <h1 className="text-3xl font-bold tracking-tight mb-2 text-center text-foreground">Upload Check Files</h1>
          <p className="text-slate-500 text-center mb-10 pb-6 border-b border-border-custom w-full max-w-sm font-medium">
             Drag, drop, or select multiple PDFs or Image files to begin a new extraction batch. Duplicates are automatically skipped.
          </p>

          <div
            {...getRootProps()}
            className={cn(
              "w-full cursor-pointer rounded-2xl p-10 border-2 border-dashed transition-all duration-300 bg-black/[0.02] dark:bg-white/[0.02] text-center mb-8",
              isDragActive ? "border-indigo-500 bg-indigo-500/5 ring-4 ring-indigo-500/20" : "border-slate-300 dark:border-slate-800 hover:border-indigo-500"
            )}
            style={{ pointerEvents: loading ? 'none' : 'auto', opacity: loading ? 0.5 : 1 }}
          >
            <input {...getInputProps()} />
            <p className="text-lg font-bold text-foreground mb-1">Select Files</p>
            <p className="text-sm font-medium text-slate-500 uppercase tracking-widest">or drag & drop</p>
          </div>

          {globalError && (
             <div className="w-full p-4 mb-8 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-sm flex items-start gap-3">
               <AlertCircle className="w-5 h-5 shrink-0" />
               <span className="font-medium">{globalError}</span>
             </div>
          )}

          <AnimatePresence>
            {files.length > 0 && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="w-full space-y-4"
              >
                <div className="max-h-64 overflow-y-auto pr-2 space-y-2">
                    {files.map((item, i) => (
                    <motion.div
                        key={item.file.name + i}
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className={cn(
                          "flex items-center justify-between p-3.5 rounded-xl border transition-colors",
                          item.status === 'error' ? "bg-red-500/5 border-red-500/20" :
                          item.status === 'success' ? "bg-emerald-500/5 border-emerald-500/20" :
                          item.status === 'processing' ? "bg-indigo-500/5 border-indigo-500/20" :
                          "bg-black/5 dark:bg-white/5 border-border-custom"
                        )}
                    >
                        <div className="flex items-center gap-3 overflow-hidden">
                          <div className={cn(
                            "p-2 rounded-lg shrink-0",
                            item.status === 'error' ? "bg-red-500/10 text-red-500" :
                            item.status === 'success' ? "bg-emerald-500/10 text-emerald-500" :
                            "bg-indigo-500/10 text-indigo-500"
                          )}>
                              {item.status === 'success' ? <CheckCircle2 className="w-4 h-4" /> :
                               item.status === 'error' ? <XCircle className="w-4 h-4" /> :
                               <FileText className="w-4 h-4" />}
                          </div>
                          <div className="flex flex-col min-w-0">
                            <span className="text-sm font-medium truncate text-foreground">{item.file.name}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-slate-500">{formatBytes(item.file.size)}</span>
                              {item.errorMsg && (
                                <span className="text-xs text-red-500 truncate font-medium flex items-center gap-1">
                                  <span>•</span> {item.errorMsg}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        {!loading && item.status !== 'success' && (
                          <button 
                            onClick={() => removeFile(i)} 
                            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-500/10 transition-colors shrink-0 ml-2"
                            title="Remove file"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                        {item.status === 'processing' && (
                          <div className="w-4 h-4 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin shrink-0 mx-2" />
                        )}
                    </motion.div>
                    ))}
                </div>

                <div className="pt-4">
                  <button
                      onClick={processBatch}
                      disabled={loading || files.length === 0 || files.every(f => f.status === 'success')}
                      className="w-full py-4 px-6 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all shadow-xl shadow-indigo-500/20 flex items-center justify-center gap-2 group disabled:opacity-50 disabled:cursor-not-allowed relative overflow-hidden"
                  >
                      {loading ? (
                         <>
                            <div className="absolute top-0 left-0 h-full bg-white/20 transition-all duration-300" style={{ width: `${progress}%` }} />
                            <div className="relative z-10 flex items-center gap-3">
                               <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                               <span>Processing... {Math.round(progress)}%</span>
                            </div>
                         </>
                      ) : files.every(f => f.status === 'success') ? (
                         <>
                            <CheckCircle2 className="w-5 h-5" />
                            <span>All Files Extracted</span>
                         </>
                      ) : files.some(f => f.status === 'error') ? (
                         <>
                            <span>Retry Failed Files</span>
                            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                         </>
                      ) : (
                        <>
                            <span>Start Extraction</span>
                            <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                        </>
                      )}
                  </button>
                  
                  {!loading && files.some(f => f.status === 'success') && files.some(f => f.status === 'error') && (
                    <div className="mt-4 text-center">
                      <Link href="/" className="text-sm font-medium text-indigo-500 hover:text-indigo-600">
                        Skip failed files and go to Dashboard
                      </Link>
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
          
        </div>
      </div>
    </main>
  );
}
