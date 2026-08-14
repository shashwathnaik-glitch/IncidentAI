import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { incidentService } from '../services/incidentService';
import { ReportIncidentModal } from './ReportIncidentModal';
import { AIRecommendationPanel } from './AIRecommendationPanel';
import { IncidentHistoryList } from './IncidentHistoryList';
import { IncidentDetailView } from './IncidentDetailView';
import { 
  Search, 
  BrainCircuit, 
  History, 
  Activity, 
  CheckCircle2, 
  Clock, 
  Plus,
  Sparkles,
  RefreshCw,
  Layers
} from 'lucide-react';

export const EmployeeDashboard = ({ onNavigate }) => {
  const { user } = useAuth();
  
  // Incident State
  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [detailIncident, setDetailIncident] = useState(null); // When viewing detail view
  const [loading, setLoading] = useState(true);
  
  // View mode & filters
  const [viewMode, setViewMode] = useState('overview'); // 'overview' | 'history' | 'detail'
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const aiPanelRef = useRef(null);

  useEffect(() => {
    loadIncidents();
  }, []);

  const loadIncidents = async () => {
    setLoading(true);
    try {
      const data = await incidentService.getIncidents();
      setIncidents(data);
      if (data && data.length > 0 && !selectedIncident) {
        setSelectedIncident(data[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRouteToAIAnalysis = async (analyzedIncident) => {
    await loadIncidents();
    setSelectedIncident(analyzedIncident);
    setViewMode('overview');

    setTimeout(() => {
      if (aiPanelRef.current) {
        aiPanelRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  };

  const handleApproveResolution = async (incidentId, solutionText, outcome, feedbackReason, operatorName) => {
    await incidentService.approveResolution(incidentId, solutionText, outcome, feedbackReason, operatorName);
    await loadIncidents();
    setIncidents(prev => prev.map(inc => {
      if (inc.id === incidentId) {
        return { ...inc, status: outcome === 'success' ? 'RESOLVED' : 'INVESTIGATING' };
      }
      return inc;
    }));
  };

  const handleRejectResolution = async (incidentId, rejectionReason, operatorName) => {
    await incidentService.rejectResolution(incidentId, rejectionReason, operatorName);
    await loadIncidents();
  };

  const openIncidentDetail = (inc) => {
    setDetailIncident(inc);
    setViewMode('detail');
  };

  const filteredIncidents = incidents.filter(inc => {
    const matchesStatus = statusFilter === 'ALL' || inc.status === statusFilter;
    const matchesSearch = searchQuery === '' || 
      inc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inc.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  const activeCount = incidents.filter(i => i.status !== 'RESOLVED').length;
  const resolvedCount = incidents.filter(i => i.status === 'RESOLVED').length;

  return (
    <div className="space-y-8">
      
      {/* Welcome Header */}
      <div className="bg-gradient-to-r from-blue-950/60 via-slate-900 to-indigo-950/50 border border-blue-500/20 rounded-3xl p-6 md:p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl -mr-20 -mt-20 pointer-events-none" />
        
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/15 border border-blue-500/30 text-blue-300 text-xs font-semibold uppercase tracking-wider mb-3">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Employee Resolution Workspace</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
              Welcome back, {user?.name || 'Engineer'}
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              IncidentMind is retrieving vector memory from CockroachDB. Report incidents, review AI recommendations, and inspect historical solution attempts.
            </p>
          </div>

          <button
            onClick={() => setIsReportModalOpen(true)}
            className="py-3.5 px-6 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 text-white font-semibold rounded-2xl shadow-xl shadow-blue-600/25 flex items-center justify-center gap-2.5 transition-all whitespace-nowrap group shrink-0"
          >
            <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
            <span>Report New Incident</span>
          </button>
        </div>
      </div>

      {/* Main View Mode Selector Tabs */}
      <div className="flex bg-slate-900/80 p-1.5 rounded-2xl border border-slate-800 text-xs font-semibold max-w-md">
        <button
          onClick={() => setViewMode('overview')}
          className={`flex-1 py-2 px-4 rounded-xl flex items-center justify-center gap-2 transition-all ${
            viewMode === 'overview'
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/20'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BrainCircuit className="w-4 h-4" />
          <span>Active & AI Analysis</span>
        </button>

        <button
          onClick={() => setViewMode('history')}
          className={`flex-1 py-2 px-4 rounded-xl flex items-center justify-center gap-2 transition-all ${
            viewMode === 'history' || viewMode === 'detail'
              ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <History className="w-4 h-4" />
          <span>Incident Memory History</span>
        </button>
      </div>

      {/* View Mode Router */}
      {viewMode === 'detail' ? (
        <IncidentDetailView
          incident={detailIncident}
          onBack={() => setViewMode('history')}
          onSelectForAI={(inc) => {
            setSelectedIncident(inc);
            setViewMode('overview');
          }}
        />
      ) : viewMode === 'history' ? (
        <IncidentHistoryList
          onSelectIncident={openIncidentDetail}
          onSelectForAI={(inc) => {
            setSelectedIncident(inc);
            setViewMode('overview');
          }}
        />
      ) : (
        /* Overview Mode */
        <div className="space-y-6">
          {/* Status Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Active Incidents</span>
                <div className="p-2 bg-amber-500/10 rounded-xl border border-amber-500/20 text-amber-400">
                  <Clock className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-slate-100">{activeCount}</div>
              <div className="text-xs text-amber-400 mt-1 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                <span>Requires investigation</span>
              </div>
            </div>

            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Resolved Memory</span>
                <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-slate-100">{resolvedCount}</div>
              <div className="text-xs text-emerald-400 mt-1 font-medium">Stored in CockroachDB</div>
            </div>

            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">AI Match Accuracy</span>
                <div className="p-2 bg-blue-500/10 rounded-xl border border-blue-500/20 text-blue-400">
                  <BrainCircuit className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-blue-400">95.2%</div>
              <div className="text-xs text-slate-400 mt-1">1,536-dim vector embeddings</div>
            </div>

            <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 backdrop-blur-xl">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Health</span>
                <div className="p-2 bg-emerald-500/10 rounded-xl border border-emerald-500/20 text-emerald-400">
                  <Activity className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-extrabold text-emerald-400">Operational</div>
              <div className="text-xs text-slate-500 mt-1">AWS Bedrock + CRDB Online</div>
            </div>
          </div>

          {/* Main Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <div className="lg:col-span-5 space-y-4">
              <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-5 backdrop-blur-xl">
                
                <div className="space-y-3 mb-4">
                  <div className="flex items-center justify-between">
                    <h2 className="text-base font-bold text-white flex items-center gap-2">
                      <Layers className="w-4 h-4 text-blue-400" />
                      <span>Incidents Overview</span>
                    </h2>
                    <button
                      onClick={loadIncidents}
                      title="Refresh incidents"
                      className="p-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 transition-all"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                    </button>
                  </div>

                  <div className="relative">
                    <Search className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search title, category, INC ID..."
                      className="w-full pl-9 pr-4 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-blue-500/50"
                    />
                  </div>

                  <div className="flex bg-slate-950/80 p-1 rounded-xl border border-slate-800 text-[11px] font-semibold">
                    {['ALL', 'OPEN', 'INVESTIGATING', 'RESOLVED'].map(st => (
                      <button
                        key={st}
                        onClick={() => setStatusFilter(st)}
                        className={`flex-1 py-1.5 px-2 rounded-lg transition-all ${
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

                <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                  {filteredIncidents.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 text-xs">
                      No incidents matching filter query.
                    </div>
                  ) : (
                    filteredIncidents.map(inc => {
                      const isSelected = selectedIncident && selectedIncident.id === inc.id;
                      
                      return (
                        <div
                          key={inc.id}
                          onClick={() => setSelectedIncident(inc)}
                          className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                            isSelected
                              ? 'bg-blue-600/15 border-blue-500/50 shadow-lg shadow-blue-500/10'
                              : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 hover:bg-slate-950/90'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono font-bold text-slate-300">{inc.id}</span>
                              <span className={`text-[9px] uppercase font-extrabold px-2 py-0.5 rounded-md ${
                                inc.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                                inc.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                                'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                              }`}>
                                {inc.severity}
                              </span>
                            </div>

                            <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded-full ${
                              inc.status === 'RESOLVED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                              inc.status === 'INVESTIGATING' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/30' :
                              'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                            }`}>
                              {inc.status}
                            </span>
                          </div>

                          <h3 className="text-xs font-bold text-slate-100 mb-1.5 leading-snug line-clamp-2">
                            {inc.title}
                          </h3>

                          <p className="text-[11px] text-slate-400 line-clamp-2 mb-2">
                            {inc.description}
                          </p>

                          <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800/60">
                            <span>Category: <span className="text-slate-400 font-medium">{inc.category}</span></span>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                openIncidentDetail(inc);
                              }}
                              className="text-blue-400 hover:underline font-semibold"
                            >
                              Detail History →
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

              </div>
            </div>

            <div ref={aiPanelRef} className="lg:col-span-7 space-y-6">
              
              {selectedIncident && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 backdrop-blur-xl">
                  <div className="flex justify-between items-start gap-4 mb-2">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono font-bold text-blue-400">{selectedIncident.id}</span>
                        <span className="text-xs text-slate-500">• Reported by {selectedIncident.reporter}</span>
                      </div>
                      <h2 className="text-lg font-bold text-white leading-snug">{selectedIncident.title}</h2>
                    </div>
                    
                    <span className={`text-xs uppercase font-extrabold px-3 py-1 rounded-xl ${
                      selectedIncident.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
                      selectedIncident.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    }`}>
                      {selectedIncident.severity}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed mb-4">
                    {selectedIncident.description}
                  </p>

                  {selectedIncident.logs && (
                    <div className="bg-slate-950 p-3 rounded-2xl border border-slate-800 font-mono text-[11px] text-slate-300 overflow-x-auto">
                      <div className="text-[10px] text-slate-500 uppercase font-semibold mb-1">Associated Log Trace</div>
                      <pre className="whitespace-pre-wrap">{selectedIncident.logs}</pre>
                    </div>
                  )}
                </div>
              )}

              <AIRecommendationPanel
                incident={selectedIncident}
                onApprove={handleApproveResolution}
                onReject={handleRejectResolution}
                operatorName={user?.name || 'Employee Operator'}
              />

            </div>

          </div>
        </div>
      )}

      {/* Report Incident Modal Dialog */}
      <ReportIncidentModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        onSuccessRouteToAI={handleRouteToAIAnalysis}
        reporterName={user?.name || 'Support Engineer'}
      />

    </div>
  );
};
