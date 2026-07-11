import React, { useState, useEffect } from 'react';
import { Calendar, UserX, CheckCircle2, AlertCircle } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export const ActiveLeaveTracker = () => {
  const [selectedDate, setSelectedDate] = useState(() => {
    const today = new Date();
    return today.toISOString().split('T')[0];
  });
  const [activeLeaves, setActiveLeaves] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchActiveLeaves = async () => {
      if (!selectedDate) return;
      setLoading(true);
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${API_BASE_URL}/api/hod/leaves/active?date_str=${selectedDate}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          setActiveLeaves(data);
        }
      } catch (err) {
        console.error("Failed to fetch active leaves", err);
      } finally {
        setLoading(false);
      }
    };
    fetchActiveLeaves();
  }, [selectedDate]);

  return (
    <div className="glass-panel rounded-2xl p-6 glow-accent-sm border border-slate-800/80 mt-6 animate-slide-up">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-6 gap-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <UserX className="w-5 h-5 text-rose-400" />
          Active Absentee Tracker
        </h3>
        
        <div className="flex items-center gap-2 bg-slate-900/50 p-2 rounded-xl border border-slate-800">
          <Calendar className="w-4 h-4 text-slate-400" />
          <input 
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="bg-transparent border-none text-sm text-slate-200 focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      {loading ? (
        <div className="py-8 text-center text-slate-400 animate-pulse text-sm">Loading tracker...</div>
      ) : activeLeaves.length === 0 ? (
        <div className="py-8 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-sm">
          No faculty members are on approved leave for this date.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {activeLeaves.map((leave) => (
            <div key={leave.leave_id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition-colors">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h4 className="font-bold text-slate-200">{leave.faculty_name}</h4>
                  <p className="text-[10px] text-slate-500 mt-0.5">{leave.faculty_email}</p>
                </div>
                <div className={`px-2 py-1 rounded-md text-[10px] font-bold border ${
                  leave.total_slots_missed === 0 ? 'bg-slate-900/50 text-slate-400 border-slate-800' :
                  leave.slots_resolved === leave.total_slots_missed ? 'bg-emerald-950/40 text-emerald-400 border-emerald-900/40' :
                  'bg-rose-950/40 text-rose-400 border-rose-900/40 animate-pulse'
                }`}>
                  {leave.slots_resolved}/{leave.total_slots_missed} Covered
                </div>
              </div>

              {leave.reason && (
                <div className="text-xs text-slate-400 italic mb-3">"{leave.reason}"</div>
              )}

              {leave.total_slots_missed === 0 ? (
                <div className="text-xs text-slate-500 bg-slate-950 p-2 rounded-lg border border-slate-800/50 flex items-center gap-2">
                  <CheckCircle2 className="w-3.5 h-3.5 text-slate-500" />
                  No classes scheduled today
                </div>
              ) : (
                <div className="space-y-2 mt-3">
                  <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">Substitutes Allocated:</div>
                  <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                    {leave.substitutes.map((sub, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-slate-950/50 p-2 rounded-lg border border-slate-800/50 text-xs">
                        <div className="flex flex-col">
                          <span className="text-slate-300 font-medium">Period {sub.period}</span>
                          <span className="text-[9px] text-slate-500">{sub.class_name}</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {sub.status === 'RESOLVED' ? (
                            <>
                              <span className="text-emerald-400 font-semibold">{sub.substitute_name}</span>
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                            </>
                          ) : (
                            <>
                              <span className="text-rose-400 font-semibold">Unresolved</span>
                              <AlertCircle className="w-3.5 h-3.5 text-rose-500" />
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
