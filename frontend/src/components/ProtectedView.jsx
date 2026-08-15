import React from 'react';
import { useAuth } from '../context/AuthContext';
import { ShieldAlert, LogOut, ArrowRight, Lock } from 'lucide-react';

export const ProtectedView = ({ children, allowedRoles = [], fallbackView = 'login', onNavigate }) => {
  const { user, isAuthenticated, loading, logout } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-200">
        <div className="w-12 h-12 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mb-4" />
        <p className="text-sm font-medium text-slate-400">Verifying session credentials...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  // Role-Aware Access Control Check
  if (allowedRoles.length > 0 && !allowedRoles.includes(user.role)) {
    return (
      <div className="min-h-[75vh] flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900/90 backdrop-blur-xl border border-red-500/30 rounded-3xl p-8 shadow-2xl shadow-red-950/40 text-center space-y-6">
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl border border-red-500/30 flex items-center justify-center mx-auto text-red-400">
            <ShieldAlert className="w-8 h-8" />
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Access Restricted</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Your account <span className="text-slate-200 font-semibold">{user.email}</span> is authenticated as <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">{user.role}</span>. You do not have permissions to view this section ({allowedRoles.join(', ')} required).
            </p>
          </div>

          {/* Explicit Note on Security Boundary */}
          <div className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 text-[11px] text-slate-400 text-left space-y-1">
            <div className="font-semibold text-slate-300 flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5 text-indigo-400" />
              <span>Security Architecture Note</span>
            </div>
            <p className="text-slate-400 leading-snug">
              Frontend checks enforce UI navigation privacy. Backend JWT authorization servers enforce the authoritative security boundary for all API endpoints.
            </p>
          </div>

          <div className="space-y-2.5">
            <button
              onClick={() => onNavigate(user.role === 'admin' ? 'admin' : 'dashboard')}
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-blue-500/25 transition-all text-xs"
            >
              <span>Return to {user.role === 'admin' ? 'Admin Panel' : 'Employee Dashboard'}</span>
              <ArrowRight className="w-4 h-4" />
            </button>

            <button
              onClick={logout}
              className="w-full py-2.5 px-4 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl flex items-center justify-center gap-2 border border-slate-700 transition-all text-xs"
            >
              <LogOut className="w-4 h-4" />
              <span>Log Out & Switch User</span>
            </button>
          </div>
        </div>
      </div>
    );
  }

  return children;
};
