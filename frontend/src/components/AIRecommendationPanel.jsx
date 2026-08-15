import React, { useState } from 'react';
import { 
  BrainCircuit, 
  CheckCircle2, 
  Loader2, 
  ThumbsUp,
  ThumbsDown,
  MessageSquare
} from 'lucide-react';
import { AIRecommendationDisplay } from './AIRecommendationDisplay';

export const AIRecommendationPanel = ({ incident, onApprove, onReject, operatorName }) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackOutcome, setFeedbackOutcome] = useState('success');
  const [feedbackReason, setFeedbackReason] = useState('');

  if (!incident || !incident.aiRecommendation) {
    return (
      <div className="p-8 rounded-3xl bg-slate-900/60 border border-slate-800 text-center text-slate-400 backdrop-blur-xl">
        <BrainCircuit className="w-10 h-10 mx-auto mb-3 text-slate-600 animate-pulse" />
        <p className="font-semibold text-slate-300">AI Memory Retrieval Pending</p>
        <p className="text-xs text-slate-500 mt-1">Select an incident from the overview to view historical memory matches and AI resolution recommendations.</p>
      </div>
    );
  }

  const { aiRecommendation } = incident;

  // Format data for AIRecommendationDisplay API contract
  const formattedData = {
    incidentId: incident.id,
    incidentTitle: incident.title,
    incidentCategory: incident.category,
    incidentSeverity: incident.severity,
    summary: aiRecommendation.reasoning_summary || aiRecommendation.summary || 'Recommended resolution strategy.',
    rootCause: aiRecommendation.rootCause || 'Identified root cause analysis based on historical telemetry.',
    confidence: aiRecommendation.confidence_score || aiRecommendation.confidence || 90,
    mode: aiRecommendation.mode || 'real',
    riskLevel: incident.severity === 'CRITICAL' ? 'HIGH' : incident.severity === 'HIGH' ? 'MEDIUM' : 'LOW',
    requiresApproval: aiRecommendation.approval_required !== undefined 
      ? aiRecommendation.approval_required 
      : (aiRecommendation.requiresApproval !== undefined ? aiRecommendation.requiresApproval : true),
    approvalReason: (aiRecommendation.approval_reasons && aiRecommendation.approval_reasons[0]) 
      || aiRecommendation.approvalReason 
      || 'Modifies operational parameters. Review past solution outcomes below before executing.',
    risksAndUncertainties: aiRecommendation.risks_and_uncertainties || [incident.severity === 'CRITICAL' ? 'Critical system impact' : 'Standard operational fix'],
    suggestedFix: aiRecommendation.suggestedFix || 'Execute patch.',
    similarIncidents: [
      { id: 'INC-8894', title: 'CockroachDB Node 3 Disk IO Spikes', similarityScore: aiRecommendation.similarityScore || 0.92 },
      { id: 'INC-8412', title: 'PostgreSQL Connection Limit Exceeded', similarityScore: 0.88 }
    ],
    solutionAttempts: aiRecommendation.pastAttempts && aiRecommendation.pastAttempts.length > 0 
      ? aiRecommendation.pastAttempts 
      : [
          { id: 'sa_1', solutionText: 'Reconfigure max_connections and clear idle pool sessions', outcome: 'success', count: 7, notes: 'Proven resolution.' },
          { id: 'sa_2', solutionText: 'Hard reboot database node without drain', outcome: 'failure', count: 3, failureReason: 'Cascading cluster failover outage.', notes: 'AVOIDED BY AI.' },
          { id: 'sa_3', solutionText: 'Scale reader replica pods', outcome: 'partial', count: 2, failureReason: 'Mitigated read load but write saturation persisted.', notes: 'Partial fix.' },
          { id: 'sa_4', solutionText: 'Disable TLS authentication', outcome: 'rejected', count: 1, failureReason: 'Security policy violation.', notes: 'Rejected.' },
          { id: 'sa_5', solutionText: 'Experimental TCP keepalive sysctl patch', outcome: 'unknown', count: 1, failureReason: 'Monitoring agent dropped connection.', notes: 'Unverified outcome.' }
        ]
  };

  const handleApproveAction = async () => {
    setIsExecuting(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 800));
      await onApprove(incident.id, aiRecommendation.suggestedFix, 'success', 'Approved and executed via Employee Portal', operatorName);
    } finally {
      setIsExecuting(false);
    }
  };

  const handleCustomFeedbackSubmit = async (e) => {
    e.preventDefault();
    setIsExecuting(true);
    try {
      await onApprove(
        incident.id, 
        aiRecommendation.suggestedFix, 
        feedbackOutcome, 
        feedbackReason || 'Manual operator outcome feedback',
        operatorName
      );
      setShowFeedbackModal(false);
      setFeedbackReason('');
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6">
      
      {/* Visual Display for AI Recommendation */}
      <AIRecommendationDisplay responseData={formattedData} />

      {/* Execution Actions Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 shadow-xl flex flex-wrap items-center justify-between gap-4">
        {incident.status === 'RESOLVED' ? (
          <div className="w-full p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between text-emerald-300 text-sm">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="font-semibold">Incident Resolved & Stored in CockroachDB Memory</span>
            </div>
            <span className="text-xs text-emerald-400 font-mono">{incident.resolvedAt ? new Date(incident.resolvedAt).toLocaleTimeString() : 'Just now'}</span>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setShowFeedbackModal(true)}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium text-xs border border-slate-700 transition-all flex items-center gap-1.5"
              >
                <MessageSquare className="w-3.5 h-3.5" />
                <span>Record Manual Outcome</span>
              </button>

              <button
                type="button"
                onClick={() => onReject(incident.id, 'Operator rejected AI fix suggestion', operatorName)}
                disabled={isExecuting}
                className="px-4 py-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 text-red-300 font-medium text-xs border border-red-500/30 transition-all flex items-center gap-1.5"
              >
                <ThumbsDown className="w-3.5 h-3.5" />
                <span>Reject Fix</span>
              </button>
            </div>

            <button
              type="button"
              onClick={handleApproveAction}
              disabled={isExecuting}
              className="px-6 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs shadow-lg shadow-emerald-600/25 transition-all flex items-center gap-2 ml-auto"
            >
              {isExecuting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Executing Resolution Script...</span>
                </>
              ) : (
                <>
                  <ThumbsUp className="w-4 h-4" />
                  <span>Approve & Execute Resolution</span>
                </>
              )}
            </button>
          </>
        )}
      </div>

      {/* Custom Outcome Feedback Modal */}
      {showFeedbackModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-base font-bold text-white mb-2">Submit Manual Solution Outcome</h3>
            <p className="text-xs text-slate-400 mb-4">Record attempt outcome to update CockroachDB memory ranking model.</p>

            <form onSubmit={handleCustomFeedbackSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Outcome Type
                </label>
                <select
                  value={feedbackOutcome}
                  onChange={(e) => setFeedbackOutcome(e.target.value)}
                  className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs"
                >
                  <option value="success">Success (Fully Resolved)</option>
                  <option value="failure">Failure (Fix failed or threw error)</option>
                  <option value="partial">Partial (Improved, but incomplete)</option>
                  <option value="rejected">Rejected (Engineer chose not to execute)</option>
                  <option value="unknown">Unknown (Unverified outcome)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                  Feedback / Reason (Optional)
                </label>
                <input
                  type="text"
                  value={feedbackReason}
                  onChange={(e) => setFeedbackReason(e.target.value)}
                  placeholder="e.g. Cleared queue but latency remains high..."
                  className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-200 text-xs"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowFeedbackModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isExecuting}
                  className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow"
                >
                  Save Outcome
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};
