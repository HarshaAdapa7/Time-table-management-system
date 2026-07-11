import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { DashboardLayout } from '../components/DashboardLayout';
import { TimetableGrid } from '../components/TimetableGrid';
import { FileText, Send, Calendar, Check, X, Sparkles, MessageSquare, AlertCircle, Bell, RefreshCw } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export default function FacultyDashboard() {
  const { user, authenticatedFetch } = useAuth();
  
  // States
  const [timetable, setTimetable] = useState([]);
  const [myLeaves, setMyLeaves] = useState([]);
  const [leaveBalance, setLeaveBalance] = useState(15);
  const [incomingSwaps, setIncomingSwaps] = useState([]);
  const [mySwaps, setMySwaps] = useState([]);
  const [swapClassCounts, setSwapClassCounts] = useState([]);
  const [substitutions, setSubstitutions] = useState([]);
  const [faculties, setFaculties] = useState([]);
  
  // Structured leave state
  const [leaveStartDate, setLeaveStartDate] = useState('');
  const [leaveEndDate, setLeaveEndDate] = useState('');
  const [leavePeriods, setLeavePeriods] = useState('');
  const [leaveReason, setLeaveReason] = useState('');
  
  // NLP leave state
  const [nlpText, setNlpText] = useState('');
  const [parsingNlp, setParsingNlp] = useState(false);
  const [nlpPreview, setNlpPreview] = useState(null);

  // Swap state
  const [swapReceiverId, setSwapReceiverId] = useState('');
  const [swapDateA, setSwapDateA] = useState('');
  const [swapPeriodA, setSwapPeriodA] = useState('');
  const [swapDateB, setSwapDateB] = useState('');
  const [swapPeriodB, setSwapPeriodB] = useState('');
  const [swapReason, setSwapReason] = useState('');
  const [selectedDate, setSelectedDate] = useState('');

  const fetchFacultyData = async (dateVal = selectedDate) => {
    if (!user?.faculty_id) return;
    try {
      // 1. Fetch own schedule
      const schedUrl = `/api/schedule/faculty/${user.faculty_id}${dateVal ? '?target_date=' + dateVal : ''}`;
      const schedRes = await authenticatedFetch(schedUrl);
      const schedData = await schedRes.json();
      setTimetable(schedData);

      // 2. Fetch own leaves
      const leavesRes = await authenticatedFetch('/api/faculty/leaves/my');
      const leavesData = await leavesRes.json();
      setMyLeaves(leavesData);

      // Fetch own leave balance
      const balanceRes = await authenticatedFetch('/api/faculty/leaves/balance');
      const balanceData = await balanceRes.json();
      setLeaveBalance(balanceData.leave_balance);

      // 3. Fetch incoming swaps
      const swapsRes = await authenticatedFetch('/api/faculty/swaps/incoming');
      const swapsData = await swapsRes.json();
      setIncomingSwaps(swapsData);

      // Fetch all my swaps (sent & received)
      const mySwapsRes = await authenticatedFetch('/api/faculty/swaps/my');
      const mySwapsData = await mySwapsRes.json();
      setMySwaps(mySwapsData);

      // Fetch swaps count per class history
      const classSwapsRes = await authenticatedFetch('/api/faculty/swaps/class-counts');
      const classSwapsData = await classSwapsRes.json();
      setSwapClassCounts(classSwapsData);

      // 4. Fetch faculty list
      const facsRes = await authenticatedFetch('/api/schedule/faculties');
      const facsData = await facsRes.json();
      setFaculties(facsData.filter(f => f.id !== user.faculty_id));

      // 5. Fetch substitutions coverages
      const subsRes = await authenticatedFetch('/api/faculty/substitutions/coverages');
      const subsData = await subsRes.json();
      setSubstitutions(subsData);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchFacultyData(selectedDate);
  }, [user, selectedDate]);

  // Handle structured leave submission
  const handleStructuredLeave = async (e) => {
    e.preventDefault();
    try {
      const res = await authenticatedFetch('/api/faculty/leave-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: leaveStartDate,
          end_date: leaveEndDate,
          specific_periods: leavePeriods || null,
          reason: leaveReason || "Personal Leave"
        })
      });

      if (!res.ok) throw new Error('Failed to submit leave request');
      
      alert('Leave request submitted successfully!');
      setLeaveStartDate('');
      setLeaveEndDate('');
      setLeavePeriods('');
      setLeaveReason('');
      fetchFacultyData();
    } catch (err) {
      alert(err.message);
    }
  };

  // Handle free-text NLP parsing
  const handleNlpParsing = async (e) => {
    e.preventDefault();
    if (!nlpText.trim()) return;

    setParsingNlp(true);
    setNlpPreview(null);
    try {
      const res = await authenticatedFetch('/api/faculty/leave-request/nlp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: nlpText })
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'NLP parsing failed');

      setNlpPreview(data);
    } catch (err) {
      alert(err.message);
    } finally {
      setParsingNlp(false);
    }
  };

  // Confirm the NLP parsed preview and submit it
  const confirmNlpLeave = async () => {
    if (!nlpPreview) return;
    try {
      const res = await authenticatedFetch('/api/faculty/leave-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_date: nlpPreview.start_date,
          end_date: nlpPreview.end_date,
          specific_periods: nlpPreview.specific_periods,
          reason: nlpPreview.reason
        })
      });

      if (!res.ok) throw new Error('Failed to submit parsed leave request');

      alert('Parsed leave request submitted successfully!');
      setNlpText('');
      setNlpPreview(null);
      fetchFacultyData();
    } catch (err) {
      alert(err.message);
    }
  };

  // Submit swap request
  const handleSwapRequest = async (e) => {
    e.preventDefault();
    try {
      const res = await authenticatedFetch('/api/faculty/swap-request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          receiver_faculty_id: parseInt(swapReceiverId),
          date_a: swapDateA,
          period_a: parseInt(swapPeriodA),
          date_b: swapDateB || null,
          period_b: swapPeriodB ? parseInt(swapPeriodB) : null,
          reason: swapReason || "Duty Swap"
        })
      });

      if (!res.ok) throw new Error('Failed to submit swap request');

      alert('Swap request submitted to target faculty!');
      setSwapReceiverId('');
      setSwapDateA('');
      setSwapPeriodA('');
      setSwapDateB('');
      setSwapPeriodB('');
      setSwapReason('');
      fetchFacultyData();
    } catch (err) {
      alert(err.message);
    }
  };

  // Respond to incoming swap requests (Accept / Reject)
  const handleSwapResponse = async (swapId, status) => {
    try {
      const res = await authenticatedFetch(`/api/faculty/swaps/${swapId}/respond`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });

      if (!res.ok) throw new Error('Failed to respond to swap');

      alert(status === 'CONFIRMED' ? 'Mutual swap confirmed! Forwarded to HOD for approval.' : 'Swap request rejected.');
      fetchFacultyData();
    } catch (err) {
      alert(err.message);
    }
  };

  // Cancel Leave Request
  const handleCancelLeave = async (leaveId) => {
    if (!window.confirm("Are you sure you want to cancel this leave request?")) return;
    try {
      const res = await authenticatedFetch(`/api/faculty/leaves/${leaveId}/cancel`, {
        method: 'POST'
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to cancel leave');
      }
      alert('Leave request cancelled successfully!');
      fetchFacultyData();
    } catch (err) {
      alert(err.message);
    }
  };

  const [activeSubSection, setActiveSubSection] = useState('schedule');

  const navigationItems = [
    { id: 'schedule', name: 'My Schedule', icon: Calendar },
    { id: 'leave', name: 'Leave Assistant', icon: FileText },
    { id: 'swap', name: 'Swap Manager', icon: RefreshCw },
    { id: 'duties', name: 'Substitution Duties', icon: Bell }
  ];

  return (
    <DashboardLayout title="Faculty Dashboard">
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Sidebar Nav */}
        <aside className="w-full lg:w-64 shrink-0 glass-panel rounded-2xl p-4 border border-slate-800/80 space-y-1.5 print-hidden">
          <div className="px-3 mb-4">
            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Faculty Portal</div>
          </div>
          {navigationItems.map(item => {
            const Icon = item.icon;
            const isActive = activeSubSection === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveSubSection(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  isActive 
                    ? 'bg-brand-500/10 text-brand-400 border-l-4 border-brand-500 pl-2' 
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-brand-400' : 'text-slate-500'}`} />
                {item.name}
                {item.id === 'duties' && substitutions.length > 0 && (
                  <span className="ml-auto text-[10px] bg-amber-500 text-white px-2 py-0.5 rounded-full font-bold">
                    {substitutions.length}
                  </span>
                )}
                {item.id === 'swap' && incomingSwaps.length > 0 && (
                  <span className="ml-auto text-[10px] bg-indigo-500 text-white px-2 py-0.5 rounded-full font-bold">
                    {incomingSwaps.length}
                  </span>
                )}
              </button>
            );
          })}
        </aside>

        {/* Content Area */}
        <div className="flex-1 w-full space-y-6">
          
          {activeSubSection === 'schedule' && (
            <div className="space-y-6 animate-fade-in">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-brand-500" />
                  My Teaching Schedule
                </h3>
                
                <div className="glass-panel py-2 px-4 rounded-xl border border-darkbg-border flex items-center gap-2 text-xs text-slate-400">
                  <span>View Schedule Date:</span>
                  <input
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="glass-input rounded-xl px-2.5 py-1 text-xs text-slate-200 border-slate-800"
                  />
                </div>
              </div>

              <TimetableGrid 
                slots={timetable} 
                title="My Teaching Schedule" 
                subTitle={selectedDate ? `Schedule for date: ${selectedDate}` : "Weekly teaching template schedule"} 
              />
            </div>
          )}

          {activeSubSection === 'leave' && (
            <div className="space-y-6 animate-fade-in">
              {/* Leave Request Panel */}
              <div className="glass-panel rounded-2xl p-6 glow-accent-sm space-y-6">
                <h3 className="text-lg font-bold text-slate-100 flex items-center justify-between gap-2 pb-4 border-b border-darkbg-border">
                  <div className="flex items-center gap-2">
                    <FileText className="w-5 h-5 text-brand-500" />
                    Leave Assistant (NLP Supported)
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-slate-400 font-semibold">
                    Balance: <strong className="text-brand-400">{leaveBalance}</strong> Days
                  </span>
                </h3>

                {/* NLP Free-text Form */}
                <form onSubmit={handleNlpParsing} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      NLP Free-Text Request
                    </label>
                    <span className="text-[10px] text-brand-400 font-bold flex items-center gap-1">
                      <Sparkles className="w-3 h-3 animate-pulse" /> Layer 5 NLP-Lite
                    </span>
                  </div>
                  
                  <div className="relative">
                    <textarea
                      value={nlpText}
                      onChange={(e) => setNlpText(e.target.value)}
                      placeholder='e.g., "I need Friday off due to family function" or "Leave tomorrow for period 2 due to dentist appointment"'
                      className="w-full glass-input rounded-xl p-3.5 text-xs h-24 resize-none pr-10"
                    />
                    <button
                      type="submit"
                      disabled={parsingNlp || !nlpText.trim()}
                      className="absolute right-3.5 bottom-3.5 p-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-all disabled:opacity-50"
                      title="Analyze Text"
                    >
                      <Sparkles className="w-4 h-4" />
                    </button>
                  </div>
                </form>

                {/* NLP Preview Modal */}
                {nlpPreview && (
                  <div className="p-4 rounded-xl border border-brand-500/30 bg-brand-950/15 text-xs space-y-3 animate-fade-in">
                    <h4 className="font-bold text-brand-300 flex items-center gap-1.5">
                      <MessageSquare className="w-4 h-4" /> Analyzed Request Details
                    </h4>
                    <div className="grid grid-cols-2 gap-3 text-slate-300 bg-slate-950/30 p-2.5 rounded-lg border border-slate-900">
                      <div>
                        <span className="text-slate-500 font-semibold block text-[10px]">Start Date</span>
                        {nlpPreview.start_date}
                      </div>
                      <div>
                        <span className="text-slate-500 font-semibold block text-[10px]">End Date</span>
                        {nlpPreview.end_date}
                      </div>
                      <div>
                        <span className="text-slate-500 font-semibold block text-[10px]">Affected Periods</span>
                        {nlpPreview.specific_periods || "All Day"}
                      </div>
                      <div>
                        <span className="text-slate-500 font-semibold block text-[10px]">Reason</span>
                        {nlpPreview.reason}
                      </div>
                    </div>
                    <div className="flex justify-end gap-2 pt-1">
                      <button 
                        onClick={() => setNlpPreview(null)} 
                        className="px-2.5 py-1.5 border border-slate-800 hover:bg-slate-900 rounded-lg text-slate-400 font-semibold"
                      >
                        Edit
                      </button>
                      <button 
                        onClick={confirmNlpLeave} 
                        className="px-3 py-1.5 bg-brand-500 hover:bg-brand-600 text-white rounded-lg font-semibold flex items-center gap-1"
                      >
                        <Check className="w-3.5 h-3.5" /> Submit Request
                      </button>
                    </div>
                  </div>
                )}

                {/* Structured Leave Form */}
                {!nlpPreview && (
                  <form onSubmit={handleStructuredLeave} className="space-y-4 pt-4 border-t border-darkbg-border">
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      Or Submit Manually
                    </label>
                    
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">Start Date</label>
                        <input
                          required
                          type="date"
                          value={leaveStartDate}
                          onChange={(e) => setLeaveStartDate(e.target.value)}
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">End Date</label>
                        <input
                          required
                          type="date"
                          value={leaveEndDate}
                          onChange={(e) => setLeaveEndDate(e.target.value)}
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Specific Periods (comma-separated, e.g. 3,4 — leave blank for full day)</label>
                      <input
                        type="text"
                        value={leavePeriods}
                        onChange={(e) => setLeavePeriods(e.target.value)}
                        placeholder="e.g. 3,4"
                        className="w-full glass-input rounded-xl p-2 text-xs"
                      />
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Reason for Absence</label>
                      <input
                        required
                        type="text"
                        value={leaveReason}
                        onChange={(e) => setLeaveReason(e.target.value)}
                        placeholder="Medical/Personal details"
                        className="w-full glass-input rounded-xl p-2.5 text-xs"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-slate-900 border border-slate-800 hover:bg-slate-850 hover:border-slate-700 text-slate-300 font-bold py-2.5 rounded-xl flex items-center justify-center gap-1.5 text-xs transition-all"
                    >
                      <Send className="w-3.5 h-3.5" /> Submit Structured Request
                    </button>
                  </form>
                )}
              </div>

              {/* Leave Request History */}
              <div className="glass-panel rounded-2xl p-6 glow-accent-sm">
                <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <FileText className="w-5 h-5 text-brand-500" />
                  My Absence Records
                </h3>

                {myLeaves.length === 0 ? (
                  <div className="p-8 text-center text-slate-500 italic border border-dashed border-slate-800 rounded-xl text-xs">
                    No leave records found.
                  </div>
                ) : (
                  <div className="overflow-y-auto max-h-[300px] space-y-3 pr-1">
                    {myLeaves.map(leave => (
                      <div key={leave.id} className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/10 text-xs flex justify-between items-center hover:border-slate-700/80 transition-colors">
                        <div>
                          <div className="font-semibold text-slate-200">
                            {leave.start_date === leave.end_date ? leave.start_date : `${leave.start_date} to ${leave.end_date}`}
                          </div>
                          <div className="text-[10px] text-slate-500 mt-1">
                            {leave.specific_periods ? `Periods: ${leave.specific_periods}` : 'All Day'} | Reason: {leave.reason}
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            leave.status === 'APPROVED' ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-900/50' :
                            leave.status === 'REJECTED' ? 'bg-rose-950/50 text-rose-300 border border-rose-900/50' :
                            leave.status === 'CANCELLED' ? 'bg-slate-900 text-slate-500 border border-slate-800' :
                            'bg-slate-950/50 text-slate-400 border border-slate-900/50'
                          }`}>
                            {leave.status}
                          </span>
                          {leave.status !== 'CANCELLED' && leave.status !== 'REJECTED' && (
                            <button
                              onClick={() => handleCancelLeave(leave.id)}
                              className="px-2 py-0.5 rounded text-[10px] font-bold border border-rose-900/40 bg-rose-950/20 hover:bg-rose-950/40 text-rose-400 transition-colors"
                            >
                              Cancel
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeSubSection === 'swap' && (
            <div className="space-y-6 animate-fade-in">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                {/* Swap Form */}
                <div className="glass-panel rounded-2xl p-6 glow-accent-sm space-y-6">
                  <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 pb-4 border-b border-darkbg-border">
                    <Calendar className="w-5 h-5 text-brand-500" />
                    Hour Swap Manager
                  </h3>

                  <form onSubmit={handleSwapRequest} className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Target Teacher</label>
                      <select
                        required
                        value={swapReceiverId}
                        onChange={(e) => setSwapReceiverId(e.target.value)}
                        className="w-full glass-input rounded-xl p-2.5 text-xs"
                      >
                        <option value="" disabled className="bg-darkbg-card">-- Select Teacher --</option>
                        {faculties.map(f => (
                          <option key={f.id} value={f.id} className="bg-darkbg-card">
                            {f.name} ({f.department_name}) — teaches {f.assigned_classes || 'No Classes'}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">My Slot Date</label>
                        <input
                          required
                          type="date"
                          value={swapDateA}
                          onChange={(e) => setSwapDateA(e.target.value)}
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">My Period (1-6)</label>
                        <input
                          required
                          type="number"
                          min="1"
                          max="6"
                          value={swapPeriodA}
                          onChange={(e) => setSwapPeriodA(e.target.value)}
                          placeholder="e.g. 3"
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">Target Slot Date (Optional)</label>
                        <input
                          type="date"
                          value={swapDateB}
                          onChange={(e) => setSwapDateB(e.target.value)}
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] text-slate-400 mb-1">Target Period (Optional)</label>
                        <input
                          type="number"
                          min="1"
                          max="6"
                          value={swapPeriodB}
                          onChange={(e) => setSwapPeriodB(e.target.value)}
                          placeholder="e.g. 4"
                          className="w-full glass-input rounded-xl p-2 text-xs"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] text-slate-400 mb-1">Swap Reason</label>
                      <input
                        required
                        type="text"
                        value={swapReason}
                        onChange={(e) => setSwapReason(e.target.value)}
                        placeholder="Details of scheduling conflict"
                        className="w-full glass-input rounded-xl p-2.5 text-xs"
                      />
                    </div>

                    <button
                      type="submit"
                      className="w-full bg-slate-900 border border-slate-800 hover:bg-slate-850 hover:border-slate-700 text-slate-300 font-bold py-2.5 rounded-xl flex items-center justify-center gap-1.5 text-xs transition-all"
                    >
                      <Send className="w-3.5 h-3.5" /> Submit Swap Proposal
                    </button>
                  </form>
                </div>

                {/* Incoming Swaps */}
                <div className="glass-panel rounded-2xl p-6 glow-accent-sm border border-slate-800/80">
                  <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-indigo-400" />
                    Incoming Swap Proposals
                  </h3>
                  {incomingSwaps.length === 0 ? (
                    <div className="p-6 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                      No incoming swap proposals.
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                      {incomingSwaps.map(swap => (
                        <div key={swap.id} className="p-3.5 rounded-xl border border-indigo-500/20 bg-indigo-950/10 text-xs flex justify-between items-start">
                          <div>
                            <h4 className="font-semibold text-slate-200">{swap.sender_name} requests a swap</h4>
                            <p className="text-slate-400 mt-1.5">
                              <span className="font-semibold text-slate-400">Their Period:</span> {swap.date_a} | Period {swap.period_a}
                            </p>
                            {swap.date_b && (
                              <p className="text-slate-400 mt-1">
                                <span className="font-semibold text-slate-400">Your Period:</span> {swap.date_b} | Period {swap.period_b}
                              </p>
                            )}
                            {swap.reason && <p className="text-slate-500 mt-2 italic">"{swap.reason}"</p>}
                          </div>
                          <div className="flex gap-1.5 ml-3 shrink-0">
                            <button 
                              onClick={() => handleSwapResponse(swap.id, 'REJECTED')}
                              className="p-1.5 bg-rose-950/20 border border-rose-900/40 text-rose-400 rounded-lg hover:bg-rose-950/40 transition-all"
                              title="Decline"
                            >
                              <X className="w-4 h-4" />
                            </button>
                            <button 
                              onClick={() => handleSwapResponse(swap.id, 'CONFIRMED')}
                              className="p-1.5 bg-emerald-950/20 border border-emerald-900/40 text-emerald-400 rounded-lg hover:bg-emerald-950/40 transition-all"
                              title="Accept & Confirm"
                            >
                              <Check className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Swap Request Logs and Stats */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-2">
                {/* Swap History List */}
                <div className="lg:col-span-2 glass-panel rounded-2xl p-6 glow-accent-sm border border-slate-800/80">
                  <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                    <FileText className="w-5 h-5 text-indigo-400" />
                    My Swap Request History
                  </h3>
                  {mySwaps.length === 0 ? (
                    <div className="p-6 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                      No swap requests sent or received yet.
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                      {mySwaps.map(s => {
                        const statusColors = {
                          "APPROVED": "bg-emerald-950/50 text-emerald-300 border border-emerald-900/50",
                          "REJECTED": "bg-rose-950/50 text-rose-300 border border-rose-900/50",
                          "REJECTED_RECEIVER": "bg-red-950/50 text-red-300 border border-red-900/50",
                          "PENDING_RECEIVER": "bg-amber-950/30 text-amber-300 border border-amber-900/30",
                          "PENDING_APPROVAL": "bg-indigo-950/30 text-indigo-300 border border-indigo-900/30"
                        };
                        return (
                          <div key={s.id} className="p-3.5 rounded-xl border border-slate-800/80 bg-slate-900/10 text-xs flex justify-between items-start hover:border-slate-700 transition-colors">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className={`text-[10px] px-1.5 py-0.2 rounded font-semibold ${s.is_sender ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20' : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'}`}>
                                  {s.is_sender ? 'Sent' : 'Received'}
                                </span>
                                <span className="font-semibold text-slate-200">
                                  {s.is_sender ? `To: ${s.receiver_name}` : `From: ${s.sender_name}`}
                                </span>
                              </div>
                              <p className="text-slate-400 mt-1.5">
                                <strong>Date:</strong> {s.date_a} | <strong>Period:</strong> {s.period_a}
                              </p>
                              {s.date_b && (
                                <p className="text-slate-400 mt-0.5">
                                  <strong>Target Date:</strong> {s.date_b} | <strong>Target Period:</strong> {s.period_b}
                                </p>
                              )}
                              <p className="text-[10px] text-slate-500 mt-1.5">Submitted: {new Date(s.created_at).toLocaleString()}</p>
                            </div>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${statusColors[s.status] || 'bg-slate-950/50 text-slate-400 border border-slate-900/50'}`}>
                              {s.status.replace('_', ' ')}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* Swaps Done Per Class Metrics */}
                <div className="glass-panel rounded-2xl p-6 glow-accent-sm border border-slate-800/80">
                  <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                    <Calendar className="w-5 h-5 text-brand-500" />
                    Swaps per Class
                  </h3>
                  {swapClassCounts.length === 0 ? (
                    <div className="p-6 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                      No swap history available.
                    </div>
                  ) : (
                    <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1">
                      {swapClassCounts.map(item => (
                        <div key={item.class_name} className="flex justify-between items-center p-3 rounded-xl border border-slate-800/50 bg-slate-900/5 hover:border-slate-800 transition-colors">
                          <span className="text-xs font-semibold text-slate-300">{item.class_name}</span>
                          <span className="text-xs px-2.5 py-1 rounded-full bg-slate-950/80 border border-slate-850 text-brand-400 font-bold font-mono">
                            {item.count} Swaps
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeSubSection === 'duties' && (
            <div className="space-y-6 animate-fade-in">
              {/* Substitution Duties */}
              <div className="glass-panel rounded-2xl p-6 glow-accent-sm border border-slate-800/80">
                <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-400" />
                  Substitution Coverages (Auto-Allocated)
                </h3>
                {substitutions.length === 0 ? (
                  <div className="p-6 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                    No active substitution duties assigned to you.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {substitutions.map(sub => (
                      <div key={sub.id} className="p-4 rounded-xl border border-amber-500/20 bg-amber-950/10 text-xs relative overflow-hidden">
                        <div className="absolute top-0 right-0 w-16 h-16 bg-amber-500/5 rounded-bl-full flex items-center justify-center">
                          <Sparkles className="w-3.5 h-3.5 text-amber-500/50" />
                        </div>
                        <h4 className="font-semibold text-amber-300 flex items-center gap-1.5 mb-2.5">
                          🔔 Coverage Assigned
                        </h4>
                        <div className="space-y-1.5 text-slate-300">
                          <div><span className="text-slate-500">Class:</span> <strong className="text-slate-100">{sub.class_group_name}</strong></div>
                          <div><span className="text-slate-500">Period:</span> <strong className="text-slate-100">Period {sub.period_number}</strong></div>
                          <div><span className="text-slate-500">Date:</span> <strong className="text-slate-100">{sub.date}</strong></div>
                          <div><span className="text-slate-500">Covering for:</span> <strong className="text-slate-100">{sub.original_faculty_name}</strong></div>
                        </div>
                        <p className="text-[10px] text-slate-400 mt-3 bg-slate-950/40 p-2.5 rounded-lg italic border border-slate-800/40">
                          {sub.explanation}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

        </div>
      </div>
    </DashboardLayout>
  );
}
