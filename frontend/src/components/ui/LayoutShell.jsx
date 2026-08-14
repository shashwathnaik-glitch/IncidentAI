import React from 'react';
import { Navbar } from '../Navbar';

/**
 * Layout Shell Component providing responsive container, top sticky header,
 * main workspace area, background grid/glows, and footer.
 */
export const LayoutShell = ({ children, currentView, onNavigate }) => {
  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100 font-sans antialiased relative selection:bg-blue-500/30 selection:text-blue-200">
      
      {/* Background Ambient Glow Effects */}
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[140px] pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none -z-10" />

      {/* Top Navbar */}
      <Navbar currentView={currentView} onNavigate={onNavigate} />

      {/* Main Responsive Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-8">
        {children}
      </main>

      {/* Persistent Enterprise Footer */}
      <footer className="border-t border-slate-800/80 py-4 px-6 text-center text-xs text-slate-500 bg-slate-950/60 backdrop-blur-md">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>IncidentMind Platform • CockroachDB AI Hackathon 2026</span>
          <span className="text-[11px] text-slate-600 font-mono">Enterprise Operational Memory v1.1 • AWS Bedrock & CRDB pgvector</span>
        </div>
      </footer>
    </div>
  );
};
