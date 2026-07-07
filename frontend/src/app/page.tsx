'use client';

import { useState, useEffect, useCallback } from 'react';

interface Job {
  job_id: string;
  filename: string;
  status: string;
  total_rows: number;
  processed_rows: number;
  created_at: string;
  completed_at: string | null;
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('IDLE'); // IDLE, UPLOADING, PROCESSING, COMPLETED, FAILED
  const [progress, setProgress] = useState<number>(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [history, setHistory] = useState<Job[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(true);

  const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  // Fetch recent jobs history list
  const fetchHistory = useCallback(async () => {
    try {
      const res = await fetch(`${apiBase}/api/v1/jobs`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (e) {
      console.error('Error fetching job history:', e);
    } finally {
      setLoadingHistory(false);
    }
  }, [apiBase]);

  // Handle file drag events
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  // Handle drop event
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.name.endsWith('.xlsx') || droppedFile.name.endsWith('.xls')) {
        setFile(droppedFile);
        setErrorMessage(null);
      } else {
        setErrorMessage("Invalid file type. Only Excel files (.xlsx, .xls) are supported.");
      }
    }
  };

  // Handle manual file selection
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  // Handle file upload
  const handleUpload = async () => {
    if (!file) return;
    setErrorMessage(null);
    setStatus('UPLOADING');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${apiBase}/api/v1/jobs/upload`, { 
        method: 'POST', 
        body: formData 
      });
      
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload structure validation failed.');
      }
      
      const data = await res.json();
      setJobId(data.job_id);
      setStatus('PROCESSING');
      setProgress(0);
      fetchHistory(); // Refresh history immediately
    } catch (e: any) {
      setErrorMessage(e.message || 'Connection to backend failed.');
      setStatus('IDLE');
    }
  };

  // Poll active job status
  useEffect(() => {
    if (!jobId || status !== 'PROCESSING') return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${apiBase}/api/v1/jobs/${jobId}/status`);
        if (!res.ok) throw new Error("Status endpoint error");
        
        const data = await res.json();
        setProgress(data.progress_percentage);
        
        if (data.status === 'COMPLETED') {
          setStatus('COMPLETED');
          clearInterval(interval);
          fetchHistory(); // Refresh history
        } else if (data.status === 'FAILED') {
          setStatus('FAILED');
          clearInterval(interval);
          fetchHistory(); // Refresh history
        }
      } catch (e) {
        console.error('Error polling status updates:', e);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, status, apiBase, fetchHistory]);

  // Initial load & history polling
  useEffect(() => {
    fetchHistory();
    const historyInterval = setInterval(fetchHistory, 5000);
    return () => clearInterval(historyInterval);
  }, [fetchHistory]);

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + ' ' + 
             date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch (e) {
      return dateStr;
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-900 via-slate-950 to-black text-slate-100 font-sans flex flex-col antialiased">
      {/* Sleek Top Banner */}
      <header className="border-b border-slate-800 bg-slate-950/50 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <svg className="h-5 w-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight bg-gradient-to-r from-indigo-400 via-violet-300 to-white bg-clip-text text-transparent">Antigravity</span>
              <span className="text-xs text-indigo-400 font-semibold block uppercase tracking-wider">Optimizer Engine</span>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
            </span>
            <span className="text-xs font-semibold tracking-wider text-slate-400 uppercase">System Active</span>
          </div>
        </div>
      </header>

      {/* Main Grid Content */}
      <div className="flex-1 max-w-7xl w-full mx-auto p-6 md:p-8 grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        
        {/* Left Side: Upload Panel */}
        <section className="lg:col-span-7 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
            <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500/5 rounded-full filter blur-3xl pointer-events-none" />
            
            <div className="mb-6">
              <h1 className="text-2xl font-bold tracking-tight text-white">Product Content Optimizer</h1>
              <p className="text-sm text-slate-400 mt-1.5 leading-relaxed">
                Transform messy, incomplete ERP spreadsheets into verified, high-converting eCommerce product descriptions. Upload your sheet to begin.
              </p>
            </div>

            {errorMessage && (
              <div className="mb-6 bg-red-950/30 border border-red-800/60 text-red-300 p-4 rounded-xl text-sm flex items-start space-x-3">
                <svg className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <span>{errorMessage}</span>
              </div>
            )}

            {/* State machine views */}
            {status === 'IDLE' && (
              <div className="space-y-5">
                <div 
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center cursor-pointer transition-all duration-300 relative bg-slate-950/40 ${
                    dragActive 
                      ? 'border-indigo-400 bg-indigo-950/10 scale-[0.99] shadow-lg shadow-indigo-500/5' 
                      : 'border-slate-800 hover:border-slate-600 hover:bg-slate-950/60'
                  }`}
                >
                  <input 
                    type="file" 
                    accept=".xlsx, .xls" 
                    className="absolute inset-0 opacity-0 cursor-pointer" 
                    onChange={handleFileChange}
                  />
                  <div className="h-12 w-12 rounded-xl bg-slate-900 border border-slate-850 flex items-center justify-center text-indigo-400 mb-4 shadow-inner">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 13h6m-3-3v6m-9 1V4a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <span className="text-sm font-semibold text-slate-200">
                    {file ? file.name : "Select or drag Excel asset sheet"}
                  </span>
                  <span className="text-xs text-slate-500 mt-2">
                    {file ? `Size: ${(file.size / 1024).toFixed(1)} KB` : "Supports standard .xlsx and .xls formats"}
                  </span>
                </div>
                
                <button 
                  onClick={handleUpload} 
                  disabled={!file}
                  className="w-full bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-500 text-white font-semibold py-3.5 px-4 rounded-xl text-sm transition-all duration-300 shadow-lg shadow-indigo-600/20 active:scale-[0.99] cursor-pointer"
                >
                  Initialize Optimization Run
                </button>
              </div>
            )}

            {(status === 'UPLOADING' || status === 'PROCESSING') && (
              <div className="space-y-6 py-4">
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="relative flex items-center justify-center">
                    {/* Pulsing glow under loader */}
                    <div className="absolute inset-0 rounded-full bg-indigo-500/10 filter blur-xl animate-pulse" />
                    <svg className="animate-spin h-10 w-10 text-indigo-500" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                      <path className="opacity-100" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                  </div>
                  <div className="text-center">
                    <h3 className="font-semibold text-white">
                      {status === 'UPLOADING' ? 'Uploading assets...' : 'Running Extraction Pipeline'}
                    </h3>
                    <p className="text-xs text-slate-400 mt-1">Analyzing schemas and validating LLM quality guardrails</p>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-xs font-semibold uppercase tracking-wider text-indigo-400">
                    <span>Processing Rows</span>
                    <span>{progress}%</span>
                  </div>
                  <div className="w-full h-2 bg-slate-950 border border-slate-850 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full transition-all duration-500" 
                      style={{ width: `${progress}%` }} 
                    />
                  </div>
                </div>
                <p className="text-xs text-center text-slate-500">Do not refresh or close this dashboard run window.</p>
              </div>
            )}

            {status === 'COMPLETED' && (
              <div className="space-y-5 py-2">
                <div className="bg-emerald-950/20 border border-emerald-800/40 p-5 rounded-xl text-center flex flex-col items-center">
                  <div className="h-10 w-10 rounded-full bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-3">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-emerald-400 text-base">Spreadsheet processing complete</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">Content frameworks and accuracy scores successfully verified.</p>
                </div>
                
                <a 
                  href={`${apiBase}/api/v1/jobs/${jobId}/download`}
                  className="block w-full text-center bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold py-3.5 px-4 rounded-xl text-sm transition-all duration-300 shadow-lg shadow-emerald-600/20 active:scale-[0.99]"
                >
                  Download Optimized File
                </a>
                
                <button 
                  onClick={() => { setStatus('IDLE'); setFile(null); setProgress(0); setJobId(null); }}
                  className="w-full bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold py-2.5 rounded-xl transition-all duration-200 active:scale-[0.99] cursor-pointer"
                >
                  Process Another File
                </button>
              </div>
            )}

            {status === 'FAILED' && (
              <div className="space-y-5 py-2">
                <div className="bg-red-950/20 border border-red-800/40 p-5 rounded-xl text-center flex flex-col items-center">
                  <div className="h-10 w-10 rounded-full bg-red-500/10 text-red-400 flex items-center justify-center mb-3">
                    <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                  <h3 className="font-semibold text-red-400 text-base">Spreadsheet processing failed</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">Quality score matrix could not be resolved after maximum retries.</p>
                </div>
                
                <button 
                  onClick={() => { setStatus('IDLE'); setFile(null); setProgress(0); setJobId(null); }}
                  className="w-full bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold py-2.5 rounded-xl transition-all duration-200 active:scale-[0.99] cursor-pointer"
                >
                  Try Again
                </button>
              </div>
            )}
          </div>
        </section>

        {/* Right Side: Recent Runs History */}
        <section className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900/60 border border-slate-800/80 backdrop-blur-xl rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white tracking-tight">Recent Runs</h2>
              <button 
                onClick={fetchHistory}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center space-x-1 transition cursor-pointer"
              >
                <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H18" />
                </svg>
                <span>Refresh</span>
              </button>
            </div>

            {loadingHistory ? (
              <div className="space-y-3 py-6">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-16 w-full bg-slate-950/40 rounded-xl animate-pulse border border-slate-850" />
                ))}
              </div>
            ) : history.length === 0 ? (
              <div className="text-center py-10 border border-slate-850 border-dashed rounded-xl bg-slate-950/20">
                <svg className="h-8 w-8 text-slate-600 mx-auto mb-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7v8a2 2 0 002 2h6M8 7V5a2 2 0 012-2h4.586a1 1 0 01.707.293l4.414 4.414a1 1 0 01.293.707V15a2 2 0 01-2 2h-2M8 7H6a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2v-2" />
                </svg>
                <span className="text-xs text-slate-500 font-medium">No previous optimization runs found</span>
              </div>
            ) : (
              <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                {history.map((job) => {
                  const isJobCompleted = job.status === 'COMPLETED';
                  const isJobProcessing = job.status === 'PROCESSING' || job.status === 'PENDING';
                  const isJobFailed = job.status === 'FAILED';
                  
                  return (
                    <div 
                      key={job.job_id} 
                      className={`p-3.5 rounded-xl border transition-all duration-200 ${
                        jobId === job.job_id 
                          ? 'bg-indigo-950/20 border-indigo-500/40' 
                          : 'bg-slate-950/40 border-slate-850 hover:bg-slate-950/80 hover:border-slate-800'
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="min-w-0 pr-2">
                          <p className="text-xs font-semibold text-white truncate max-w-[200px]" title={job.filename}>
                            {job.filename}
                          </p>
                          <p className="text-[10px] text-slate-500 mt-0.5">
                            {formatDate(job.created_at)} • {job.total_rows} rows
                          </p>
                        </div>
                        
                        {/* Status Badge */}
                        <div>
                          {isJobCompleted && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              COMPLETED
                            </span>
                          )}
                          {isJobProcessing && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 animate-pulse">
                              {job.status}
                            </span>
                          )}
                          {isJobFailed && (
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">
                              FAILED
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Download link for completed runs */}
                      {isJobCompleted && (
                        <div className="mt-3 flex items-center justify-between border-t border-slate-850 pt-2.5">
                          <span className="text-[10px] text-slate-400">Ready to download</span>
                          <a 
                            href={`${apiBase}/api/v1/jobs/${job.job_id}/download`}
                            className="text-[10px] font-bold text-emerald-400 hover:text-emerald-300 flex items-center space-x-1 transition"
                          >
                            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            <span>Download</span>
                          </a>
                        </div>
                      )}

                      {/* Micro progress indicator for processing runs */}
                      {isJobProcessing && (
                        <div className="mt-3">
                          <div className="flex justify-between text-[9px] font-medium text-indigo-400 mb-1">
                            <span>Progress</span>
                            <span>{job.processed_rows}/{job.total_rows} rows</span>
                          </div>
                          <div className="w-full h-1 bg-slate-900 border border-slate-850 rounded-full overflow-hidden">
                            <div 
                              className="h-full bg-indigo-500 rounded-full transition-all duration-300"
                              style={{ width: `${(job.processed_rows / job.total_rows * 100) || 0}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

      </div>

      <footer className="border-t border-slate-850 bg-slate-950/80 py-4 text-center">
        <p className="text-[10px] text-slate-500">
          © {new Date().getFullYear()} Antigravity Optimizer Engine. Powered by OpenAI & Tavily APIs.
        </p>
      </footer>
    </main>
  );
}
