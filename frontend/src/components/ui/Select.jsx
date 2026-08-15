import React from 'react';
import { AlertCircle } from 'lucide-react';

/**
 * Reusable Select Dropdown Component
 */
export const Select = ({
  label,
  options = [],
  error,
  helperText,
  className = '',
  id,
  children,
  ...props
}) => {
  const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label
          htmlFor={selectId}
          className="block text-xs font-semibold text-slate-300 uppercase tracking-wider"
        >
          {label}
        </label>
      )}

      <select
        id={selectId}
        className={`w-full px-4 py-3 bg-slate-950/90 border border-slate-800 rounded-xl text-slate-100 text-sm focus:outline-none focus:ring-2 focus:border-blue-500/50 focus:ring-blue-500/20 transition-all ${
          error ? 'border-red-500/50 focus:ring-red-500/30' : ''
        } ${className}`}
        {...props}
      >
        {options.length > 0
          ? options.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))
          : children}
      </select>

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
