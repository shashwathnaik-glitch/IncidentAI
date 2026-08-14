import React from 'react';

/**
 * Reusable Badge Component for Status, Severity, and Solution Outcomes
 * Outcome variants: success | failure | partial | rejected | unknown
 * Severity variants: CRITICAL | HIGH | MEDIUM | LOW
 * Status variants: OPEN | INVESTIGATING | RESOLVED | ALL
 */
export const Badge = ({
  children,
  variant = 'default',
  size = 'md',
  icon: Icon = null,
  className = '',
  ...props
}) => {
  const variantStyles = {
    // Solution Outcomes (v1.1 Specs)
    success: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    failure: 'bg-red-500/15 text-red-400 border-red-500/30',
    partial: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    rejected: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
    unknown: 'bg-slate-800 text-slate-400 border-slate-700',

    // Severities
    CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/30',
    HIGH: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    MEDIUM: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    LOW: 'bg-slate-800 text-slate-300 border-slate-700',

    // Statuses
    RESOLVED: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    INVESTIGATING: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    OPEN: 'bg-blue-500/10 text-blue-400 border-blue-500/30',

    // Roles
    admin: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    employee: 'bg-blue-500/20 text-blue-400 border-blue-500/30',

    // Generic
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    blue: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
    indigo: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30'
  };

  const sizeStyles = {
    sm: 'text-[9px] px-1.5 py-0.5 rounded-md font-mono',
    md: 'text-[10px] px-2.5 py-0.5 rounded-full font-extrabold uppercase',
    lg: 'text-xs px-3 py-1 rounded-xl font-bold uppercase'
  };

  const styleClass = variantStyles[variant] || variantStyles.default;

  return (
    <span
      className={`inline-flex items-center gap-1 border shrink-0 font-sans ${styleClass} ${sizeStyles[size] || sizeStyles.md} ${className}`}
      {...props}
    >
      {Icon && <Icon className="w-3 h-3 shrink-0" />}
      <span>{children}</span>
    </span>
  );
};
