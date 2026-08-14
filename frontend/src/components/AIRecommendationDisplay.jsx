import React, { useState } from 'react';
import { 
  BrainCircuit, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  Ban, 
  Sparkles, 
  ShieldAlert, 
  ShieldCheck, 
  History, 
  Info,
  FlaskConical
} from 'lucide-react';

/**
 * Outcome visual styling configuration for all 5 outcome types defined in v1.1 Memory Specs:
 * - success: Fix solved the incident
 * - failure: Fix did not solve it (deprioritized / avoided)
 * - partial: Fix improved but did not fully resolve
 * - rejected: Engineer chose not to execute
 * - unknown: Outcome could not be verified (never imply success!)
 */
const OUTCOME_CONFIG = {
  success: {
    label: 'SUCCESS',
    badgeClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    icon: CheckCircle2,
    explanation: 'Proven Fix: High positive historical evidence. Prioritized by AI ranker.'
  },
  failure: {
    label: 'FAILED ATTEMPT',
    badgeClass: 'bg-red-500/15 text-red-400 border-red-500/30',
    icon: XCircle,
    explanation: 'Known Failure: Failed in past incidents. Deprioritized to prevent repeated errors.'
  },
  partial: {
    label: 'PARTIAL RESOLUTION',
    badgeClass: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    icon: AlertTriangle,
    explanation: 'Conditional Fix: Mitigated symptoms but required secondary intervention.'
  },
  rejected: {
    label: 'ENGINEER REJECTED',
    badgeClass: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    icon: Ban,
    explanation: 'Consideration Recorded: Engineer opted out due to policy or risk concerns.'
  },
  unknown: {
    label: 'UNVERIFIED OUTCOME',
    badgeClass: 'bg-slate-800 text-slate-400 border-slate-700',
    icon: HelpCircle,
    explanation: 'Unverified: Outcome status unconfirmed. Cannot be treated as positive evidence.'
  }
};

// Comprehensive test scenario dataset covering all 5 outcome types
const DEMO_5_OUTCOMES_RESPONSE = {
  incidentId: 'INC-9104',
  incidentTitle: 'CockroachDB Connection Pool Exhaustion in Pod-B',
  incidentCategory: 'Database',
  incidentSeverity: 'CRITICAL',
  summary: 'Scale CockroachDB max_connections parameter to 500 and flush idle proxy pooler sessions.',
  rootCause: 'Connection leak caused by unclosed DB cursors in legacy auth middleware during traffic burst spikes.',
  confidence: 94,
  riskLevel: 'HIGH', // 'HIGH' | 'MEDIUM' | 'LOW'
  requiresApproval: true,
  approvalReason: 'Modifies global database cluster connection limits and terminates active backend sessions.',
  suggestedFix: 'ALTER RANGE CONSTRAINTS SET max_connections = 500; SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = "idle";',
  
  similarIncidents: [
    {
      id: 'INC-8894',
      title: 'CockroachDB Node 3 Disk IO Spikes',
      similarityScore: 0.94,
      outcomeSummary: 'Resolved via max_connections adjustment'
    },
    {
      id: 'INC-8412',
      title: 'PostgreSQL Max Client Connections Reached',
      similarityScore: 0.88,
      outcomeSummary: 'Resolved via pooler restart'
    }
  ],

  // Solution attempts demonstrating ALL FIVE outcome types
  solutionAttempts: [
    {
      id: 'att_01',
      solutionText: 'Increase DB max_connections to 500 & restart pgBouncer pooler',
      outcome: 'success',
      count: 8,
      confidenceAtExecution: 0.94,
      failureReason: null,
      notes: 'Proven solution. Resolved incident in 8 out of 8 previous occurrences.'
    },
    {
      id: 'att_02',
      solutionText: 'Hard reboot CockroachDB cluster node during peak traffic',
      outcome: 'failure',
      count: 3,
      confidenceAtExecution: 0.40,
      failureReason: 'Triggered cascading failover alerts across region us-east-1 and dropped active connections.',
      notes: 'AVOIDED BY AI: High failure penalty applied due to repeated operational outages.'
    },
    {
      id: 'att_03',
      solutionText: 'Scale application replica pods without expanding DB pool',
      outcome: 'partial',
      count: 2,
      confidenceAtExecution: 0.65,
      failureReason: 'Slightly reduced CPU load but connection pool remained 100% saturated.',
      notes: 'Partial improvement only. Required subsequent database pool reconfiguration.'
    },
    {
      id: 'att_04',
      solutionText: 'Disable TLS encryption on internal proxy sockets',
      outcome: 'rejected',
      count: 1,
      confidenceAtExecution: 0.50,
      failureReason: 'Security policy violation rejected by Lead SRE.',
      notes: 'Rejected consideration: Preserved in audit trail for policy compliance.'
    },
    {
      id: 'att_05',
      solutionText: 'Apply experimental TCP keepalive sysctl patch',
      outcome: 'unknown',
      count: 1,
      confidenceAtExecution: 0.30,
      failureReason: 'Monitoring agent went offline during patch application; final status unverified.',
      notes: 'UNVERIFIED: Retained in memory but strictly excluded from positive recommendation weighting.'
    }
  ]
};

export const AIRecommendationDisplay = ({ responseData = DEMO_5_OUTCOMES_RESPONSE, onApproveAction }) => {
  const [activeTestFilter, setActiveTestFilter] = useState('ALL'); // 'ALL' | 'success' | 'failure' | 'partial' | 'rejected' | 'unknown'
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  const data = responseData || DEMO_5_OUTCOMES_RESPONSE;

  // Filter solution attempts based on interactive test filter
  const displayedAttempts = data.solutionAttempts.filter(att => 
    activeTestFilter === 'ALL' || att.outcome === activeTestFilter
  );

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
      
      {/* 1. Header: Incident Being Analyzed & AI Confidence */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-mono font-bold">
              <BrainCircuit className="w-3.5 h-3.5" />
              <span>Analyzing: {data.incidentId}</span>
            </span>
            <span className={`text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded border ${
              data.mode === 'mock' 
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30' 
                : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
            }`}>
              {data.mode === 'mock' ? 'MOCK MODE' : 'REAL CRDB MEMORY'}
            </span>
            <span className="text-xs text-slate-400">• {data.incidentCategory}</span>
          </div>

          <h2 className="text-xl font-extrabold text-white tracking-tight">
            {data.incidentTitle}
          </h2>
        </div>

        {/* Confidence & Risk Score Box */}
        <div className="flex items-center gap-3 bg-slate-950/90 p-3 rounded-2xl border border-slate-800 shrink-0">
          <div className="text-right">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">AI Confidence</div>
            <div className="text-xl font-extrabold text-blue-400">{data.confidence}%</div>
          </div>

          <div className="pl-3 border-l border-slate-800 text-left">
            <div className="text-[10px] text-slate-400 uppercase font-semibold">Risk Level</div>
            <div className={`text-xs font-bold uppercase px-2 py-0.5 rounded-md mt-0.5 ${
              data.riskLevel === 'HIGH' ? 'bg-red-500/20 text-red-400 border border-red-500/30' :
              data.riskLevel === 'MEDIUM' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
              'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
            }`}>
              {data.riskLevel} Risk
            </div>
          </div>
        </div>
      </div>

      {/* 2. Recommendation + Root Cause Reasoning */}
      <div className="space-y-4">
        <div className="p-5 rounded-2xl bg-gradient-to-r from-blue-950/40 via-slate-950 to-indigo-950/30 border border-blue-500/30 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-blue-400">
            <Sparkles className="w-4 h-4 text-blue-400" />
            <span>AI Recommended Solution</span>
          </div>
          <p className="text-base font-bold text-slate-100">{data.summary}</p>
          <div className="p-3.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-blue-200">
            {data.suggestedFix}
          </div>
        </div>

        {/* Root Cause Reasoning Explanation */}
        <div className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-1.5">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5 text-indigo-400" />
            <span>Root Cause Reasoning</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">{data.rootCause}</p>
        </div>
      </div>

      {/* 3. Approval Required Banner */}
      {data.requiresApproval ? (
        <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3 text-amber-300 text-xs">
          <ShieldAlert className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <div className="flex items-center justify-between">
              <span className="font-bold uppercase tracking-wider text-amber-200">Engineer Approval Required</span>
              <span className="text-[10px] bg-amber-500/20 px-2 py-0.5 rounded font-mono">High Impact Action</span>
            </div>
            <p className="mt-1 text-amber-300/90 leading-relaxed">
              {data.approvalReason || 'This recommendation involves high-risk system changes. Review past solution outcomes below before approving execution.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-300 text-xs">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span>Low Risk Action: Pre-approved for automated remediation script execution.</span>
        </div>
      )}

      {/* 4. Outcome-Aware Solution Attempts Breakdown (All 5 Types) */}
      <div className="space-y-4 pt-2">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <History className="w-4 h-4 text-indigo-400" />
              <span>Historical Solution Attempts Memory ({data.solutionAttempts.length})</span>
            </h3>
            <p className="text-[11px] text-slate-400">
              CockroachDB memory evaluates positive evidence while preserving failed attempts as cautionary memory.
            </p>
          </div>

          {/* Interactive Outcome Scenario Filter for Testing */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800 text-[10px] font-bold">
            <span className="px-2 text-slate-500 flex items-center gap-1">
              <FlaskConical className="w-3 h-3 text-purple-400" />
              <span>Test:</span>
            </span>
            {['ALL', 'success', 'failure', 'partial', 'rejected', 'unknown'].map(type => (
              <button
                key={type}
                type="button"
                onClick={() => setActiveTestFilter(type)}
                className={`px-2 py-1 rounded-lg uppercase transition-all ${
                  activeTestFilter === type
                    ? 'bg-blue-600 text-white'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Attempts List rendering distinct styling for all 5 outcome types */}
        <div className="space-y-3">
          {displayedAttempts.map((att) => {
            const config = OUTCOME_CONFIG[att.outcome] || OUTCOME_CONFIG.unknown;
            const Icon = config.icon;

            return (
              <div
                key={att.id}
                className="p-4 rounded-2xl bg-slate-950/80 border border-slate-800 space-y-2 hover:border-slate-700 transition-all"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-xl border shrink-0 mt-0.5 ${config.badgeClass}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-xs font-semibold text-slate-200">{att.solutionText}</div>
                      <div className="text-[11px] text-slate-400 mt-0.5">{config.explanation}</div>
                    </div>
                  </div>

                  {/* Outcome Badge */}
                  <span className={`text-[10px] uppercase font-extrabold px-2.5 py-1 rounded-full border shrink-0 ${config.badgeClass}`}>
                    {config.label} {att.count ? `(${att.count}x)` : ''}
                  </span>
                </div>

                {/* Explicit Failure / Caution Notes */}
                {att.failureReason && (
                  <div className="ml-11 p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-[11px] text-red-300 leading-snug">
                    <span className="font-bold uppercase text-[9px] text-red-400 block mb-0.5">Failure Reason Recorded:</span>
                    {att.failureReason}
                  </div>
                )}

                {/* AI Selection / Avoidance Rationale Note */}
                {att.notes && (
                  <div className="ml-11 text-[10px] text-slate-400 font-mono flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    <span>Memory Evidence: {att.notes}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 5. Similar Historical Incidents */}
      {data.similarIncidents && data.similarIncidents.length > 0 && (
        <div className="space-y-3 pt-2">
          <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Similar Incidents Vector Matches
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.similarIncidents.map(inc => (
              <div key={inc.id} className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs">
                <div>
                  <div className="font-mono font-bold text-blue-400">{inc.id}</div>
                  <div className="text-slate-200 font-medium truncate max-w-[200px]">{inc.title}</div>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-extrabold bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-full">
                    {Math.round(inc.similarityScore * 100)}% Similarity
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};
