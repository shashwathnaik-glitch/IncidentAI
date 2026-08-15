import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { authService } from '../services/authService';
import { 
  User, 
  ShieldCheck, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  AlertCircle, 
  Loader2, 
  Sparkles,
  CheckCircle2,
  Cpu
} from 'lucide-react';

export const LoginForm = ({ onSuccessRedirect }) => {
  const { login } = useAuth();
  const [activeRole, setActiveRole] = useState('employee'); // 'employee' | 'admin'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  
  // UI states
  const [errors, setErrors] = useState({});
  const [authError, setAuthError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Client-side input validation
  const validateForm = () => {
    const newErrors = {};

    if (!email.trim()) {
      newErrors.email = 'Email address is required.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
      newErrors.email = 'Please enter a valid email address (e.g. name@company.com).';
    }

    if (!password) {
      newErrors.password = 'Password is required.';
    } else if (password.length < 6) {
      newErrors.password = 'Password must be at least 6 characters long.';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const user = await login(email, password, activeRole);
      if (onSuccessRedirect) {
        onSuccessRedirect(user.role);
      }
    } catch (err) {
      setAuthError(err.message || 'Authentication failed. Please verify your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillDemoAccount = (demoEmail, demoPassword, role) => {
    setActiveRole(role);
    setEmail(demoEmail);
    setPassword(demoPassword);
    setErrors({});
    setAuthError('');
  };

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Brand Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold uppercase tracking-wider mb-4">
          <Cpu className="w-3.5 h-3.5" />
          <span>CockroachDB AI Incident Resolution</span>
        </div>
        <h1 className="text-3xl font-extrabold text-white tracking-tight">
          Incident<span className="bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">Mind</span>
        </h1>
        <p className="text-slate-400 text-sm mt-1">
          AI Incident Resolution Engineer with persistent memory
        </p>
      </div>

      {/* Login Card */}
      <div className="bg-slate-900/80 backdrop-blur-2xl border border-slate-800 rounded-3xl p-8 shadow-2xl shadow-blue-950/20">
        
        {/* Role Toggle Tabs */}
        <div className="flex bg-slate-950/70 p-1.5 rounded-2xl border border-slate-800 mb-6">
          <button
            type="button"
            onClick={() => {
              setActiveRole('employee');
              setErrors({});
              setAuthError('');
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-semibold text-xs transition-all ${
              activeRole === 'employee'
                ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            <User className="w-4 h-4" />
            <span>Employee Portal</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setActiveRole('admin');
              setErrors({});
              setAuthError('');
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl font-semibold text-xs transition-all ${
              activeRole === 'admin'
                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50'
            }`}
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Admin Console</span>
          </button>
        </div>

        {/* Global Error Banner */}
        {authError && (
          <div className="mb-6 p-4 rounded-2xl bg-red-500/10 border border-red-500/30 flex items-start gap-3 text-red-300 text-sm animate-in fade-in slide-in-from-top-2">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-red-200">Authentication Error</p>
              <p className="text-xs text-red-300/90 mt-0.5 leading-relaxed">{authError}</p>
            </div>
          </div>
        )}

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="space-y-5" noValidate>
          {/* Email Field */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Corporate Email Address
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Mail className="w-4 h-4" />
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errors.email) setErrors((prev) => ({ ...prev, email: '' }));
                }}
                disabled={isSubmitting}
                placeholder={activeRole === 'admin' ? 'admin@company.com' : 'engineer@company.com'}
                className={`w-full pl-10 pr-4 py-3 bg-slate-950/80 border rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 transition-all ${
                  errors.email
                    ? 'border-red-500/50 focus:ring-red-500/30'
                    : 'border-slate-800 focus:border-blue-500/50 focus:ring-blue-500/20'
                }`}
              />
            </div>
            {errors.email && (
              <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{errors.email}</span>
              </p>
            )}
          </div>

          {/* Password Field */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Password
              </label>
              <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Please contact your IT administrator to reset corporate credentials.'); }} className="text-xs text-blue-400 hover:text-blue-300">
                Forgot password?
              </a>
            </div>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) setErrors((prev) => ({ ...prev, password: '' }));
                }}
                disabled={isSubmitting}
                placeholder="••••••••••••"
                className={`w-full pl-10 pr-10 py-3 bg-slate-950/80 border rounded-xl text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 transition-all ${
                  errors.password
                    ? 'border-red-500/50 focus:ring-red-500/30'
                    : 'border-slate-800 focus:border-blue-500/50 focus:ring-blue-500/20'
                }`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-red-400 mt-1.5 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" />
                <span>{errors.password}</span>
              </p>
            )}
          </div>

          {/* Submit Button with Loading State */}
          <button
            type="submit"
            disabled={isSubmitting}
            className={`w-full py-3.5 px-4 rounded-xl font-semibold text-sm text-white shadow-lg transition-all flex items-center justify-center gap-2 ${
              activeRole === 'admin'
                ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 shadow-indigo-600/25'
                : 'bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-500 hover:to-cyan-500 shadow-blue-600/25'
            } ${isSubmitting ? 'opacity-70 cursor-not-allowed' : ''}`}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Authenticating Credentials...</span>
              </>
            ) : (
              <>
                <span>Log In to {activeRole === 'admin' ? 'Admin Console' : 'IncidentMind'}</span>
                <CheckCircle2 className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* Demo Quick-Fill Presets */}
        <div className="mt-8 pt-6 border-t border-slate-800/80">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-3">
            <span className="font-semibold uppercase tracking-wider text-slate-500">Quick Test Credentials</span>
            <span className="flex items-center gap-1 text-emerald-400 font-medium">
              <Sparkles className="w-3 h-3" /> Ready
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => fillDemoAccount('employee@company.com', 'password123', 'employee')}
              className="p-2.5 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800 hover:border-blue-500/30 text-left transition-all group"
            >
              <div className="text-xs font-semibold text-slate-200 group-hover:text-blue-400">
                Employee Demo
              </div>
              <div className="text-[10px] text-slate-500 truncate">employee@company.com</div>
            </button>

            <button
              type="button"
              onClick={() => fillDemoAccount('admin@company.com', 'admin123', 'admin')}
              className="p-2.5 rounded-xl bg-slate-950/60 hover:bg-slate-800/80 border border-slate-800 hover:border-indigo-500/30 text-left transition-all group"
            >
              <div className="text-xs font-semibold text-slate-200 group-hover:text-indigo-400">
                Admin Demo
              </div>
              <div className="text-[10px] text-slate-500 truncate">admin@company.com</div>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
