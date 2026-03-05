
"use client";

import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "next-themes";
import {
  FileText,
  Upload,
  X,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Table as TableIcon,
  Download,
  CreditCard,
  Banknote,
  Navigation,
  Moon,
  Sun
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface ChequeData {
  Date: string;
  Cheque_No: string;
  Payee: string;
  Amount: string;
  Memo: string;
  Bank: string;
  Routing_No: string;
  Account_No: string;
  ai_enhanced?: boolean;
  confidence?: Record<string, number>;
}

function ConfidenceDot({ score }: { score?: number }) {
  if (score === undefined) return null;
  const color = score >= 0.9 ? "bg-emerald-400" : score >= 0.7 ? "bg-amber-400" : "bg-red-400";
  const label = score >= 0.9 ? "High" : score >= 0.7 ? "Medium" : "Low";
  return (
    <span title={`AI Confidence: ${label} (${Math.round(score * 100)}%)`}
      className={`inline-block w-2 h-2 rounded-full ${color} ml-1 cursor-help`} />
  );
}

export default function Home() {
  const [files, setFiles] = useState<File[]>([]);
  const [results, setResults] = useState<ChequeData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
  });

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const processFiles = async () => {
    if (files.length === 0) return;

    setLoading(true);
    setError(null);
    const newResults: ChequeData[] = [];

    try {
      for (const file of files) {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch("/api/extract", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`Failed to process ${file.name}`);
        }

        const data = await response.json();
        if (Array.isArray(data)) {
          newResults.push(...data);
        } else {
          newResults.push(data);
        }
      }
      setResults(prev => [...prev, ...newResults]);
      setFiles([]); // Clear pending files
    } catch (err: any) {
      setError(err.message || "Something went wrong during extraction.");
    } finally {
      setLoading(false);
    }
  };

  const downloadCSV = () => {
    if (results.length === 0) return;
    const headers = ["Date", "Cheque_No", "Payee", "Amount", "Memo", "Bank", "Routing_No", "Account_No"];
    const csvContent = [
      headers.join(","),
      ...results.map(row =>
        headers.map(h => `"${(row as any)[h] || ""}"`).join(",")
      )
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "extracted_cheques.csv");
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!mounted) {
    return <div className="min-h-screen bg-background" />;
  }

  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-indigo-500/30">
      {/* Theme Toggle */}
      <div className="fixed top-8 right-8 z-50">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="p-3 rounded-2xl bg-card border border-border-custom shadow-xl hover:scale-110 transition-transform duration-300 group"
        >
          {theme === "dark" ? (
            <Sun className="w-5 h-5 text-amber-400 group-hover:rotate-45 transition-transform duration-500" />
          ) : (
            <Moon className="w-5 h-5 text-indigo-600" />
          )}
        </button>
      </div>

      {/* Background decoration */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full dark:opacity-100 opacity-40" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full dark:opacity-100 opacity-40" />
      </div>

      <div className="relative max-w-6xl mx-auto px-6 py-12 md:py-24">
        {/* Header */}
        <header className="mb-16 text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 dark:text-indigo-400 text-sm font-medium mb-4"
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>Next-Gen Zonal OCR Powered</span>
          </motion.div>
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-7xl font-bold tracking-tight mb-4 bg-clip-text text-transparent bg-gradient-to-b from-foreground to-slate-400 dark:to-slate-500"
          >
            Cheque Printing System
          </motion.h1>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-lg text-slate-800 dark:text-slate-400 max-w-2xl mx-auto font-medium"
          >
            Extract routing numbers, account numbers, and payee details with high-accuracy coordinate scanning.
          </motion.p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Uploader Section */}
          <div className="lg:col-span-12 xl:col-span-5 space-y-6">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="p-1 rounded-3xl bg-gradient-to-br from-indigo-500/20 via-border-custom to-blue-500/20 border border-border-custom shadow-2xl backdrop-blur-xl"
            >
              <div
                {...getRootProps()}
                className={cn(
                  "relative group cursor-pointer rounded-[22px] bg-card p-12 border-2 border-dashed transition-all duration-300",
                  isDragActive ? "border-indigo-500 bg-indigo-500/5" : "border-slate-300 dark:border-slate-800 hover:border-indigo-500"
                )}
              >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center justify-center text-center">
                  <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                    <Upload className="w-8 h-8 text-indigo-500 dark:text-indigo-400" />
                  </div>
                  <h3 className="text-xl font-bold mb-2 text-foreground">Upload Cheque PDFs</h3>
                  <p className="text-slate-700 dark:text-slate-500 text-sm font-semibold uppercase tracking-wider">Drag and drop or click to select files</p>
                </div>
              </div>
            </motion.div>

            {/* File List */}
            <AnimatePresence>
              {files.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-3"
                >
                  <div className="flex items-center justify-between px-2">
                    <h4 className="text-sm font-bold text-slate-800 dark:text-slate-400 italic">Pending Batch</h4>
                    <span className="text-xs text-indigo-600 dark:text-indigo-400 font-mono font-bold">{files.length} Files</span>
                  </div>
                  {files.map((file, i) => (
                    <motion.div
                      key={file.name + i}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className="flex items-center justify-between p-3 rounded-xl bg-card border border-border-custom shadow-sm"
                    >
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-red-500/10 text-red-500">
                          <FileText className="w-4 h-4" />
                        </div>
                        <span className="text-sm font-medium truncate max-w-[200px] text-foreground">{file.name}</span>
                      </div>
                      <button onClick={() => removeFile(i)} className="p-1.5 rounded-lg hover:bg-black/5 dark:hover:bg-white/5 text-slate-500 hover:text-foreground transition-colors">
                        <X className="w-4 h-4" />
                      </button>
                    </motion.div>
                  ))}
                  <button
                    onClick={processFiles}
                    disabled={loading}
                    className="w-full py-4 px-6 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2 group disabled:opacity-50"
                  >
                    {loading ? (
                      <div className="flex items-center gap-3">
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Scanning Zones...</span>
                      </div>
                    ) : (
                      <>
                        <span>Extract Batch</span>
                        <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                      </>
                    )}
                  </button>
                </motion.div>
              )}
            </AnimatePresence>

            {error && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 dark:text-red-400 text-sm flex items-start gap-3">
                <AlertCircle className="w-5 h-5 shrink-0" />
                <span>{error}</span>
              </motion.div>
            )}
          </div>

          {/* Results Table Section */}
          <div className="lg:col-span-12 xl:col-span-7">
            <div className="bg-card border border-border-custom rounded-3xl overflow-hidden backdrop-blur-md shadow-2xl min-h-[500px] flex flex-col transition-colors duration-300">
              <div className="p-6 border-b border-border-custom flex items-center justify-between bg-card/40">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-500">
                    <TableIcon className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg text-foreground tracking-tight">Extracted Data</h3>
                    <p className="text-xs text-slate-800 dark:text-slate-500 font-bold uppercase tracking-widest">Validated Records</p>
                  </div>
                </div>
                {results.length > 0 && (
                  <button
                    onClick={downloadCSV}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-sm font-medium transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>Export CSV</span>
                  </button>
                )}
              </div>

              <div className="flex-1 overflow-x-auto">
                <AnimatePresence mode="wait">
                  {results.length > 0 ? (
                    <motion.table
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="w-full text-left border-collapse"
                    >
                      <thead>
                        <tr className="border-b border-border-custom bg-black/[0.02] dark:bg-white/[0.02]">
                          <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Cheque Details</th>
                          <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Recipient & Value</th>
                          <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">
                            MICR Footer
                            {results.some(r => r.ai_enhanced) && (
                              <span className="ml-2 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-500 dark:text-violet-400 text-[9px] font-bold tracking-wide normal-case">
                                ✦ AI
                              </span>
                            )}
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-custom">
                        {results.map((row, i) => (
                          <motion.tr
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.05 }}
                            className="group hover:bg-black/[0.01] dark:hover:bg-white/[0.02] transition-colors"
                          >
                            <td className="px-6 py-6 border-l-4 border-l-transparent group-hover:border-l-indigo-500 transition-all">
                              <div className="flex flex-col gap-1">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-bold text-foreground">#{row.Cheque_No}</span>
                                  {row.ai_enhanced && (
                                    <span className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-violet-500/10 text-violet-500 dark:text-violet-400 text-[9px] font-bold tracking-wide">
                                      ✦ AI
                                    </span>
                                  )}
                                </div>
                                <span className="text-xs text-slate-500">{row.Date} | {row.Bank}</span>
                                {row.Memo && <span className="text-[10px] text-indigo-500 dark:text-indigo-400 font-semibold italic">M: {row.Memo}</span>}
                              </div>
                            </td>
                            <td className="px-6 py-6">
                              <div className="flex flex-col gap-1">
                                <span className="text-sm font-medium text-indigo-600 dark:text-indigo-300">{row.Payee}</span>
                                <div className="flex items-center gap-1.5">
                                  <Banknote className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                                  <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 tracking-wide">${row.Amount}</span>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-6">
                              <div className="space-y-2">
                                <div className="flex items-center gap-2">
                                  <div className="flex flex-col">
                                    <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold tracking-tighter uppercase">ROUTING</span>
                                    <div className="flex items-center">
                                      <span className="text-xs font-mono text-slate-700 dark:text-slate-300">{row.Routing_No}</span>
                                      <ConfidenceDot score={row.confidence?.Routing_No} />
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  <div className="flex flex-col">
                                    <span className="text-[9px] text-slate-400 dark:text-slate-500 font-bold tracking-tighter uppercase">ACCOUNT</span>
                                    <div className="flex items-center">
                                      <span className="text-xs font-mono text-slate-700 dark:text-slate-300">{row.Account_No}</span>
                                      <ConfidenceDot score={row.confidence?.Account_No} />
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </motion.table>
                  ) : (
                    <div className="flex flex-col items-center justify-center h-full text-center p-12 opacity-30 dark:opacity-50">
                      <FileText className="w-16 h-16 mb-4 text-slate-400 dark:text-slate-800" />
                      <p className="text-lg text-foreground font-medium">Awaiting Input</p>
                      <p className="text-sm text-slate-500">Upload cheque PDFs to start extraction</p>
                    </div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-24 border-t border-border-custom py-12 text-center text-slate-500 text-xs font-medium">
        &copy; 2026 Cheque Printing System (CPS).
      </footer>
    </main>
  );
}
