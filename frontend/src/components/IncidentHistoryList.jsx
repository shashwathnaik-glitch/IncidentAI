import React, { useState, useEffect } from 'react';
import { incidentService } from '../services/incidentService';
import { 
  Search, 
  ChevronLeft, 
  ChevronRight, 
  RefreshCw, 
  AlertCircle, 
  Inbox, 
  Layers, 
  CheckCircle2,
  BrainCircuit,
  ArrowRight,
  Clock
} from 'lucide-react';

export const IncidentHistoryList = ({ onSelectIncident, onSelectForAI }) => {
  const [incidents, setIncidents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(5);
  const [totalPages, setTotalPages] = useState(1);
  
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  
  // UI States
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState('');

  useEffect(() => {
    fetchHistory();
  }, [page, limit, statusFilter, searchQuery]);

  const fetchHistory = async () => {
    setLoading(true);
    setApiError('');
    try {
      const data = await incidentService.getIncidentsPaginated(page, limit, statusFilter, searchQuery);
      setIncidents(data.incidents || []);
      setTotal(data.total || 0);
      setTotalPages(data.totalPages || 1);
    } catch (err) {
      setApiError(err.message || 'Failed to communicate with CockroachDB memory backend.');
    } finally {
      setLoading(false);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) setPage(page - 1);
  };

  const handleNextPage = () => {
    if (page < totalPages) setPage(page + 1);
  };

  return (
    <div className="space-y-6">
      
      {/* Search & Filter Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl shadow-xl space-y-4">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
              <Layers className="w-5 h-5 text-blue-400" />
              <span>Incident History & Memory Ledger</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Historical log of reported incidents, solution attempts, and resolution outcomes stored in CockroachDB.
            </p>
          </div>

          <button
            onClick={fetchHistory}
            disabled={loading}
            className="py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs flex items-center justify-center gap-2 border border-slate-700 transition-all shrink-0"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh Ledger</span>
          </button>
        </div>

        {/* Filters Row */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 pt-2">
          
          {/* Search Input */}
          <div className="md:col-span-6 relative">
            <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(1);
              }}
              placeholder="Filter by title, category, INC ID..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-950/90 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          {/* Status Filter Tabs */}
          <div className="md:col-span-6 flex bg-slate-950 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
            {['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED'].map((st) => (
              <button
                key={st}
                onClick={() => {
                  setStatusFilter(st);
                  setPage(1);
                }}
                className={`flex-1 py-1.5 px-2 rounded-lg transition-all text-[11px] ${
                  statusFilter === st
                    ? 'bg-blue-600 text-white shadow'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

        </div>

      </div>

      {/* API Failure State */}
      {apiError && (
        <div className="p-6 rounded-3xl bg-red-500/10 border border-red-500/30 flex items-center justify-between text-red-300 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-6 h-6 text-red-400 shrink-0" />
            <div>
              <p className="font-bold text-red-200">API Gateway Communication Error</p>
              <p className="text-xs text-red-300/80">{apiError}</p>
            </div>
          </div>
          <button
            onClick={fetchHistory}
            className="py-2 px-4 bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-200 rounded-xl font-semibold text-xs"
          >
            Retry API
          </button>
        </div>
      )}

      {/* Incident List Table / Cards */}
      <div className="space-y-3">
        {loading ? (
          <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400 text-sm">
            <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-blue-400" />
            <p>Querying CockroachDB Memory Ledger...</p>
          </div>
        ) : incidents.length === 0 ? (
          /* Empty History State */
          <div className="p-12 text-center bg-slate-900/60 rounded-3xl border border-slate-800 text-slate-400 space-y-3">
            <Inbox className="w-12 h-12 mx-auto text-slate-600" />
            <h3 className="text-base font-bold text-slate-300">No Incident Records Found</h3>
            <p className="text-xs text-slate-500 max-w-sm mx-auto">
              No historical incidents match your current status or search filter criteria.
            </p>
          </div>
        ) : (
          incidents.map((inc) => (
            <div
              key={inc.id}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 hover:border-slate-700 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 group"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-mono font-bold text-blue-400 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">
                    {inc.id}
                  </span>
                  
                  <span className={`text-[9px] uppercase font-extrabold px-2 py-0.5 rounded ${
                    inc.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                    inc.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                    'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                  }`}>
                    {inc.severity}
                  </span>

                  <span className={`text-[9px] uppercase font-extrabold px-2 py-0.5 rounded-full ${
                    inc.status === 'RESOLVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                    inc.status === 'INVESTIGATING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                    'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                  }`}>
                    {inc.status}
                  </span>

                  <span className="text-[10px] text-slate-500 font-medium">Category: {inc.category}</span>
                </div>

                <h3 className="text-sm font-bold text-white group-hover:text-blue-300 transition-colors">
                  {inc.title}
                </h3>

                {inc.resolutionOutcome ? (
                  <p className="text-xs text-emerald-400/90 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    <span>{inc.resolutionOutcome}</span>
                  </p>
                ) : (
                  <p className="text-xs text-slate-400 line-clamp-1">{inc.description}</p>
                )}

                <div className="text-[10px] text-slate-500 flex items-center gap-2">
                  <Clock className="w-3 h-3" />
                  <span>Reported {new Date(inc.createdAt).toLocaleString()}</span>
                  <span>• By {inc.reporter || 'Operator'}</span>
                </div>
              </div>

              {/* Actions Column */}
              <div className="flex items-center gap-2 shrink-0 border-t md:border-t-0 md:border-l border-slate-800 pt-3 md:pt-0 md:pl-4">
                <button
                  type="button"
                  onClick={() => onSelectIncident(inc)}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-1.5 transition-all"
                >
                  <span>View Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>

                {onSelectForAI && (
                  <button
                    type="button"
                    onClick={() => onSelectForAI(inc)}
                    title="Open AI Recommendation"
                    className="p-2 rounded-xl bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/30 text-blue-300 text-xs transition-all"
                  >
                    <BrainCircuit className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination Controls */}
      {!loading && incidents.length > 0 && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-4 border-t border-slate-800/80 text-xs text-slate-400">
          <div className="flex items-center gap-3">
            <span>Showing {incidents.length} of {total} incidents</span>
            <select
              value={limit}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
              className="bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-300 px-2 py-1"
            >
              <option value={5}>5 per page</option>
              <option value={10}>10 per page</option>
              <option value={20}>20 per page</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handlePrevPage}
              disabled={page <= 1}
              className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 transition-all"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            <span className="font-semibold text-slate-200 px-2">
              Page {page} of {totalPages}
            </span>

            <button
              onClick={handleNextPage}
              disabled={page >= totalPages}
              className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed text-slate-300 transition-all"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

    </div>
  );
};
