import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, Calendar, Shield, Users, Layers, Award } from 'lucide-react';

export const DashboardLayout = ({ children, title = "Dashboard" }) => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-darkbg flex flex-col font-sans">
      {/* Top Navigation Header */}
      <header className="border-b border-darkbg-border bg-darkbg-card/45 backdrop-blur-md sticky top-0 z-30 px-6 py-4 flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-500">
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <h1 className="font-bold text-slate-100 leading-tight">Adaptive Scheduling</h1>
            <p className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">Engine Core</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-semibold text-slate-200">{user?.name}</div>
            <div className="text-[10px] text-brand-400 font-bold uppercase tracking-wider mt-0.5">{user?.role}</div>
          </div>
          <div className="w-px h-6 bg-darkbg-border hidden sm:block"></div>
          <button
            onClick={logout}
            className="p-2.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:bg-rose-950/20 hover:border-rose-900/30 text-slate-400 hover:text-rose-400 transition-all flex items-center justify-center gap-2"
            title="Log Out"
          >
            <LogOut className="w-4 h-4" />
            <span className="text-xs font-semibold hidden md:inline">Log Out</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex flex-col md:flex-row">
        {/* Sub-Header bar for Page title & Context */}
        <main className="flex-1 p-4 md:p-6 space-y-6 max-w-[1500px] mx-auto w-full">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
            <div>
              <h2 className="text-2xl font-bold text-slate-100 leading-tight tracking-tight">{title}</h2>
              <div className="flex items-center gap-2 mt-1.5">
                <span className="text-xs text-slate-400">Environment: Stable</span>
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              </div>
            </div>
          </div>
          {children}
        </main>
      </div>
    </div>
  );
};
