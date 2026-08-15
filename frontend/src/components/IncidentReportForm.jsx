import React, { useState, useRef } from 'react';
import { incidentService } from '../services/incidentService';
import { 
  AlertTriangle, 
  Send, 
  Loader2, 
  Terminal, 
  Layers, 
  FileText,
  BrainCircuit,
  Sparkles,
  AlertCircle,
  CheckCircle2
} from 'lucide-react';

export const IncidentReportForm = ({ onSuccessRouteToAI, reporterName = 'Support Engineer', onCancel }) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState('HIGH');
  const [category, setCategory] = useState('Database');
  const [logs, setLogs] = useState('');

  // UI & Validation States
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Guard against duplicate submissions
  const isSubmittingRef = useRef(false);

  const validateForm = () => {
    const newErrors = {};

    const cleanTitle = title.trim();
    if (!cleanTitle) {
      newErrors.title = 'Incident title is required.';
    } else if (cleanTitle.length < 5) {
      newErrors.title = 'Title must be at least 5 characters long.';
    }

    const cleanDesc = description.trim();
    if (!cleanDesc) {
      newErrors.description = 'Detailed description is required.';
    } else if (cleanDesc.length < 10) {
      newErrors.description = 'Description must be at least 10 characters long.';
    }

    if (!severity) {
      newErrors.severity = 'Severity level is required.';
    }

    if (!category) {
      newErrors.category = 'System category is required.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setApiError('');

    // Duplicate submission prevention check
    if (isSubmittingRef.current || isSubmitting) {
      return;
    }

    if (!validateForm()) {
      return;
    }

    // Lock submission state immediately
    isSubmittingRef.current = true;
    setIsSubmitting(true);

    try {
      const incidentData = {
        title,
        description,
        severity,
        category,
        logs
      };

      // Call backend API + AI analysis pipeline
      const analyzedIncident = await incidentService.submitAndAnalyzeIncident(
        incidentData,
        reporterName
      );

      // Route directly to AI Analysis / Recommendation view
      if (onSuccessRouteToAI) {
        onSuccessRouteToAI(analyzedIncident);
      }
    } catch (err) {
      setApiError(err.message || 'Failed to submit incident report. Please try again.');
      isSubmittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl backdrop-blur-xl max-w-3xl mx-auto">
      
      {/* Form Header */}
      <div className="flex items-center gap-3 pb-6 border-b border-slate-800 mb-6">
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-2xl text-red-400">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div>
          <div className="inline-flex items-center gap-1.5 text-xs text-blue-400 font-semibold uppercase tracking-wider mb-0.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>CockroachDB Memory Retrieval Trigger</span>
          </div>
          <h2 className="text-xl font-extrabold text-white">Report New Incident</h2>
        </div>
      </div>

      {/* Global Submission Error Alert */}
      {apiError && (
        <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-300 text-sm">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-200">Submission Failed</p>
            <p className="text-xs text-red-300/90 mt-0.5">{apiError}</p>
          </div>
        </div>
      )}

      {/* Incident Form */}
      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        
        {/* Title Field */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Incident Headline / Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (errors.title) setErrors((prev) => ({ ...prev, title: '' }));
            }}
            disabled={isSubmitting}
            placeholder="e.g. CockroachDB Connection Pool Exhaustion in Pod-B"
            className={`w-full px-4 py-3 bg-slate-950/90 border rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 transition-all ${
              errors.title
                ? 'border-red-500/50 focus:ring-red-500/30'
                : 'border-slate-800 focus:border-blue-500/50 focus:ring-blue-500/20'
            }`}
          />
          {errors.title && (
            <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errors.title}</span>
            </p>
          )}
        </div>

        {/* Category & Severity Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              System Category *
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-4 py-3 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-blue-500/50"
            >
              <option value="Database">Database (CockroachDB)</option>
              <option value="Backend API">Backend API (FastAPI)</option>
              <option value="AI Service">AI Service (Amazon Bedrock)</option>
              <option value="Infrastructure">Infrastructure / Cloud</option>
              <option value="Frontend">Frontend Web App</option>
              <option value="Security">Security / Auth</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Severity Level *
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value)}
              disabled={isSubmitting}
              className="w-full px-4 py-3 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:border-blue-500/50"
            >
              <option value="CRITICAL">Critical (P1 - Full Outage)</option>
              <option value="HIGH">High (P2 - Service Degradation)</option>
              <option value="MEDIUM">Medium (P3 - Partial Anomaly)</option>
              <option value="LOW">Low (P4 - Minor Warning)</option>
            </select>
          </div>
        </div>

        {/* Description Field */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Detailed Description *
          </label>
          <textarea
            rows={4}
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              if (errors.description) setErrors((prev) => ({ ...prev, description: '' }));
            }}
            disabled={isSubmitting}
            placeholder="Describe operational failure symptoms, impacted users, and environment..."
            className={`w-full px-4 py-3 bg-slate-950/90 border rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 transition-all ${
              errors.description
                ? 'border-red-500/50 focus:ring-red-500/30'
                : 'border-slate-800 focus:border-blue-500/50 focus:ring-blue-500/20'
            }`}
          />
          {errors.description && (
            <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
              <AlertCircle className="w-3.5 h-3.5" />
              <span>{errors.description}</span>
            </p>
          )}
        </div>

        {/* Logs & Stacktrace Field */}
        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-blue-400" />
              <span>Logs / Error Stacktrace (Optional)</span>
            </label>
            <span className="text-[10px] text-slate-500">Increases vector embedding match score</span>
          </div>
          <textarea
            rows={3}
            value={logs}
            onChange={(e) => setLogs(e.target.value)}
            disabled={isSubmitting}
            placeholder="Paste console stack traces, exception messages, or log snippets..."
            className="w-full px-4 py-3 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-200 font-mono text-xs focus:outline-none focus:border-blue-500/50"
          />
        </div>

        {/* AI Processing Info Banner */}
        <div className="p-4 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center gap-3 text-xs text-blue-300">
          <BrainCircuit className="w-5 h-5 text-blue-400 shrink-0" />
          <p className="leading-relaxed">
            Submitting will call the backend API, generate vector embeddings, and immediately route to the <strong>AI Analysis & Resolution Panel</strong>.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          {onCancel && (
            <button
              type="button"
              onClick={onCancel}
              disabled={isSubmitting}
              className="px-5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-sm transition-all"
            >
              Cancel
            </button>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className={`px-6 py-3.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-sm shadow-lg shadow-blue-500/25 flex items-center justify-center gap-2 transition-all ${
              isSubmitting ? 'opacity-75 cursor-not-allowed' : ''
            }`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Submitting & Analyzing Memory...</span>
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                <span>Submit & View AI Analysis</span>
              </>
            )}
          </button>
        </div>

      </form>

    </div>
  );
};
