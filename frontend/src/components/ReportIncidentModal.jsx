import React from 'react';
import { X } from 'lucide-react';
import { IncidentReportForm } from './IncidentReportForm';

export const ReportIncidentModal = ({ isOpen, onClose, onSuccessRouteToAI, reporterName }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in">
      <div className="relative w-full max-w-3xl max-h-[92vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-6 right-6 z-10 p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all"
        >
          <X className="w-5 h-5" />
        </button>

        <IncidentReportForm
          onSuccessRouteToAI={(analyzedIncident) => {
            onSuccessRouteToAI(analyzedIncident);
            onClose();
          }}
          reporterName={reporterName}
          onCancel={onClose}
        />
      </div>
    </div>
  );
};
