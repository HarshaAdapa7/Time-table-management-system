import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Calendar, Lock, Mail, Play, AlertCircle, Cpu, ShieldCheck, Zap, Activity } from 'lucide-react';

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (role) => {
    setError('');
    setLoading(true);
    let demoEmail = '';
    let demoPass = '';

    if (role === 'ADMIN') {
      demoEmail = 'admin@timetable.edu';
      demoPass = 'Admin@12345';
    } else if (role === 'HOD') {
      demoEmail = 'hod_csd@anits.edu.in';
      demoPass = 'Password@123';
    } else {
      demoEmail = 'sivarao.csd@anits.edu.in';
      demoPass = 'Password@123';
    }

    try {
      setEmail(demoEmail);
      setPassword(demoPass);
      await login(demoEmail, demoPass);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-darkbg p-4 md:p-8 relative overflow-hidden font-sans">
      {/* Visual Tech Timetable Grid Background */}
      <div className="absolute inset-0 opacity-[0.02] pointer-events-none select-none">
        <svg width="100%" height="100%" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="white" strokeWidth="1"/>
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </div>

      {/* Glowing Ambient Lights */}
      <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] bg-brand-500/10 rounded-full blur-[140px] pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Main Container: Split Grid Layout */}
      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center z-10 animate-fade-in">
        
        {/* Left Side: Scheduling Engine Visualizer (Creative branding panel) */}
        <div className="lg:col-span-6 space-y-6 text-left hidden lg:block pr-6">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20 text-xs font-semibold text-brand-400">
              <Zap className="w-3.5 h-3.5 animate-pulse" /> Core Engine Status: Online
            </div>
            
            <h1 className="text-4xl md:text-5xl font-extrabold text-transparent bg-clip-text bg-gradient-to-br from-white via-slate-200 to-slate-500 tracking-tight leading-none">
              ADAPTIVE<br />SCHEDULING
            </h1>
            
            <p className="text-slate-400 text-sm max-w-md leading-relaxed">
              Google OR-Tools CP-SAT powered scheduling system. Automated collision-free base generation, real-time leaves, mutual swaps, and workload balancing.
            </p>
          </div>

          {/* Engine Dashboard Stats Block */}
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Solve Efficiency</div>
              <div className="text-xl font-bold text-slate-200 mt-1 flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" /> 99.8%
              </div>
            </div>
            <div className="p-4 rounded-2xl bg-slate-900/40 border border-slate-800/80">
              <div className="text-[10px] text-slate-500 uppercase tracking-widest font-bold">Execution Speed</div>
              <div className="text-xl font-bold text-slate-200 mt-1 flex items-center gap-1.5">
                <Activity className="w-4 h-4 text-brand-400" /> &lt;150ms
              </div>
            </div>
          </div>

          {/* Simulated Real-Time Feeds */}
          <div className="p-4 rounded-2xl bg-slate-900/50 border border-slate-800/80 space-y-3">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Engine Core Operations Log</div>
            <div className="space-y-2 font-mono text-[10px]">
              <div className="flex items-center gap-2 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                <span>[OK] CP-SAT solver successfully mapped 480 slots</span>
              </div>
              <div className="flex items-center gap-2 text-brand-400">
                <span className="w-1.5 h-1.5 rounded-full bg-brand-500"></span>
                <span>[AUTO] Substitution resolved for CSD C-Section</span>
              </div>
              <div className="flex items-center gap-2 text-slate-400">
                <span className="w-1.5 h-1.5 rounded-full bg-slate-600"></span>
                <span>[AUDIT] Leave approval substitution fairness checked</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Login Card */}
        <div className="lg:col-span-6 w-full max-w-md mx-auto space-y-6">
          {/* Logo / Header for Mobile View only */}
          <div className="text-center space-y-2 lg:hidden">
            <div className="inline-flex items-center justify-center p-3 rounded-2xl bg-brand-500/10 border border-brand-500/20 mb-2">
              <Cpu className="w-7 h-7 text-brand-400" />
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Adaptive Scheduling</h2>
            <p className="text-xs text-slate-400">Intelligent Academic Scheduling Engine</p>
          </div>

          {/* Glassmorphic Form Card */}
          <div className="glass-panel rounded-3xl p-8 glow-accent border border-slate-800/80 bg-slate-900/15 backdrop-blur-xl space-y-6">
            <div className="space-y-1.5">
              <h3 className="text-xl font-bold text-white tracking-tight">Secure Sign In</h3>
              <p className="text-xs text-slate-500">Enter your credentials to access the engine control portal.</p>
            </div>

            {error && (
              <div className="p-3.5 rounded-xl border border-rose-500/20 bg-rose-950/15 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 mb-2 uppercase tracking-wider">Email Address</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    required
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@university.edu"
                    className="w-full glass-input rounded-2xl py-3.5 pl-11 pr-4 text-sm border-slate-800/60 focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-400 mb-2 uppercase tracking-wider">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    required
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full glass-input rounded-2xl py-3.5 pl-11 pr-4 text-sm border-slate-800/60 focus:border-brand-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-500 hover:bg-brand-600 text-white font-bold py-3.5 rounded-2xl flex items-center justify-center gap-2 text-sm transition-all shadow-lg shadow-brand-500/20 hover:scale-[1.01] active:scale-[0.99]"
              >
                {loading ? (
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                ) : (
                  <>
                    Sign In <Play className="w-3.5 h-3.5 fill-white" />
                  </>
                )}
              </button>
            </form>

            {/* Quick Login Shortcuts */}
            <div className="pt-4 border-t border-darkbg-border text-center">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-3">Quick Demo Portals</p>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => handleQuickLogin('ADMIN')}
                  className="bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-slate-300 font-semibold py-2 px-1 rounded-xl text-[10px] transition-all hover:border-brand-500/30"
                >
                  Admin
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('HOD')}
                  className="bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-slate-300 font-semibold py-2 px-1 rounded-xl text-[10px] transition-all hover:border-brand-500/30"
                >
                  CSE HOD
                </button>
                <button
                  type="button"
                  onClick={() => handleQuickLogin('FACULTY')}
                  className="bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-slate-300 font-semibold py-2 px-1 rounded-xl text-[10px] transition-all hover:border-brand-500/30"
                >
                  Faculty
                </button>
              </div>
            </div>
          </div>

          <div className="text-center text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
            © {new Date().getFullYear()} Academic Operations Engine
          </div>
        </div>

      </div>
    </div>
  );
}
