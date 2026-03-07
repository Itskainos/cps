"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useTheme } from "next-themes";
import Link from "next/link";
import {
  FileText,
  CheckCircle2,
  Table as TableIcon,
  Download,
  AlertCircle,
  Moon,
  Sun,
  Eye,
  Clock,
  Search,
  Plus,
  Trash2
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Ensure matches Enum in FastAPI
type CheckStatus = "PENDING" | "MANUAL_REVIEW" | "APPROVED" | "REJECTED";

interface Batch {
  batch_id: number;
  batch_number: number;
  status: CheckStatus;
  created_by: string;
  created_at?: string;
  total_checks?: number;
  approved_checks?: number;
}

export default function Dashboard() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    fetchBatches();
  }, []);

  const fetchBatches = async () => {
    try {
      const res = await fetch("/api/checks/batches", {
          headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!res.ok) throw new Error("Failed to load batches");
      const data = await res.json();
      setBatches(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
          setError(err.message);
      } else {
          setError("Failed to load batches");
      }
    } finally {
      setLoading(false);
    }
  };

  const deleteBatch = async (batchId: number) => {
    if (!confirm(`Are you sure you want to delete Batch #${batchId}?`)) return;
    try {
      const res = await fetch(`/api/checks/batch/${batchId}`, {
        method: "DELETE",
        headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!res.ok) throw new Error("Failed to delete batch");
      setBatches(batches.filter(b => b.batch_id !== batchId));
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(err.message);
      }
    }
  };

  const handleExport = async (batchId: number, format: 'excel' | 'csv') => {
    try {
      const endpoint = format === 'csv' 
          ? `/api/checks/export/csv?batch_id=${batchId}`
          : `/api/checks/export?batch_id=${batchId}`;
          
      const res = await fetch(endpoint, {
        headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!res.ok) throw new Error("Failed to export batch");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `QuickTrack_Batch_${batchId}_Export.${format === 'csv' ? 'csv' : 'xlsx'}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert("Export failed: " + err.message);
      }
    }
  };

  const getStatusColor = (status: CheckStatus) => {
    switch (status) {
      case "APPROVED": return "bg-emerald-500/10 text-emerald-500 border-emerald-500/20";
      case "MANUAL_REVIEW": return "bg-amber-500/10 text-amber-500 border-amber-500/20";
      case "REJECTED": return "bg-red-500/10 text-red-500 border-red-500/20";
      default: return "bg-slate-500/10 text-slate-500 border-slate-500/20";
    }
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

      <div className="relative max-w-6xl mx-auto px-6 py-12 md:py-24 space-y-12">
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-end justify-between gap-6">
          <div>
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-500 dark:text-indigo-400 text-sm font-medium mb-4"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>AI Extraction System</span>
            </motion.div>
            <motion.h1
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="text-4xl md:text-5xl font-bold tracking-tight mb-2 bg-clip-text text-transparent bg-gradient-to-b from-foreground to-slate-400 dark:to-slate-500"
            >
              Batch Dashboard
            </motion.h1>
            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-slate-600 dark:text-slate-400 font-medium"
            >
              Manage, review, and export check data batches.
            </motion.p>
          </div>
          
          <motion.div 
             initial={{ opacity: 0, scale: 0.9 }}
             animate={{ opacity: 1, scale: 1 }}
             transition={{ delay: 0.3 }}
          >
            <Link 
              href="/upload" 
              className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold transition-all shadow-lg shadow-indigo-500/20 group"
            >
              <Plus className="w-5 h-5 group-hover:scale-110 transition-transform" />
              <span>New Batch</span>
            </Link>
          </motion.div>
        </header>

        {/* Stats / Overview (Optional) */}
        
        {/* Table Section */}
        <motion.div
           initial={{ opacity: 0, y: 40 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.4 }}
           className="bg-card border border-border-custom rounded-3xl overflow-hidden backdrop-blur-md shadow-2xl min-h-[400px] flex flex-col"
        >
          <div className="p-6 border-b border-border-custom flex items-center justify-between bg-card/40">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-500">
                <TableIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-foreground tracking-tight">Recent Batches</h3>
              </div>
            </div>
            {/* Search or Filter could go here */}
            <div className="relative hidden md:block">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search batches..." 
                className="pl-9 pr-4 py-2 bg-black/5 dark:bg-white/5 border border-border-custom rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all w-64 text-foreground"
              />
            </div>
          </div>

          <div className="flex-1 overflow-x-auto">
            {loading ? (
               <div className="flex flex-col items-center justify-center h-64 opacity-50">
                  <div className="w-8 h-8 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
                  <p className="font-medium text-slate-500">Loading batches...</p>
               </div>
            ) : error ? (
                <div className="flex items-center justify-center h-64 text-red-500 gap-2">
                   <AlertCircle className="w-5 h-5" />
                   <span>{error}</span>
                </div>
            ) : batches.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-border-custom bg-black/[0.02] dark:bg-white/[0.02]">
                    <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Batch ID</th>
                    <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Status</th>
                    <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Created</th>
                    <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider">Progress</th>
                    <th className="px-6 py-4 text-xs font-bold uppercase text-slate-500 dark:text-slate-400 tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-custom">
                  {batches.map((batch) => (
                    <tr
                      key={batch.batch_id}
                      className="group hover:bg-black/[0.01] dark:hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                           <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold">
                             #{batch.batch_number ?? batch.batch_id}
                           </div>
                           <div className="flex flex-col">
                              <span className="text-sm font-bold text-foreground">Upload Batch {batch.batch_number ?? batch.batch_id}</span>
                              <span className="text-xs text-slate-500">by {batch.created_by}</span>
                           </div>
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide uppercase border",
                          getStatusColor(batch.status)
                        )}>
                          {batch.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-5">
                         <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400">
                           <Clock className="w-4 h-4" />
                           <span>{batch.created_at ? new Date(batch.created_at).toLocaleDateString() : 'N/A'}</span>
                         </div>
                      </td>
                      <td className="px-6 py-5">
                         {batch.total_checks ? (
                             <div className="flex items-center gap-3 w-48">
                               <div className="flex-1 h-2 bg-black/5 dark:bg-white/10 rounded-full overflow-hidden">
                                 <div 
                                    className={cn(
                                      "h-full rounded-full transition-all duration-1000",
                                      batch.approved_checks === batch.total_checks ? "bg-emerald-500" : "bg-indigo-500"
                                    )}
                                    style={{ width: `${(batch.approved_checks! / batch.total_checks) * 100}%` }}
                                 />
                               </div>
                               <span className="text-xs font-medium text-slate-500 w-12 text-right">
                                 {batch.approved_checks} / {batch.total_checks}
                               </span>
                             </div>
                         ) : (
                           <span className="text-xs text-slate-500 italic">Processing...</span>
                         )}
                      </td>
                      <td className="px-6 py-5 text-right">
                        <div className="flex items-center justify-end gap-2 transition-opacity">
                          <button
                            title="Export to Excel"
                            onClick={() => handleExport(batch.batch_id, 'excel')}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold rounded-xl transition-all bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20"
                          >
                            <Download className="w-4 h-4" />
                            <span>Export</span>
                          </button>
                          
                          <Link 
                            href={`/batch/${batch.batch_id}`}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold rounded-xl transition-all bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20"
                            title="Review Batch"
                          >
                            <Eye className="w-4 h-4" />
                            <span>Review</span>
                          </Link>
                        
                          <button
                            title="Delete Batch"
                            onClick={() => deleteBatch(batch.batch_id)}
                            className="flex items-center gap-2 p-2 text-sm font-medium rounded-xl transition-all bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-center p-12 opacity-60">
                <FileText className="w-12 h-12 mb-4 text-slate-400" />
                <p className="text-lg text-foreground font-medium">No Batches Found</p>
                <p className="text-sm text-slate-500 mt-1 max-w-sm">
                  Upload new check PDFs to extract their data and start managing routing and account numbers securely.
                </p>
              </div>
            )}
          </div>
        </motion.div>
      </div>
    </main>
  );
}
