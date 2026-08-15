import React from 'react';
import { useAuth } from '../context/AuthContext';
import { 
  Cpu, 
  ShieldCheck, 
  LogOut, 
  LayoutDashboard
} from 'lucide-react';

export const Navbar = ({ currentView, onNavigate }) => {
  const { user, isAuthenticated, logout } = useAuth();

  if (!isAuthenticated) return null;

  return (
    <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800 px-4 md:px-8 py-3">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Logo & Brand */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5 text-left select-none">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
              <Cpu className="w-5 h-5" />
            </div>
            <div>
              <span className="font-extrabold text-base text-white tracking-tight">
                Incident<span className="text-blue-400">Mind</span>
              </span>
              <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-medium">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span>CockroachDB Active</span>
              </div>
            </div>
          </div>

          {/* Non-interactive session role badge */}
          {user?.role === 'admin' ? (
            <div className="px-3 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold flex items-center gap-1.5 select-none">
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Admin Console</span>
            </div>
          ) : (
            <div className="px-3 py-1.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold flex items-center gap-1.5 select-none">
              <LayoutDashboard className="w-3.5 h-3.5" />
              <span>Employee Portal</span>
            </div>
          )}
        </div>

        {/* User Info & Logout */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-3 pl-4 border-l border-slate-800">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-200">
              {user?.avatar ? (
                <img src={user.avatar} alt={user.name} className="w-full h-full rounded-full object-cover" />
              ) : (
                user?.name?.substring(0, 2).toUpperCase() || 'US'
              )}
            </div>
            <div className="text-left">
              <div className="text-xs font-bold text-slate-200">{user?.name}</div>
              <div className="flex items-center gap-1">
                <span className={`text-[9px] uppercase font-bold px-1.5 py-0.2 rounded ${
                  user?.role === 'admin' ? 'bg-indigo-500/20 text-indigo-300' : 'bg-blue-500/20 text-blue-300'
                }`}>
                  {user?.role}
                </span>
                <span className="text-[10px] text-slate-500 truncate max-w-[120px]">{user?.email}</span>
              </div>
            </div>
          </div>

          <button
            onClick={logout}
            title="Log Out"
            className="p-2 rounded-xl bg-slate-900 hover:bg-red-500/10 border border-slate-800 hover:border-red-500/30 text-slate-400 hover:text-red-400 transition-all"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
