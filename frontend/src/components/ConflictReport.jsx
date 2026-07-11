import React, { useState, useEffect } from 'react';
import { AlertCircle, ArrowRight, UserCheck, ShieldAlert } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export const ConflictReport = ({ unresolvedAllocations = [], facultyList = [], onOverrideSuccess, allowEdit = false }) => {
  const [selectedAlloc, setSelectedAlloc] = useState(null);
  const [overrideFacultyId, setOverrideFacultyId] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (unresolvedAllocations.length > 0 && !selectedAlloc) {
      setSelectedAlloc(unresolvedAllocations[0]);
    }
  }, [unresolvedAllocations]);

  const handleOverride = async (e) => {
    e.preventDefault();
    if (!selectedAlloc || !overrideFacultyId) return;

    setSubmitting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/api/hod/substitutions/${selectedAlloc.id}/override`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Authorization': `Bearer ${token}`
        },
        body: new URLSearchParams({
          substitute_faculty_id: overrideFacultyId
        })
      });

      if (!response.ok) {
        throw new Error('Failed to apply override');
      }

      alert('Manual substitute assigned successfully!');
      onOverrideSuccess();
      setSelectedAlloc(null);
      setOverrideFacultyId('');
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up">
      {/* Unresolved Conflict List */}
      <div className="lg:col-span-2 glass-panel rounded-2xl p-6 glow-accent-sm">
        <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          Unresolved Period Conflicts
          {unresolvedAllocations.length > 0 && (
            <span className="text-xs bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded-full font-mono">
              {unresolvedAllocations.length}
            </span>
          )}
        </h3>

        {unresolvedAllocations.length === 0 ? (
          <div className="p-8 text-center text-slate-500 italic border border-dashed border-slate-800 rounded-xl">
            All periods have valid teachers. Zero conflicts flagged.
          </div>
        ) : (
          <div className="space-y-4">
            {unresolvedAllocations.map((alloc) => (
              <div 
                key={alloc.id} 
                className={`p-4 rounded-xl border cursor-pointer transition-all ${
                  selectedAlloc?.id === alloc.id 
                    ? 'border-rose-500 bg-rose-950/10' 
                    : 'border-slate-800/80 bg-slate-900/20 hover:border-slate-700'
                }`}
                onClick={() => setSelectedAlloc(alloc)}
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-xs bg-rose-950 text-rose-400 border border-rose-900/50 px-2 py-0.5 rounded font-mono font-bold uppercase">
                      Clash Detected
                    </span>
                    <h4 className="font-semibold text-slate-200 mt-2">
                      Class {alloc.class_group_name} — Period {alloc.period_number}
                    </h4>
                    <p className="text-xs text-slate-400 mt-1">
                      Date: {alloc.date} | Absent Teacher: {alloc.original_faculty_name}
                    </p>
                  </div>
                  <div className="text-xs text-slate-500 italic flex items-center gap-1">
                    Click to view constraints <ArrowRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Constraint Explainer & Manual Override Form */}
      <div className="glass-panel rounded-2xl p-6 glow-accent-sm">
        <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-amber-500" />
          Conflict Explainer
        </h3>

        {!selectedAlloc ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-800 rounded-xl text-slate-500 italic text-xs">
            Select a conflict card to explain scheduling clashes and override.
          </div>
        ) : (
          <div className="space-y-5">
            <div>
              <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Automated Reason</h4>
              <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-900 text-xs font-mono text-slate-300 whitespace-pre-line leading-relaxed max-h-[220px] overflow-y-auto">
                {selectedAlloc.explanation || "No explanation provided."}
              </div>
            </div>

            {allowEdit && (
              <div className="pt-4 border-t border-darkbg-border">
                <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">Manual Override</h4>
                <form onSubmit={handleOverride} className="space-y-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1.5">Select Override Teacher</label>
                    <select
                      required
                      value={overrideFacultyId}
                      onChange={(e) => setOverrideFacultyId(e.target.value)}
                      className="w-full glass-input rounded-xl p-2.5 text-xs text-slate-200"
                    >
                      <option value="" disabled className="bg-darkbg-card">-- Select Faculty --</option>
                      {facultyList
                        .filter(f => f.name !== selectedAlloc.original_faculty_name)
                        .map(f => (
                          <option key={f.id} value={f.id} className="bg-darkbg-card">
                            {f.name} ({f.department_name})
                          </option>
                        ))
                      }
                    </select>
                  </div>

                  <button
                    type="submit"
                    disabled={submitting || !overrideFacultyId}
                    className="w-full bg-brand-500 hover:bg-brand-600 text-white font-bold py-2.5 px-4 rounded-xl flex items-center justify-center gap-1.5 text-xs transition-all shadow-md shadow-brand-500/25"
                  >
                    <UserCheck className="w-4 h-4" /> Force Allocate Teacher
                  </button>
                </form>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
