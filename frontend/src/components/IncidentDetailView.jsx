import React from 'react';
import { 
  ArrowLeft, 
  Clock, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  Ban, 
  Terminal, 
  History, 
  ShieldAlert, 
  BrainCircuit
} from 'lucide-react';

const OUTCOME_STYLES = {
  success: {
    label: 'SUCCESS',
    badge: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle2,
    desc: 'Fix successfully resolved the incident.'
  },
  failure: {
    label: 'FAILED',
    badge: 'bg-red-500/15 text-red-400 border-red-500/30',
    icon: XCircle,
    desc: 'Attempt failed or threw error during execution.'
  },
  partial: {
    label: 'PARTIAL',
    badge: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    icon: AlertTriangle,
    desc: 'Mitigated symptoms partially; required subsequent action.'
  },
  rejected: {
    label: 'REJECTED',
    badge: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    icon: Ban,
    desc: 'Engineer rejected AI suggested fix consideration.'
  },
  unknown: {
    label: 'UNVERIFIED',
    badge: 'bg-slate-800 text-slate-400 border-slate-700',
    icon: HelpCircle,
    desc: 'Execution outcome status unconfirmed.'
  }
};

export const IncidentDetailView = ({ incident, onBack, onSelectForAI }) => {
  // Edge Case: Invalid or missing incident ID
  if (!incident) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-12 text-center max-w-xl mx-auto backdrop-blur-xl">
        <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center mx-auto mb-4 text-red-400">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-white mb-2">Incident Not Found</h2>
        <p className="text-xs text-slate-400 mb-6">
          The requested incident ID does not exist in CockroachDB memory or may have been deleted.
        </p>
        <button
          onClick={onBack}
          className="py-2.5 px-5 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-xl text-xs flex items-center justify-center gap-2 mx-auto transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Return to Incident History</span>
        </button>
      </div>
    );
  }

  const solutionAttempts = incident.solutionAttempts || [];

  return (
    <div className="space-y-6">
      
      {/* Top Action Bar */}
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="py-2 px-4 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Incident List</span>
        </button>

        {onSelectForAI && (
          <button
            onClick={() => onSelectForAI(incident)}
            className="py-2 px-4 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold flex items-center gap-2 shadow-lg shadow-blue-600/20 transition-all"
          >
            <BrainCircuit className="w-4 h-4" />
            <span>Open in AI Analysis View</span>
          </button>
        )}
      </div>

      {/* Incident Overview Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 backdrop-blur-xl shadow-2xl space-y-6">
        
        {/* Header Metadata */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className="text-sm font-mono font-bold text-blue-400 px-2.5 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30">
                {incident.id}
              </span>
              <span className="text-xs text-slate-400">• Category: <strong className="text-slate-200">{incident.category}</strong></span>
              <span className="text-xs text-slate-500">• Reported by {incident.reporter || 'Operator'}</span>
            </div>

            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              {incident.title}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <span className={`text-xs uppercase font-extrabold px-3 py-1 rounded-xl ${
              incident.severity === 'CRITICAL' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
              incident.severity === 'HIGH' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              'bg-blue-500/20 text-blue-400 border border-blue-500/30'
            }`}>
              {incident.severity}
            </span>

            <span className={`text-xs uppercase font-extrabold px-3 py-1 rounded-xl ${
              incident.status === 'RESOLVED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
              incident.status === 'INVESTIGATING' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              'bg-blue-500/20 text-blue-400 border border-blue-500/30'
            }`}>
              {incident.status}
            </span>
          </div>
        </div>

        {/* Timestamps Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs text-slate-400 bg-slate-950/60 p-4 rounded-2xl border border-slate-800/80">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-slate-500" />
            <span>Reported At: <strong className="text-slate-200">{new Date(incident.createdAt).toLocaleString()}</strong></span>
          </div>
          {incident.resolvedAt && (
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Resolved At: <strong className="text-emerald-300">{new Date(incident.resolvedAt).toLocaleString()}</strong></span>
            </div>
          )}
        </div>

        {/* Full Description */}
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Full Description</h3>
          <p className="text-sm text-slate-200 leading-relaxed bg-slate-950/40 p-4 rounded-2xl border border-slate-800/60">
            {incident.description}
          </p>
        </div>

        {/* Log Trace snippet */}
        {incident.logs && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-blue-400" />
              <span>Log Trace Output</span>
            </h3>
            <div className="bg-slate-950 p-4 rounded-2xl border border-slate-800 font-mono text-xs text-slate-300 overflow-x-auto">
              <pre className="whitespace-pre-wrap">{incident.logs}</pre>
            </div>
          </div>
        )}

        {/* Resolution Outcome Summary */}
        {incident.resolutionOutcome && (
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Final Outcome Summary</h3>
            <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300 font-medium">
              {incident.resolutionOutcome}
            </div>
          </div>
        )}

      </div>

      {/* CRITICAL FEATURE: Solution Attempts Historical Timeline (Never Merged / Overwritten) */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 backdrop-blur-xl space-y-6">
        
        <div className="flex justify-between items-center pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <History className="w-5 h-5 text-indigo-400" />
              <span>Solution Attempts Timeline ({solutionAttempts.length})</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              CockroachDB Audit Rule: Every execution attempt is appended as a distinct immutable record.
            </p>
          </div>

          <span className="text-[10px] uppercase font-bold px-2.5 py-1 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
            Immutable Memory
          </span>
        </div>

        {solutionAttempts.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/60 rounded-2xl border border-slate-800 text-slate-500 text-xs">
            No execution attempts recorded for this incident yet.
          </div>
        ) : (
          <div className="space-y-4">
            {solutionAttempts.map((att, index) => {
              const outcomeStyle = OUTCOME_STYLES[att.outcome] || OUTCOME_STYLES.unknown;
              const OutcomeIcon = outcomeStyle.icon;

              return (
                <div 
                  key={att.id || index}
                  className="p-5 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-3 relative overflow-hidden"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/80">
                    <div className="flex items-center gap-3">
                      <div className={`p-2 rounded-xl border ${outcomeStyle.badge}`}>
                        <OutcomeIcon className="w-4 h-4" />
                      </div>
                      <div>
                        <div className="text-xs font-mono font-bold text-slate-400">Attempt #{solutionAttempts.length - index} • {att.id}</div>
                        <div className="text-[11px] text-slate-500">By {att.performedBy || 'Operator'} • {new Date(att.createdAt).toLocaleString()}</div>
                      </div>
                    </div>

                    <span className={`text-[10px] font-extrabold uppercase px-3 py-1 rounded-full border shrink-0 ${outcomeStyle.badge}`}>
                      {outcomeStyle.label}
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-slate-200 bg-slate-900/60 p-3 rounded-xl border border-slate-800/60">
                    {att.solutionText}
                  </div>

                  {att.failureReason && (
                    <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-300 space-y-0.5">
                      <div className="text-[10px] font-bold text-red-400 uppercase">Reason / Feedback:</div>
                      <p>{att.failureReason}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-between text-[11px] text-slate-500 pt-1">
                    <span>Execution Duration: <strong className="text-slate-300">{att.executionDurationMs || 320} ms</strong></span>
                    <span>AI Confidence: <strong className="text-blue-400">{att.confidenceAtExecution ? Math.round(att.confidenceAtExecution * 100) : 90}%</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>

    </div>
  );
};
