"use client";

import { useState, useEffect, useMemo } from "react";
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
  Trash2,
  Activity,
  CheckSquare,
  ClipboardList,
  ChevronLeft,
  ChevronRight
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

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

interface Stats {
  total_batches: number;
  pending_checks: number;
  review_checks: number;
  approved_today: number;
}

export default function Dashboard() {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  // Filtering & Pagination
  const [searchQuery, setSearchQuery] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  useEffect(() => {
    setMounted(true);
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch stats
      const statsRes = await fetch("/api/checks/stats", {
          headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }

      // Fetch batches (currently fetching all for client-side search, but backend supports pagination if we need server-side search later)
      const res = await fetch("/api/checks/batches?skip=0&limit=1000", {
          headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!res.ok) throw new Error("Failed to load batches");
      const data = await res.json();
      setBatches(data.batches || []);
    } catch (err: unknown) {
      if (err instanceof Error) setError(err.message);
      else setError("Failed to load batches");
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
      fetchData(); // Refresh stats
    } catch (err: unknown) {
      if (err instanceof Error) alert(err.message);
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
      if (err instanceof Error) alert("Export failed: " + err.message);
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

  // Derived state for filtering and pagination
  const filteredBatches = useMemo(() => {
    if (!searchQuery) return batches;
    const lowerQuery = searchQuery.toLowerCase();
    return batches.filter(batch => 
      batch.batch_number?.toString().includes(lowerQuery) ||
      batch.created_by?.toLowerCase().includes(lowerQuery) ||
      batch.status?.toLowerCase().includes(lowerQuery)
    );
  }, [batches, searchQuery]);

  const totalPages = Math.ceil(filteredBatches.length / itemsPerPage);
  
  const currentBatches = useMemo(() => {
    const start = (currentPage - 1) * itemsPerPage;
    return filteredBatches.slice(start, start + itemsPerPage);
  }, [filteredBatches, currentPage, itemsPerPage]);

  // Reset page when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  if (!mounted) return <div className="min-h-screen bg-background" />;

  return (
    <main className="min-h-screen bg-background text-foreground selection:bg-indigo-500/30">
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

      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-500/10 blur-[120px] rounded-full dark:opacity-100 opacity-40" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-blue-500/10 blur-[120px] rounded-full dark:opacity-100 opacity-40" />
      </div>

      <div className="relative max-w-6xl mx-auto px-6 py-12 md:py-24 space-y-12">
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

        {/* Stats Row */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="bg-card border border-border-custom rounded-3xl p-6 flex flex-col shadow-lg backdrop-blur-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-500">
                <ClipboardList className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-slate-500">Total Batches</h3>
            </div>
            <p className="text-4xl font-bold tracking-tight">{stats?.total_batches ?? "-"}</p>
          </div>
          
          <div className="bg-card border border-border-custom rounded-3xl p-6 flex flex-col shadow-lg backdrop-blur-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-amber-500/10 text-amber-500">
                <Activity className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-slate-500">Checks Pending Review</h3>
            </div>
            <p className="text-4xl font-bold tracking-tight text-amber-600 dark:text-amber-400">
              {(stats?.review_checks ?? 0) + (stats?.pending_checks ?? 0) || "-"}
            </p>
          </div>

          <div className="bg-card border border-border-custom rounded-3xl p-6 flex flex-col shadow-lg backdrop-blur-md">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-500">
                <CheckSquare className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-slate-500">Approved Today</h3>
            </div>
            <p className="text-4xl font-bold tracking-tight text-emerald-600 dark:text-emerald-400">
              {stats?.approved_today ?? "-"}
            </p>
          </div>
        </motion.div>

        {/* Table Section */}
        <motion.div
           initial={{ opacity: 0, y: 40 }}
           animate={{ opacity: 1, y: 0 }}
           transition={{ delay: 0.4 }}
           className="bg-card border border-border-custom rounded-3xl overflow-hidden backdrop-blur-md shadow-2xl min-h-[400px] flex flex-col"
        >
          <div className="p-6 border-b border-border-custom flex flex-col md:flex-row md:items-center justify-between bg-card/40 gap-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-500">
                <TableIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-lg text-foreground tracking-tight">Recent Batches</h3>
              </div>
            </div>
            <div className="relative w-full md:w-auto">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search by ID, status, or creator..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 bg-black/5 dark:bg-white/5 border border-border-custom rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all w-full md:w-72 text-foreground"
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
            ) : currentBatches.length > 0 ? (
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
                  {currentBatches.map((batch) => (
                    <tr
                      key={batch.batch_id}
                      className="group hover:bg-black/[0.01] dark:hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-3">
                           <div className="w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-600 dark:text-indigo-400 font-bold shrink-0">
                             #{batch.batch_number ?? batch.batch_id}
                           </div>
                           <div className="flex flex-col min-w-0">
                              <span className="text-sm font-bold text-foreground truncate">Upload Batch {batch.batch_number ?? batch.batch_id}</span>
                              <span className="text-xs text-slate-500 truncate">by {batch.created_by}</span>
                           </div>
                        </div>
                      </td>
                      <td className="px-6 py-5 whitespace-nowrap">
                        <span className={cn(
                          "inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wide uppercase border",
                          getStatusColor(batch.status)
                        )}>
                          {batch.status.replace("_", " ")}
                        </span>
                      </td>
                      <td className="px-6 py-5 whitespace-nowrap">
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
                      <td className="px-6 py-5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2 transition-opacity">
                          <button
                            title="Export to Excel"
                            onClick={() => handleExport(batch.batch_id, 'excel')}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold rounded-xl transition-all bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20"
                          >
                            <Download className="w-4 h-4" />
                            <span className="hidden sm:inline">Export</span>
                          </button>
                          
                          <Link 
                            href={`/batch/${batch.batch_id}`}
                            className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold rounded-xl transition-all bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 hover:bg-indigo-500/20 border border-indigo-500/20"
                            title="Review Batch"
                          >
                            <Eye className="w-4 h-4" />
                            <span className="hidden sm:inline">Review</span>
                          </Link>
                        
                          <button
                            title="Delete Batch"
                            onClick={() => deleteBatch(batch.batch_id)}
                            className="flex items-center gap-2 p-2.5 text-sm font-medium rounded-xl transition-all bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20"
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
                  {searchQuery ? "Try adjusting your search query." : "Upload new check PDFs to extract their data and start managing routing and account numbers securely."}
                </p>
              </div>
            )}
          </div>
          
          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="p-4 border-t border-border-custom bg-black/[0.02] dark:bg-white/[0.02] flex items-center justify-between">
              <span className="text-sm text-slate-500 font-medium ml-4">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredBatches.length)} of {filteredBatches.length}
              </span>
              <div className="flex gap-2">
                <button 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <button 
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg hover:bg-black/5 dark:hover:bg-white/10 disabled:opacity-50 transition-colors"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </main>
  );
}
