import React from 'react';

/**
 * Reusable Card Component with Glassmorphism and dark enterprise design
 */
export const Card = ({
  children,
  className = '',
  header = null,
  footer = null,
  gradientBorder = false,
  padding = 'p-6',
  ...props
}) => {
  return (
    <div
      className={`bg-slate-900/80 border border-slate-800 rounded-3xl backdrop-blur-xl shadow-2xl shadow-blue-950/10 overflow-hidden relative ${
        gradientBorder ? 'before:absolute before:inset-0 before:p-[1px] before:bg-gradient-to-r before:from-blue-500/20 before:to-indigo-500/20 before:rounded-3xl before:-z-10' : ''
      } ${className}`}
      {...props}
    >
      {header && (
        <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
          {header}
        </div>
      )}

      <div className={padding}>{children}</div>

      {footer && (
        <div className="px-6 py-4 border-t border-slate-800/80 bg-slate-950/40 flex items-center justify-between">
          {footer}
        </div>
      )}
    </div>
  );
};
