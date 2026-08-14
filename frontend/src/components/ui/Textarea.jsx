import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Reusable Textarea Component
 */
export const Textarea = ({
  label,
  error,
  helperText,
  rows = 4,
  isMonospace = false,
  className = '',
  id,
  ...props
}) => {
  const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label
          htmlFor={textareaId}
          className="block text-xs font-semibold text-slate-300 uppercase tracking-wider"
        >
          {label}
        </label>
      )}

      <textarea
        id={textareaId}
        rows={rows}
        className={`w-full px-4 py-3 bg-slate-950/90 border rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 transition-all ${
          isMonospace ? 'font-mono text-xs' : ''
        } ${
          error
            ? 'border-red-500/50 focus:ring-red-500/30'
            : 'border-slate-800 focus:border-blue-500/50 focus:ring-blue-500/20'
        } ${className}`}
        {...props}
      />

      {error ? (
        <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
          <AlertCircle className="w-3.5 h-3.5 shrink-0" />
          <span>{error}</span>
        </p>
      ) : helperText ? (
        <p className="text-[11px] text-slate-500 mt-1">{helperText}</p>
      ) : null}
    </div>
  );
};
