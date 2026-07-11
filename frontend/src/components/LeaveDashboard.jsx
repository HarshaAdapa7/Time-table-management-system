import React, { useState } from 'react';
import { AlertCircle, Check, X, Sparkles } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export const LeaveDashboard = ({ pendingLeaves = [], onActionSuccess }) => {
  const [loadingId, setLoadingId] = useState(null);
  const [commentsMap, setCommentsMap] = useState({});
  const [selectedLeaves, setSelectedLeaves] = useState([]);
  const [isBulkApproving, setIsBulkApproving] = useState(false);

  const handleAction = async (leaveId, status) => {
    setLoadingId(leaveId);
    try {
      const token = localStorage.getItem('token');
      const comments = commentsMap[leaveId] || `${status} by HOD`;
      const response = await fetch(`${API_BASE_URL}/api/hod/leaves/${leaveId}/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          status,
          comments
        })
      });

      if (!response.ok) {
        throw new Error('Failed to take action on leave');
      }

      onActionSuccess();
      // Clear comments for this leave
      setCommentsMap(prev => {
        const next = { ...prev };
        delete next[leaveId];
        return next;
      });
    } catch (err) {
      alert(err.message);
    } finally {
      setLoadingId(null);
    }
  };

  const handleCommentChange = (leaveId, value) => {
    setCommentsMap(prev => ({
      ...prev,
      [leaveId]: value
    }));
  };

  const handleToggleSelect = (leaveId) => {
    setSelectedLeaves(prev => 
      prev.includes(leaveId) ? prev.filter(id => id !== leaveId) : [...prev, leaveId]
    );
  };

  const handleBulkApprove = async () => {
    if (selectedLeaves.length === 0) return;
    setIsBulkApproving(true);
    
    try {
      const token = localStorage.getItem('token');
      
      // We will approve them sequentially to avoid race conditions with DB
      for (const leaveId of selectedLeaves) {
        const comments = commentsMap[leaveId] || `Bulk APPROVED by HOD`;
        await fetch(`${API_BASE_URL}/api/hod/leaves/${leaveId}/action`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ status: 'APPROVED', comments })
        });
      }
      
      onActionSuccess();
      setSelectedLeaves([]);
    } catch (err) {
      alert("Error during bulk approval: " + err.message);
    } finally {
      setIsBulkApproving(false);
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-6 glow-accent-sm animate-slide-up">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-brand-400" />
          Pending Leave Requests
          {pendingLeaves.length > 0 && (
            <span className="text-xs bg-brand-500/20 text-brand-300 px-2 py-0.5 rounded-full font-mono">
              {pendingLeaves.length}
            </span>
          )}
        </h3>
        
        {pendingLeaves.length > 0 && (
          <button 
            onClick={handleBulkApprove}
            disabled={selectedLeaves.length === 0 || isBulkApproving}
            className={`text-xs px-4 py-2 rounded-xl transition-all font-semibold flex items-center gap-2 ${
              selectedLeaves.length > 0
                ? 'bg-brand-500 hover:bg-brand-600 text-white shadow-md glow-accent-sm'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed'
            }`}
          >
            {isBulkApproving ? (
              <span className="animate-pulse">Processing...</span>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Approve Selected ({selectedLeaves.length})
              </>
            )}
          </button>
        )}
      </div>

      {pendingLeaves.length === 0 ? (
        <div className="p-8 text-center text-slate-500 italic border border-dashed border-slate-800 rounded-xl text-xs">
          No pending leave requests found. All department allocations are stable.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {pendingLeaves.map((leave) => (
            <div 
              key={leave.id} 
              className={`p-4 rounded-xl border flex flex-col justify-between transition-colors ${
                selectedLeaves.includes(leave.id) ? 'border-brand-500/50 bg-brand-950/20' : 'border-slate-800/80 bg-slate-900/10 hover:border-slate-700/80'
              }`}
            >
              <div>
                <div className="flex justify-between items-start">
                  <div className="flex gap-3 items-start">
                    <input 
                      type="checkbox" 
                      checked={selectedLeaves.includes(leave.id)}
                      onChange={() => handleToggleSelect(leave.id)}
                      className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-800 text-brand-500 focus:ring-brand-500/20"
                    />
                    <div>
                      <h4 className="font-semibold text-slate-200">{leave.faculty_name}</h4>
                      <p className="text-xs text-slate-400 mt-1">
                        {leave.start_date === leave.end_date 
                          ? `Date: ${leave.start_date}` 
                          : `Duration: ${leave.start_date} to ${leave.end_date}`}
                      </p>
                    </div>
                  </div>
                  {leave.specific_periods && (
                    <span className="text-[10px] bg-indigo-950 text-indigo-300 px-2 py-0.5 rounded font-semibold border border-indigo-900/35">
                      Periods: {leave.specific_periods}
                    </span>
                  )}
                </div>
                
                {leave.reason && (
                  <p className="text-xs text-slate-300 mt-3 bg-slate-950/40 p-2.5 rounded-lg italic border border-slate-800/40">
                    "{leave.reason}"
                  </p>
                )}

                <div className="mt-4">
                  <label className="block text-[10px] uppercase tracking-wider font-semibold text-slate-500 mb-1">HOD Comments</label>
                  <input
                    type="text"
                    value={commentsMap[leave.id] || ''}
                    onChange={(e) => handleCommentChange(leave.id, e.target.value)}
                    placeholder="e.g. Approved. Substitutes will be auto-allocated."
                    className="w-full glass-input rounded-lg p-2 text-xs"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mt-4 pt-3 border-t border-slate-800/40">
                <button
                  disabled={loadingId !== null}
                  onClick={() => handleAction(leave.id, 'REJECTED')}
                  className="bg-slate-950 border border-slate-800 hover:bg-slate-900 text-rose-400 hover:text-rose-300 font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 text-xs transition-all"
                >
                  <X className="w-4 h-4" /> Reject
                </button>
                <button
                  disabled={loadingId !== null}
                  onClick={() => handleAction(leave.id, 'APPROVED')}
                  className="bg-brand-500 hover:bg-brand-600 text-white font-semibold py-2 px-3 rounded-lg flex items-center justify-center gap-1.5 text-xs transition-all shadow-md shadow-brand-500/20"
                >
                  <Check className="w-4 h-4" /> Approve & Auto-Allocate
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      <div className="mt-4 p-3 rounded-xl bg-brand-500/5 border border-brand-500/10 text-[11px] text-slate-400 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-brand-400 shrink-0 animate-pulse" />
        <span><strong>Automated Scheduling Mode</strong>: Approving a leave will automatically find qualified cover teachers, resolve the timetable conflict for that date, and issue notifications in real-time.</span>
      </div>
    </div>
  );
};
