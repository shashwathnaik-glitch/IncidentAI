import React, { useEffect } from 'react';
import { X } from 'lucide-react';

/**
 * Reusable Modal Component with backdrop blur and escape key handling
 */
export const Modal = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-2xl',
  className = ''
}) => {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/85 backdrop-blur-md animate-in fade-in">
      <div
        className={`relative w-full ${maxWidth} max-h-[92vh] overflow-y-auto bg-slate-900/95 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl shadow-blue-950/40 ${className}`}
      >
        {/* Close Button */}
        <button
          onClick={onClose}
          type="button"
          className="absolute top-6 right-6 z-10 p-2 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all cursor-pointer"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        {title && (
          <div className="mb-6 pr-8">
            <h2 className="text-xl font-extrabold text-white tracking-tight">{title}</h2>
            {subtitle && <p className="text-xs text-slate-400 mt-1">{subtitle}</p>}
          </div>
        )}

        {/* Modal Content */}
        {children}
      </div>
    </div>
  );
};
