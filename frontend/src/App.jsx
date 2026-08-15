import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LoginForm } from './components/LoginForm';
import { EmployeeDashboard } from './components/EmployeeDashboard';
import { AdminDashboard } from './components/AdminDashboard';
import { ProtectedView } from './components/ProtectedView';
import { LayoutShell } from './components/ui';

function AppContent() {
  const { user, isAuthenticated } = useAuth();
  const [currentView, setCurrentView] = useState('login'); // 'login' | 'dashboard' | 'admin'

  // Auto-redirect upon authentication state change
  useEffect(() => {
    if (isAuthenticated && user) {
      if (currentView === 'login') {
        // Role-based initial redirect
        setCurrentView(user.role === 'admin' ? 'admin' : 'dashboard');
      }
    } else {
      setCurrentView('login');
    }
  }, [isAuthenticated, user, currentView]);

  const handleLoginSuccess = (role) => {
    // Role-based redirect target
    if (role === 'admin') {
      setCurrentView('admin');
    } else {
      setCurrentView('dashboard');
    }
  };

  return (
    <LayoutShell currentView={currentView} onNavigate={(view) => setCurrentView(view)}>
      {!isAuthenticated || currentView === 'login' ? (
        <div className="min-h-[80vh] flex items-center justify-center">
          <LoginForm onSuccessRedirect={handleLoginSuccess} />
        </div>
      ) : currentView === 'admin' ? (
        <ProtectedView allowedRoles={['admin']} onNavigate={(v) => setCurrentView(v)}>
          <AdminDashboard />
        </ProtectedView>
      ) : (
        <ProtectedView allowedRoles={['employee', 'admin']} onNavigate={(v) => setCurrentView(v)}>
          <EmployeeDashboard onNavigate={(v) => setCurrentView(v)} />
        </ProtectedView>
      )}
    </LayoutShell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
