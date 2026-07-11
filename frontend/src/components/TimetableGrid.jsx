import React from 'react';
import { Calendar, User, BookOpen, MapPin } from 'lucide-react';

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const PERIODS = [1, 2, 3, 4, 5, 6];
const PERIOD_TIMINGS = {
  1: "09:00 - 10:00 AM",
  2: "10:00 - 11:00 AM",
  3: "11:15 - 12:15 PM",
  4: "12:15 - 01:15 PM",
  5: "02:00 - 03:00 PM",
  6: "03:00 - 04:00 PM",
};

// Simple hashing function to generate subject colors dynamically
const getSubjectColor = (subjectCode) => {
  if (!subjectCode) return 'border-slate-800 bg-slate-900/40 text-slate-400';
  
  let hash = 0;
  for (let i = 0; i < subjectCode.length; i++) {
    hash = subjectCode.charCodeAt(i) + ((hash << 5) - hash);
  }
  
  const colors = [
    'border-emerald-500/30 bg-emerald-950/20 text-emerald-300',
    'border-sky-500/30 bg-sky-950/20 text-sky-300',
    'border-violet-500/30 bg-violet-950/20 text-violet-300',
    'border-amber-500/30 bg-amber-950/20 text-amber-300',
    'border-rose-500/30 bg-rose-950/20 text-rose-300',
    'border-cyan-500/30 bg-cyan-950/20 text-cyan-300',
    'border-indigo-500/30 bg-indigo-950/20 text-indigo-300',
  ];
  
  return colors[Math.abs(hash) % colors.length];
};

export const TimetableGrid = ({ slots = [], title = "Weekly Schedule", subTitle = "" }) => {
  
  // Group slots by day and period for quick lookup
  const slotLookup = React.useMemo(() => {
    const lookup = {};
    slots.forEach(slot => {
      const key = `${slot.day_of_week}_${slot.period_number}`;
      lookup[key] = slot;
    });
    return lookup;
  }, [slots]);

  return (
    <div className="glass-panel rounded-2xl p-6 glow-accent-sm animate-slide-up print-section">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 pb-4 border-b border-darkbg-border">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-brand-500" />
            {title}
          </h3>
          {subTitle && <p className="text-sm text-slate-400 mt-1">{subTitle}</p>}
        </div>
        <div className="flex gap-4 mt-3 md:mt-0 text-xs">
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-brand-500 inline-block"></span> Normal Slot</div>
          <div className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-amber-500 inline-block animate-pulse"></span> Substitute Slot</div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="p-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-darkbg-border w-24">Day</th>
              {PERIODS.map(period => (
                <th key={period} className="p-3 text-left text-xs font-semibold text-slate-400 border-b border-darkbg-border min-w-[150px]">
                  <div className="font-bold text-slate-200">Period {period}</div>
                  <div className="text-[10px] text-slate-500 font-normal">{PERIOD_TIMINGS[period]}</div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {DAYS.map(day => (
              <tr key={day} className="hover:bg-slate-900/10 transition-colors duration-150">
                <td className="p-3 font-semibold text-sm text-slate-300 border-b border-darkbg-border py-6">
                  {day.substring(0, 3)}
                </td>
                {PERIODS.map(period => {
                  const slot = slotLookup[`${day}_${period}`];
                  const hasSub = slot?.is_substitution || slot?.faculty_name?.includes('(Substitute)');
                  
                  return (
                    <td key={period} className="p-2 border-b border-darkbg-border">
                      {slot ? (
                        <div className={`p-3 rounded-xl border text-xs leading-relaxed transition-all duration-300 hover:scale-[1.02] ${
                          hasSub 
                            ? 'border-amber-500/40 bg-amber-950/20 text-amber-200 ring-1 ring-amber-500/40 shadow-md shadow-amber-500/10'
                            : getSubjectColor(slot.subject_code)
                        }`}>
                          <div className="font-bold text-slate-100 flex items-center justify-between gap-1">
                            <span className="truncate">{slot.subject_name}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono ${hasSub ? 'bg-amber-500/10 text-amber-300' : 'bg-white/5'}`}>{slot.subject_code}</span>
                          </div>
                          
                          <div className="mt-2 space-y-1 text-[11px] text-slate-300/80">
                            <div className="flex items-center gap-1.5 truncate">
                              <User className={`w-3.5 h-3.5 shrink-0 ${hasSub ? 'text-amber-400' : 'text-slate-400'}`} />
                              <span className={hasSub ? 'text-amber-400 font-medium' : ''}>{slot.faculty_name}</span>
                            </div>
                            
                            <div className="flex items-center gap-1.5 truncate">
                              <MapPin className={`w-3.5 h-3.5 shrink-0 ${hasSub ? 'text-amber-400' : 'text-slate-400'}`} />
                              <span>{slot.classroom_number ? `Room ${slot.classroom_number}` : 'No Room'}</span>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="h-[92px] rounded-xl border border-dashed border-slate-800/60 bg-slate-950/5 flex items-center justify-center text-[10px] text-slate-600 italic">
                          Free Slot
                        </div>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
