import React, { useState, useEffect } from 'react';
import { BarChart3, Users, Clock, AlertTriangle, CalendarRange, Download, Printer } from 'lucide-react';
import { API_BASE_URL } from '../../context/AuthContext';

export const AnalyticsDashboard = () => {
  const [workloadData, setWorkloadData] = useState(null);
  const [leaveData, setLeaveData] = useState(null);
  const [substituteData, setSubstituteData] = useState(null);
  const [conflictData, setConflictData] = useState(null);
  const [timetableData, setTimetableData] = useState([]);
  const [swapClassCounts, setSwapClassCounts] = useState([]);
  const [timetablePivot, setTimetablePivot] = useState('class'); // 'class', 'faculty', 'room'
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };
        
        const [wRes, lRes, sRes, cRes, tRes, scRes] = await Promise.all([
          fetch(`${API_BASE_URL}/api/hod/reports/workload`, { headers }),
          fetch(`${API_BASE_URL}/api/hod/reports/leaves`, { headers }),
          fetch(`${API_BASE_URL}/api/hod/reports/substitutes`, { headers }),
          fetch(`${API_BASE_URL}/api/hod/reports/conflicts`, { headers }),
          fetch(`${API_BASE_URL}/api/hod/reports/timetable`, { headers }),
          fetch(`${API_BASE_URL}/api/faculty/swaps/class-counts`, { headers })
        ]);
        
        if (wRes.ok) setWorkloadData(await wRes.json());
        if (lRes.ok) setLeaveData(await lRes.json());
        if (sRes.ok) setSubstituteData(await sRes.json());
        if (cRes.ok) setConflictData(await cRes.json());
        if (tRes.ok) setTimetableData(await tRes.json());
        if (scRes.ok) setSwapClassCounts(await scRes.json());
        
      } catch (err) {
        console.error("Failed to fetch reports:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchReports();
  }, []);

  if (loading) {
    return <div className="p-12 text-center text-slate-400 animate-pulse">Loading Analytics & Reports...</div>;
  }

  return (
    <div className="space-y-8 animate-slide-up print-section">
      
      <div className="flex justify-between items-center print-hidden">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-brand-400" />
            Analytics & Reports
          </h2>
          <p className="text-slate-400 text-sm mt-1">Comprehensive overview of department health, workload, and scheduling stability.</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => window.print()} className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white text-sm font-semibold rounded-xl flex items-center gap-2 transition-all">
            <Download className="w-4 h-4" /> Export PDF
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Dept Utilization</div>
          <div className="text-3xl font-bold text-white">
            {workloadData?.department_summary.utilization_percentage.toFixed(1)}%
          </div>
          <div className="text-xs text-slate-500 mt-2">Assigned hours vs Total Capacity</div>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Overload Alerts</div>
          <div className="text-3xl font-bold text-rose-400">
            {workloadData?.department_summary.overloaded_count}
          </div>
          <div className="text-xs text-slate-500 mt-2">Faculty operating &gt;80% capacity</div>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Auto-Resolved Conflicts</div>
          <div className="text-3xl font-bold text-emerald-400">
            {conflictData?.conflict_summary.auto_resolved_actions}
          </div>
          <div className="text-xs text-slate-500 mt-2">Conflicts automatically handled by AI</div>
        </div>
        <div className="glass-panel p-5 rounded-2xl border border-slate-800">
          <div className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">Total Substitutions</div>
          <div className="text-3xl font-bold text-indigo-400">
            {substituteData?.substitute_history.length}
          </div>
          <div className="text-xs text-slate-500 mt-2">Tracked in recent history</div>
        </div>
      </div>

      {/* 4.1 Workload Report */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 mt-6 page-break-inside-avoid">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-6">
          <Users className="w-5 h-5 text-brand-400" />
          4.1 Faculty Workload & Overload Report
        </h3>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div>
            <h4 className="text-sm font-semibold text-slate-300 mb-4">Workload Distribution</h4>
            <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {workloadData?.faculty_workloads.map(f => (
                <div key={f.faculty_id} className="text-sm">
                  <div className="flex justify-between mb-1">
                    <span className="text-slate-300">{f.name}</span>
                    <span className={`font-mono ${f.is_overloaded ? 'text-rose-400 font-bold' : 'text-slate-400'}`}>
                      {f.current_workload} / {f.max_hours} hrs
                    </span>
                  </div>
                  <div className="w-full bg-slate-800 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${f.is_overloaded ? 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.5)]' : 'bg-brand-500'}`} 
                      style={{ width: `${Math.min(100, f.ratio * 100)}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          <div>
            <h4 className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" /> 
              Overload Alerts
            </h4>
            {workloadData?.overload_alerts.length === 0 ? (
              <div className="p-4 bg-emerald-950/20 border border-emerald-900/30 rounded-xl text-emerald-400 text-xs">
                No faculty members are currently overloaded. Department balance is healthy.
              </div>
            ) : (
              <div className="space-y-3">
                {workloadData?.overload_alerts.map(f => (
                  <div key={f.faculty_id} className="p-3 bg-rose-950/20 border border-rose-900/30 rounded-xl flex justify-between items-center">
                    <div>
                      <div className="font-semibold text-rose-200 text-sm">{f.name}</div>
                      <div className="text-xs text-rose-400/70 mt-0.5">High Burnout Risk (Score: {f.burnout_score.toFixed(1)})</div>
                    </div>
                    <div className="px-2 py-1 bg-rose-950 rounded text-rose-400 text-xs font-bold border border-rose-900/50">
                      {f.current_workload} hrs
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4.2 Leave Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 page-break-inside-avoid">
        <div className="glass-panel rounded-2xl p-6 border border-slate-800/80">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4">
            <CalendarRange className="w-5 h-5 text-indigo-400" />
            4.2 Leave Trends & History
          </h3>
          <div className="mb-6">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">Top Absenteeism (Days)</h4>
            <div className="flex items-end gap-2 h-32 pt-4">
              {leaveData?.leave_trends.map((t, idx) => (
                <div key={idx} className="flex-1 flex flex-col items-center gap-2 group">
                  <div className="w-full bg-indigo-500/20 hover:bg-indigo-500/40 border border-indigo-500/30 rounded-t-sm relative transition-all"
                       style={{ height: `${Math.max(5, t.days * 15)}px` }}>
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 text-[10px] text-indigo-300 font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                      {t.days}d
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 -rotate-45 whitespace-nowrap overflow-hidden text-ellipsis w-8">{t.name.split(' ')[0]}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 4.5 & 4.6 Reports */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 page-break-inside-avoid">
        {/* 4.5 Substitute Reports */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800/80">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-emerald-400" />
            4.5 Substitute Fairness Check
          </h3>
          <div className="text-xs text-slate-400 mb-4">Tracking which faculty are assigned as substitutes most often.</div>
          <div className="space-y-3 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
            {substituteData?.most_assigned.map((sub, idx) => (
              <div key={idx} className="flex justify-between items-center p-2.5 bg-slate-900/40 rounded-lg border border-slate-800/50">
                <span className="text-sm text-slate-300">{sub.name}</span>
                <span className="text-xs font-bold text-emerald-400 bg-emerald-950 px-2 py-0.5 rounded border border-emerald-900/30">
                  {sub.times_substituted} assignments
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* 4.6 Class-wise Swap Metrics */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800/80">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4">
            <CalendarRange className="w-5 h-5 text-indigo-400" />
            4.6 Class-wise Swap Metrics
          </h3>
          <div className="text-xs text-slate-400 mb-4">Total number of peer-to-peer timetable hour swaps approved per class.</div>
          <div className="space-y-3 max-h-[200px] overflow-y-auto pr-2 custom-scrollbar">
            {swapClassCounts.length === 0 ? (
              <div className="p-4 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                No swap records found in history.
              </div>
            ) : (
              swapClassCounts.map((item, idx) => (
                <div key={idx} className="flex justify-between items-center p-2.5 bg-slate-900/40 rounded-lg border border-slate-800/50">
                  <span className="text-sm text-slate-300">{item.class_name}</span>
                  <span className="text-xs font-bold text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded border border-indigo-900/30 font-mono">
                    {item.count} Swaps
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* 4.3 Master Timetable Reports */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 page-break-inside-avoid print-section">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <CalendarRange className="w-5 h-5 text-sky-400" />
            4.3 Master Timetable Reports
          </h3>
          <div className="flex gap-2 print-hidden">
            <button onClick={() => setTimetablePivot('class')} className={`px-3 py-1.5 text-xs font-bold rounded-lg ${timetablePivot === 'class' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-400'}`}>Class-wise</button>
            <button onClick={() => setTimetablePivot('faculty')} className={`px-3 py-1.5 text-xs font-bold rounded-lg ${timetablePivot === 'faculty' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-400'}`}>Faculty-wise</button>
            <button onClick={() => setTimetablePivot('room')} className={`px-3 py-1.5 text-xs font-bold rounded-lg ${timetablePivot === 'room' ? 'bg-sky-500 text-white' : 'bg-slate-800 text-slate-400'}`}>Room-wise</button>
          </div>
        </div>
        
        <div className="text-xs text-slate-400 mb-4 print-hidden">This raw aggregate view groups all {timetableData.length} scheduled periods by your selected pivot.</div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-300 border-collapse">
            <thead className="text-xs text-slate-500 uppercase bg-slate-900/50">
              <tr>
                <th className="px-4 py-3 border-b border-slate-700">Day</th>
                <th className="px-4 py-3 border-b border-slate-700">Period</th>
                <th className="px-4 py-3 border-b border-slate-700">{timetablePivot === 'class' ? 'Class' : timetablePivot === 'faculty' ? 'Faculty' : 'Room'}</th>
                <th className="px-4 py-3 border-b border-slate-700">Subject</th>
                <th className="px-4 py-3 border-b border-slate-700">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {timetableData.slice(0, 100).map((slot, idx) => ( // limit to 100 to prevent huge DOM in preview
                <tr key={idx} className="hover:bg-slate-900/20">
                  <td className="px-4 py-2 text-xs font-semibold">{slot.day}</td>
                  <td className="px-4 py-2 text-xs">Period {slot.period}</td>
                  <td className="px-4 py-2 text-xs text-sky-400 font-bold">
                    {timetablePivot === 'class' ? slot.class_group : timetablePivot === 'faculty' ? slot.faculty : slot.room}
                  </td>
                  <td className="px-4 py-2 text-[11px]">{slot.subject}</td>
                  <td className="px-4 py-2 text-[10px] text-slate-400">
                    {timetablePivot === 'class' ? `${slot.faculty} | ${slot.room}` : 
                     timetablePivot === 'faculty' ? `Class ${slot.class_group} | ${slot.room}` : 
                     `Class ${slot.class_group} | ${slot.faculty}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {timetableData.length > 100 && (
            <div className="text-center text-xs text-slate-500 py-4 italic print-hidden">Showing first 100 entries... Export to view full grid.</div>
          )}
        </div>
      </div>

      {/* 4.4 Conflict Reports */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800/80 page-break-inside-avoid">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          4.4 Conflict Resolution History
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-400">
            <thead className="text-xs text-slate-500 uppercase bg-slate-900/50">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Timestamp</th>
                <th className="px-4 py-3">Action Type</th>
                <th className="px-4 py-3 rounded-tr-lg">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50">
              {conflictData?.resolution_history.map((log, idx) => (
                <tr key={idx} className="hover:bg-slate-900/20">
                  <td className="px-4 py-3 whitespace-nowrap text-xs font-mono">{new Date(log.timestamp).toLocaleString()}</td>
                  <td className="px-4 py-3">
                    <span className={`text-[10px] px-2 py-1 rounded font-bold border ${
                      log.action.includes('RESOLVE') || log.action.includes('ALLOCATE') ? 'bg-emerald-950 text-emerald-400 border-emerald-900/40' :
                      log.action.includes('CONFLICT') ? 'bg-amber-950 text-amber-400 border-amber-900/40' :
                      'bg-slate-900 text-slate-300 border-slate-800'
                    }`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
};
