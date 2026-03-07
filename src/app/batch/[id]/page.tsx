"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  AlertCircle,
  Save,
  Image as ImageIcon,
  FileText,
  Moon,
  Sun,
  XCircle,
  LayoutGrid,
  Download,
  Banknote
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type CheckStatus = "PENDING" | "MANUAL_REVIEW" | "APPROVED" | "REJECTED";

interface Check {
  id: number;
  check_number: string | null;
  check_date: string | null;
  store_name: string | null;
  payee: string | null;
  amount: number | null;
  memo: string | null;
  bank_name?: string | null;
  routing_number?: string | null;
  account_number?: string | null;
  status: CheckStatus;
  confidence_score: number | null;
  validation_notes: string | null;
  s3_image_url?: string;
}

interface BatchDetails {
  batch_id: number;
  batch_number?: number;
  status: CheckStatus;
  created_by: string;
  checks: Check[];
}

export default function ReviewPage() {
  const { id } = useParams();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  
  const [batch, setBatch] = useState<BatchDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [currentIndex, setCurrentIndex] = useState(0);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [showReviewAnyway, setShowReviewAnyway] = useState(false);

  // Form State for current Check
  const [editForm, setEditForm] = useState<{
      store_name: string;
      check_number: string;
      check_date: string;
      payee: string;
      amount: string;
      memo: string;
      bank_name: string;
      routing_number: string;
      account_number: string;
      status: string;
  }>({
      store_name: "", 
      check_number: "",
      check_date: "",
      payee: "", 
      amount: "", 
      memo: "", 
      bank_name: "", 
      routing_number: "",
      account_number: "",
      status: "APPROVED"
  });

  useEffect(() => {
    fetchBatchDetails();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (batch && batch.checks.length > 0) {
        const currentCheck = batch.checks[currentIndex];
        setEditForm({
            store_name: currentCheck.store_name || "",
            check_number: currentCheck.check_number || "",
            check_date: currentCheck.check_date || "",
            payee: currentCheck.payee || "",
            amount: currentCheck.amount ? currentCheck.amount.toString() : "",
            memo: currentCheck.memo || "",
            bank_name: currentCheck.bank_name || "",
            routing_number: currentCheck.routing_number || "",
            account_number: currentCheck.account_number || "",
            status: currentCheck.status
        });
        setSaveSuccess(false);
    }
  }, [currentIndex, batch]);

  const fetchBatchDetails = async () => {
    try {
        const res = await fetch(`/api/checks/batch/${id}`, {
            headers: { "Authorization": "Bearer local-dev-token" }
        });
        if (!res.ok) throw new Error("Failed to load batch data");
        const data = await res.json();
        
        setBatch(data);
        setLoading(false);
        
    } catch (err: unknown) {
        if (err instanceof Error) {
           setError(err.message);
        } else {
           setError("Failed to load batch data");
        }
        setLoading(false);
    }
  };

  const currentCheck = batch?.checks[currentIndex];

  const handleSave = async (status: CheckStatus) => {
      if (!currentCheck) return;
      setSaving(true);
      setSaveSuccess(false);

      try {
          const res = await fetch(`/api/checks/${currentCheck.id}`, {
              method: "PATCH",
              headers: { 
                  "Content-Type": "application/json",
                  "Authorization": "Bearer local-dev-token"
              },
              body: JSON.stringify({
                  status,
                  store_name: editForm.store_name,
                  check_number: editForm.check_number,
                  check_date: editForm.check_date,
                  payee: editForm.payee,
                  amount: parseFloat(editForm.amount) || null,
                  memo: editForm.memo,
                  bank_name: editForm.bank_name,
                  routing_number: editForm.routing_number,
                  account_number: editForm.account_number
              })
          });

          if (!res.ok) {
              const errorData = await res.json();
              throw new Error(errorData.detail || "Failed to update check");
          }

          // Update local state to reflect changes
          setBatch(prev => {
              if (!prev) return prev;
              const newChecks = [...prev.checks];
              newChecks[currentIndex] = {
                  ...newChecks[currentIndex],
                  status,
                  store_name: editForm.store_name,
                  check_number: editForm.check_number,
                  check_date: editForm.check_date,
                  payee: editForm.payee,
                  amount: parseFloat(editForm.amount) || null,
                  memo: editForm.memo,
                  bank_name: editForm.bank_name,
                  routing_number: editForm.routing_number,
                  account_number: editForm.account_number
              };
              return { ...prev, checks: newChecks };
          });

          setSaveSuccess(true);
          setTimeout(() => setSaveSuccess(false), 3000);

          // Auto advance if there are more
          if (currentIndex < batch!.checks.length - 1) {
              setCurrentIndex(currentIndex + 1);
          }

      } catch (err: unknown) {
          if (err instanceof Error) {
             alert(err.message);
          }
      } finally {
          setSaving(false);
      }
  };

  const handleExportCSV = async () => {
    try {
      const res = await fetch(`/api/checks/export/csv?batch_id=${batch?.batch_id}`, {
        headers: { "Authorization": "Bearer local-dev-token" }
      });
      if (!res.ok) throw new Error("Failed to export batch");
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `QuickTrack_Batch_${batch?.batch_id}_Export.csv`;
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

  if (loading) {
      return (
          <div className="min-h-screen bg-background flex flex-col items-center justify-center">
              <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
              <p className="font-medium text-slate-500">Loading Batch Details...</p>
          </div>
      );
  }

  if (error || !batch || batch.checks.length === 0) {
      return (
          <div className="min-h-screen bg-background flex flex-col items-center justify-center p-6 text-center">
              <div className="p-4 rounded-full bg-red-500/10 mb-6">
                <AlertCircle className="w-12 h-12 text-red-500" />
              </div>
              <h2 className="text-3xl font-bold text-foreground mb-3">No Records Found</h2>
              <p className="text-slate-500 mb-8 max-w-md">
                  {error || "This batch appears to be empty. This typically happens if an error occurred during the initial PDF extraction."}
              </p>
              <div className="flex flex-col sm:flex-row gap-4">
                <Link href="/upload" className="px-8 py-3 bg-indigo-600 text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20">
                    Start New Batch
                </Link>
                <Link href="/" className="px-8 py-3 bg-card border border-border-custom text-foreground font-bold rounded-2xl hover:bg-black/5 dark:hover:bg-white/5 transition-all">
                    Back to Dashboard
                </Link>
              </div>
          </div>
      );
  }

   // If ALL checks are PROCESSED (APPROVED or REJECTED), show the Validated Records Summary Table instead of Split Screen
   // Unless they clicked "Re-Review"
   const allProcessed = batch.checks.every(c => c.status === "APPROVED" || c.status === "REJECTED");
   
   if (allProcessed && !showReviewAnyway) {
       return (
           <main className="min-h-screen bg-[#04060A] text-slate-300 p-8 flex flex-col items-center selection:bg-indigo-500/30">
              
              <div className="w-full max-w-5xl mb-6 flex items-center justify-between">
                   <Link href="/" className="mb-4 text-xs font-bold text-[#565C68] hover:text-indigo-400 transition-colors flex items-center gap-2 uppercase tracking-widest">
                       <ChevronLeft className="w-4 h-4" /> Back to Dashboard
                   </Link>
                   <div className={cn(
                       "px-4 py-1.5 rounded-full border text-[10px] font-bold uppercase tracking-widest flex items-center gap-2",
                       batch.checks.every(c => c.status === "APPROVED") 
                        ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500" 
                        : "bg-amber-500/10 border-amber-500/20 text-amber-500"
                   )}>
                        {batch.checks.every(c => c.status === "APPROVED") ? (
                            <><CheckCircle2 className="w-3.5 h-3.5" /> Batch Fully Approved</>
                        ) : (
                            <><AlertCircle className="w-3.5 h-3.5" /> Batch Processed with Rejections</>
                        )}
                   </div>
               </div>

               <div className="w-full max-w-5xl bg-[#0B101A] border border-white/5 rounded-2xl overflow-hidden shadow-2xl">
                   {/* Success Banner */}
                   <div className={cn(
                       "w-full border-b p-4 flex items-center justify-center gap-3",
                       batch.checks.every(c => c.status === "APPROVED") 
                        ? "bg-emerald-500/5 border-emerald-500/10" 
                        : "bg-amber-500/5 border-amber-500/10"
                   )}>
                       <div className={cn(
                           "w-8 h-8 rounded-full flex items-center justify-center",
                           batch.checks.every(c => c.status === "APPROVED") ? "bg-emerald-500" : "bg-amber-500"
                       )}>
                           {batch.checks.every(c => c.status === "APPROVED") ? (
                               <CheckCircle2 className="w-5 h-5 text-white" />
                           ) : (
                               <XCircle className="w-5 h-5 text-white" />
                           )}
                       </div>
                       <div className="flex flex-col">
                           <span className="text-sm font-bold text-white leading-tight">Batch Processed Successfully</span>
                           <span className="text-xs text-slate-500">
                               {batch.checks.every(c => c.status === "APPROVED") 
                                ? "All records have been validated and are ready for export." 
                                : "Validation complete. Some records were rejected and excluded from totals."}
                           </span>
                       </div>
                   </div>

                   <div className="p-6 md:p-8 flex flex-row items-center justify-between border-b border-white/5 text-white">
                       <div className="flex items-center gap-4">
                           <div className="p-3 bg-indigo-500/10 rounded-xl">
                               <LayoutGrid className="w-6 h-6 text-indigo-500" />
                           </div>
                           <div>
                               <h1 className="text-xl font-bold">Extracted Data</h1>
                               <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mt-1">
                                   {batch.checks.filter(c => c.status === "APPROVED").length} Approved / {batch.checks.length} Total
                               </p>
                           </div>
                       </div>
                       <div className="flex items-center gap-3">
                           <button 
                              onClick={() => setShowReviewAnyway(true)}
                              className="px-4 py-2.5 bg-white/5 hover:bg-white/10 text-slate-300 text-xs font-bold rounded-xl transition-all"
                           >
                              Edit Data
                           </button>
                           <button 
                              onClick={handleExportCSV}
                              className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold rounded-xl transition-all shadow-lg shadow-emerald-500/20"
                           >
                              <Download className="w-4 h-4" />
                              Download Report
                           </button>
                       </div>
                   </div>

                  <div className="grid grid-cols-3 gap-4 px-8 py-4 bg-white/[0.02] border-b border-white/5 text-[11px] font-bold uppercase tracking-widest text-[#565C68]">
                      <div>Cheque Details</div>
                      <div>Recipient & Value</div>
                      <div>MICR Footer</div>
                  </div>

                  <div className="divide-y divide-white/5">
                      {batch.checks.map(check => (
                          <div key={check.id} className={cn(
                              "grid grid-cols-3 gap-4 px-8 py-6 hover:bg-white/[0.02] transition-colors relative",
                              check.status === "REJECTED" && "opacity-50 grayscale"
                          )}>
                              <div className="flex flex-col gap-1.5 justify-center">
                                  <div className="flex items-center gap-2">
                                      <span className="text-base font-bold text-white">#{check.check_number || "N/A"}</span>
                                      <span className={cn(
                                          "px-2 py-0.5 rounded text-[8px] font-black uppercase tracking-tighter",
                                          check.status === "APPROVED" ? "bg-emerald-500/20 text-emerald-500" : "bg-red-500/20 text-red-500"
                                      )}>
                                          {check.status}
                                      </span>
                                  </div>
                                  <span className="text-sm text-[#565C68] font-medium">{check.check_date || "N/A"} | {check.bank_name || "N/A"}</span>
                                  <span className="text-sm italic text-indigo-400 font-medium">M: {check.memo || "N/A"}</span>
                              </div>
                              
                              <div className="flex flex-col gap-1.5 justify-center">
                                  <span className="text-sm text-indigo-300 font-bold">{check.payee || "N/A"}</span>
                                  <span className="text-xl font-bold text-emerald-500 flex items-center gap-1.5">
                                      <Banknote className="w-5 h-5 opacity-80" />
                                      ${check.amount ? check.amount.toFixed(2) : "0.00"}
                                  </span>
                              </div>

                              <div className="flex flex-col gap-3 justify-center">
                                  <div className="flex flex-col">
                                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#565C68] mb-0.5">Routing</span>
                                      <span className="text-sm font-medium text-slate-300 tracking-wider">{check.routing_number || "N/A"}</span>
                                  </div>
                                  <div className="flex flex-col">
                                      <span className="text-[10px] font-bold uppercase tracking-widest text-[#565C68] mb-0.5">Account</span>
                                      <span className="text-sm font-medium text-slate-300 tracking-wider">{check.account_number || "N/A"}</span>
                                  </div>
                              </div>
                          </div>
                      ))}
                  </div>
             </div>
          </main>
      );
  }

  return (
    <main className="min-h-screen bg-background text-foreground flex flex-col h-screen overflow-hidden selection:bg-indigo-500/30">
      {/* Top Navigation Bar */}
      <header className="flex-shrink-0 h-16 border-b border-border-custom bg-card flex items-center justify-between px-6 z-20">
          <div className="flex items-center gap-4">
              <Link href="/" className="p-2 -ml-2 rounded-xl hover:bg-black/5 dark:hover:bg-white/5 text-slate-500 transition-colors">
                  <ChevronLeft className="w-5 h-5" />
              </Link>
              <div className="flex flex-col">
                  <span className="text-sm font-bold text-foreground leading-tight">Batch #{batch.batch_number ?? batch.batch_id} Review</span>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{currentIndex + 1} of {batch.checks.length} Checks</span>
              </div>
          </div>

          <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentIndex(Math.max(0, currentIndex - 1))}
                disabled={currentIndex === 0}
                className="p-2 rounded-xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 disabled:opacity-30 transition-colors"
              >
                  <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={() => setCurrentIndex(Math.min(batch.checks.length - 1, currentIndex + 1))}
                disabled={currentIndex === batch.checks.length - 1}
                className="p-2 rounded-xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 disabled:opacity-30 transition-colors"
              >
                  <ChevronRight className="w-4 h-4" />
              </button>

              <div className="w-px h-6 bg-border-custom mx-2" />

              <button
                onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
                className="p-2 rounded-xl bg-black/5 dark:bg-white/5 hover:bg-black/10 dark:hover:bg-white/10 transition-colors text-slate-500"
              >
                {theme === "dark" ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
              </button>
          </div>
      </header>

      {/* Main Split Screen Area */}
      <div className="flex-1 flex flex-col md:flex-row overflow-hidden">
          
          {/* Left Side: Check Image Viewer */}
          <div className="flex-1 bg-black/5 dark:bg-[#0a0a0a] border-r border-border-custom relative flex flex-col">
             {currentCheck?.s3_image_url ? (
                 <div className="flex-1 w-full h-full flex flex-col items-center justify-center p-4 md:p-8 bg-black/5 dark:bg-white/5 overflow-hidden">
                     {currentCheck.s3_image_url.toLowerCase().endsWith('.pdf') ? (
                         <iframe 
                             src={currentCheck.s3_image_url} 
                             className="w-full h-full rounded-xl shadow-2xl border border-border-custom bg-white"
                             title="Check Scan PDF"
                         />
                     ) : (
                         <img 
                            src={currentCheck.s3_image_url} 
                            alt="Check Scan" 
                            className="max-w-full h-auto max-h-full rounded-xl shadow-2xl border border-border-custom object-contain bg-white" 
                         />
                     )}
                 </div>
             ) : (
                 <div className="flex-1 w-full h-full flex flex-col items-center justify-center text-slate-400 p-8">
                     <ImageIcon className="w-16 h-16 mb-4 opacity-50" />
                     <p className="font-medium">Image Not Available</p>
                     <p className="text-xs mt-1">S3 Image mock URL was not provided for this check.</p>
                 </div>
             )}
             
             {/* Confidence Banner Overlay */}
             {currentCheck?.status === "MANUAL_REVIEW" && (
                 <div className="absolute top-4 left-4 right-4 bg-amber-500/90 backdrop-blur-md text-amber-950 px-4 py-3 rounded-2xl flex items-center justify-between shadow-xl">
                      <div className="flex items-center gap-3">
                          <AlertCircle className="w-5 h-5" />
                          <div className="flex flex-col">
                              <span className="text-sm font-bold">Manual Review Required</span>
                              <span className="text-xs opacity-80">{currentCheck.validation_notes}</span>
                          </div>
                      </div>
                      <span className="text-xs font-bold uppercase py-1 px-2 rounded-lg bg-black/10">AI Confidence: {Math.round((currentCheck.confidence_score || 0) * 100)}%</span>
                 </div>
             )}
          </div>

          {/* Right Side: Data Edit Form */}
          <div className="w-full md:w-[450px] lg:w-[500px] flex flex-col bg-card overflow-y-auto">
              <div className="p-6 md:p-8 space-y-6">
                  
                  <div>
                      <h2 className="text-xl font-bold text-foreground mb-1">Extraction Data</h2>
                      <p className="text-sm text-slate-500">Edit any misread fields from the scan before approving.</p>
                  </div>

                  <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); handleSave("APPROVED"); }}>
                      
                      <div className="space-y-1">
                          <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Store Name</label>
                          <input 
                              type="text" 
                              value={editForm.store_name}
                              onChange={e => setEditForm({...editForm, store_name: e.target.value})}
                              className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                          />
                      </div>

                      <div className="flex gap-4">
                          <div className="space-y-1 flex-1">
                              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Check #</label>
                              <input 
                                  type="text" 
                                  value={editForm.check_number}
                                  onChange={e => setEditForm({...editForm, check_number: e.target.value})}
                                  className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                              />
                          </div>
                          <div className="space-y-1 flex-1">
                              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Date (YYYY-MM-DD)</label>
                              <input 
                                  type="text" 
                                  value={editForm.check_date}
                                  onChange={e => setEditForm({...editForm, check_date: e.target.value})}
                                  className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                              />
                          </div>
                      </div>

                      <div className="space-y-1">
                          <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Payee</label>
                          <input 
                              type="text" 
                              value={editForm.payee}
                              onChange={e => setEditForm({...editForm, payee: e.target.value})}
                              className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                          />
                      </div>

                      <div className="flex gap-4">
                          <div className="space-y-1 flex-1">
                              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Amount ($)</label>
                              <input 
                                  type="number" 
                                  step="0.01"
                                  value={editForm.amount}
                                  onChange={e => setEditForm({...editForm, amount: e.target.value})}
                                  className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                              />
                          </div>
                      </div>

                      <div className="space-y-1">
                          <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Bank Name</label>
                          <input 
                              type="text" 
                              value={editForm.bank_name}
                              onChange={e => setEditForm({...editForm, bank_name: e.target.value})}
                              className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                          />
                      </div>

                      <div className="space-y-1">
                          <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Memo</label>
                          <input 
                              type="text" 
                              value={editForm.memo}
                              onChange={e => setEditForm({...editForm, memo: e.target.value})}
                              className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                          />
                      </div>

                      <div className="flex gap-4">
                          <div className="space-y-1 flex-1">
                              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Routing #</label>
                              <input 
                                  type="text" 
                                  value={editForm.routing_number}
                                  onChange={e => setEditForm({...editForm, routing_number: e.target.value})}
                                  className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                              />
                          </div>
                          <div className="space-y-1 flex-1">
                              <label className="text-xs font-bold uppercase tracking-wider text-slate-500">Account #</label>
                              <input 
                                  type="text" 
                                  value={editForm.account_number}
                                  onChange={e => setEditForm({...editForm, account_number: e.target.value})}
                                  className="w-full px-4 py-3 rounded-xl border border-border-custom bg-black/5 dark:bg-white/5 text-foreground font-medium focus:ring-2 focus:ring-indigo-500/50 focus:outline-none transition-all"
                              />
                          </div>
                      </div>

                      <hr className="border-border-custom my-8" />

                      {/* Action Buttons */}
                      <AnimatePresence>
                          {saveSuccess && (
                              <motion.div 
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                exit={{ opacity: 0, height: 0 }}
                                className="mb-4 p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 text-sm font-medium flex items-center justify-center gap-2"
                              >
                                  <CheckCircle2 className="w-4 h-4" />
                                  Check Approved & Saved Successfully!
                              </motion.div>
                          )}
                      </AnimatePresence>

                      <div className="flex items-center gap-3">
                          <button 
                             type="button"
                             onClick={() => handleSave("REJECTED")}
                             disabled={saving}
                             className="flex flex-col items-center justify-center w-24 py-3 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-600 transition-colors disabled:opacity-50"
                          >
                             <XCircle className="w-5 h-5 mb-1" />
                             <span className="text-[10px] font-bold uppercase">Reject</span>
                          </button>
                          
                          <button 
                             type="submit"
                             disabled={saving}
                             className="flex-1 flex items-center justify-center gap-2 py-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50 disabled:shadow-none"
                          >
                              {saving ? (
                                  <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                              ) : (
                                  <>
                                      <CheckCircle2 className="w-5 h-5" />
                                      <span>{editForm.status === "APPROVED" ? "Save Changes" : "Approve Check"}</span>
                                  </>
                              )}
                          </button>
                      </div>

                  </form>
              </div>
          </div>

      </div>
    </main>
  );
}
