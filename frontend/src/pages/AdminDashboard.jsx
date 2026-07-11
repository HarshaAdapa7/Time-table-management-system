import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { DashboardLayout } from '../components/DashboardLayout';
import { WorkloadHeatmap } from '../components/WorkloadHeatmap';
import { ConflictReport } from '../components/ConflictReport';
import { TimetableGrid } from '../components/TimetableGrid';
import { Upload, Play, RefreshCw, FileSpreadsheet, ShieldAlert, ListFilter, LayoutDashboard, Users, BookOpen, FileText, AlertTriangle } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export default function AdminDashboard() {
  const { authenticatedFetch } = useAuth();
  
  // States
  const [stats, setStats] = useState({ faculty: 0, subjects: 0, classes: 0, rooms: 5 });
  const [auditLogs, setAuditLogs] = useState([]);
  const [workloads, setWorkloads] = useState([]);
  const [conflicts, setConflicts] = useState([]);
  const [classes, setClasses] = useState([]);
  const [selectedClassId, setSelectedClassId] = useState('');
  const [timetable, setTimetable] = useState([]);
  const [swaps, setSwaps] = useState([]);
  
  const [solving, setSolving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [uploadMessages, setUploadMessages] = useState({});
  const [activeSubSection, setActiveSubSection] = useState('overview');

  const fetchData = async () => {
    setLoading(true);
    try {
      const wlRes = await authenticatedFetch('/api/admin/reports/workload');
      if (!wlRes.ok) throw new Error('Access Denied');
      const wlData = await wlRes.json();
      setWorkloads(wlData);

      const auditRes = await authenticatedFetch('/api/admin/reports/audit-logs');
      if (!auditRes.ok) throw new Error('Access Denied');
      const auditData = await auditRes.json();
      setAuditLogs(auditData.slice(0, 15)); 

      const conflictRes = await authenticatedFetch('/api/schedule/conflicts');
      if (!conflictRes.ok) throw new Error('Access Denied');
      const conflictData = await conflictRes.json();
      setConflicts(conflictData);

      const clsRes = await authenticatedFetch('/api/schedule/classes');
      if (!clsRes.ok) throw new Error('Access Denied');
      const clsData = await clsRes.json();
      setClasses(clsData);
      
      const swapsRes = await authenticatedFetch('/api/hod/swaps/list');
      if (!swapsRes.ok) throw new Error('Access Denied');
      const swapsData = await swapsRes.json();
      setSwaps(swapsData.slice(0, 15));
      
      if (clsData.length > 0 && !selectedClassId) {
        setSelectedClassId(clsData[0].id.toString());
      }

      setStats({
        faculty: wlData.length,
        subjects: 7, 
        classes: clsData.length,
        rooms: 5
      });
    } catch (err) {
      console.error("Error fetching admin data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (selectedClassId) {
      fetchClassTimetable(selectedClassId);
    }
  }, [selectedClassId]);

  const fetchClassTimetable = async (classId) => {
    try {
      const res = await authenticatedFetch(`/api/schedule/class/${classId}`);
      const data = await res.json();
      setTimetable(data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploadMessages(prev => ({ ...prev, [type]: { status: 'PENDING', text: 'Uploading...' } }));

    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/api/admin/upload/${type}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Upload failed');

      setUploadMessages(prev => ({ ...prev, [type]: { status: 'SUCCESS', text: data.message } }));
      fetchData();
    } catch (err) {
      setUploadMessages(prev => ({ ...prev, [type]: { status: 'ERROR', text: err.message } }));
    }
  };

  const runSolver = async () => {
    setSolving(true);
    try {
      const res = await authenticatedFetch('/api/admin/generate-base', { method: 'POST' });
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail?.reason || data.detail || 'Failed to solve timetable');
      }

      alert(`Success! Generated timetable with ${data.slots_created} slots.`);
      fetchData();
      if (selectedClassId) fetchClassTimetable(selectedClassId);
    } catch (err) {
      alert(err.message);
    } finally {
      setSolving(false);
    }
  };

  const navigationItems = [
    { id: 'overview', name: 'Overview Console', icon: LayoutDashboard },
    { id: 'ingestor', name: 'CSV Data Ingestor', icon: FileSpreadsheet },
    { id: 'workloads', name: 'Faculty Workloads', icon: Users },
    { id: 'schedules', name: 'Class Schedules', icon: BookOpen },
    { id: 'swaps', name: 'Swap Tracking', icon: RefreshCw }
  ];

  return (
    <DashboardLayout title="Admin Control Room">
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Sidebar Nav */}
        <aside className="w-full lg:w-64 shrink-0 glass-panel rounded-2xl p-4 border border-slate-800/80 space-y-1.5 print-hidden">
          <div className="px-3 mb-4">
            <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Administration</div>
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
              </button>
            );
          })}
        </aside>

        {/* Content Area */}
        <div className="flex-1 w-full space-y-6">
          
          {activeSubSection === 'overview' && (
            <div className="space-y-6 animate-fade-in">
              {/* Stats Grid */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
                {Object.entries({
                  'Total Faculty': stats.faculty,
                  'Active Classes': stats.classes,
                  'Total Subjects': stats.subjects,
                  'Classrooms': stats.rooms
                }).map(([key, val]) => (
                  <div key={key} className="glass-panel rounded-2xl p-5 border border-darkbg-border flex flex-col justify-between">
                    <span className="text-xs text-slate-500 font-semibold uppercase tracking-wider">{key}</span>
                    <span className="text-3xl font-bold text-slate-100 font-mono mt-2">{val}</span>
                  </div>
                ))}
              </div>

              {/* Solver Trigger & Conflicts Alert */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                  {conflicts.length > 0 && (
                    <div className="p-4 bg-rose-950/20 border border-rose-900/30 rounded-2xl flex items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <ShieldAlert className="w-5 h-5 text-rose-400 shrink-0" />
                        <div>
                          <h4 className="text-sm font-bold text-slate-200">{conflicts.length} Active System Conflicts</h4>
                          <p className="text-xs text-slate-400">Timetable slots have structural overlapping. Click Schedules to resolve them.</p>
                        </div>
                      </div>
                      <button onClick={() => setActiveSubSection('schedules')} className="text-xs font-semibold text-rose-400 hover:text-rose-300">
                        Resolve Conflicts
                      </button>
                    </div>
                  )}
                  
                  <div className="glass-panel rounded-2xl p-6 glow-accent-sm">
                    <h3 className="text-lg font-bold text-slate-100 mb-4">Solver Constraints Status</h3>
                    <div className="space-y-2.5 text-xs text-slate-300">
                      <div className="flex justify-between py-2 border-b border-slate-800">
                        <span>Workload Threshold constraint</span>
                        <span className="text-emerald-400 font-semibold">Active (&lt;16h)</span>
                      </div>
                      <div className="flex justify-between py-2 border-b border-slate-800">
                        <span>Consecutive Teaching limits</span>
                        <span className="text-emerald-400 font-semibold">Active (&lt;3h)</span>
                      </div>
                      <div className="flex justify-between py-2">
                        <span>Classroom overlapping avoidance</span>
                        <span className="text-emerald-400 font-semibold">Enforced (Hard)</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="glass-panel rounded-2xl p-6 glow-accent-sm flex flex-col justify-between">
                  <div>
                    <h3 className="text-lg font-bold text-slate-100 mb-3 flex items-center gap-2">
                      <Play className="w-5 h-5 text-emerald-500 fill-emerald-500/20" />
                      CP-SAT Solver Console
                    </h3>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">
                      Calculates optimal teaching slots satisfying base loads, room availability, and teacher schedules.
                    </p>
                  </div>
                  <button
                    onClick={runSolver}
                    disabled={solving}
                    className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 px-4 rounded-xl flex items-center justify-center gap-2 text-xs transition-all shadow-md shadow-emerald-600/25 hover:scale-[1.01]"
                  >
                    {solving ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        Solving Constraints...
                      </>
                    ) : (
                      <>
                        <Play className="w-4 h-4 fill-white" /> Compute Base Timetable
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Audit Log Trail */}
              <div className="glass-panel rounded-2xl p-6 glow-accent-sm">
                <h3 className="text-lg font-bold text-slate-100 mb-4">Scheduling Audit Trail</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-darkbg-border text-slate-500 font-semibold">
                        <th className="py-2.5">Action type</th>
                        <th className="py-2.5">Details</th>
                        <th className="py-2.5">Actor</th>
                        <th className="py-2.5 text-right">Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLogs.map(log => (
                        <tr key={log.id} className="border-b border-slate-900/60 hover:bg-slate-900/5">
                          <td className="py-3 font-semibold text-slate-300">
                            <span className={`px-2 py-0.5 rounded text-[10px] ${
                              log.action_type === 'BASE_GENERATION' ? 'bg-indigo-950 text-indigo-300' :
                              log.action_type === 'LEAVE_APPROVE' ? 'bg-amber-950 text-amber-300' : 'bg-slate-950 text-slate-400'
                            }`}>
                              {log.action_type}
                            </span>
                          </td>
                          <td className="py-3 text-slate-300/90">{log.details}</td>
                          <td className="py-3 text-slate-400">{log.performer_name}</td>
                          <td className="py-3 text-right text-slate-500">{new Date(log.timestamp).toLocaleTimeString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeSubSection === 'ingestor' && (
            <div className="glass-panel rounded-2xl p-6 glow-accent-sm space-y-6 animate-fade-in">
              <div className="flex justify-between items-center pb-4 border-b border-darkbg-border">
                <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <FileSpreadsheet className="w-5 h-5 text-brand-500" />
                  CSV Bulk Data Ingestor
                </h3>
                <button onClick={fetchData} className="p-2 hover:bg-slate-900 rounded-lg text-slate-400 hover:text-slate-200 transition-all">
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {['classrooms', 'subjects', 'classes', 'faculty'].map((type) => (
                  <div key={type} className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/10 flex flex-col justify-between h-32">
                    <div>
                      <h4 className="font-semibold text-slate-200 capitalize">{type} Upload</h4>
                      <p className="text-[10px] text-slate-500 mt-0.5">Bulk database injection schema</p>
                    </div>
                    
                    <div className="mt-3 flex items-center justify-between gap-4">
                      <label className="bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 font-semibold py-1.5 px-3 rounded-lg text-xs transition-all cursor-pointer flex items-center gap-1">
                        <Upload className="w-3.5 h-3.5" /> Select CSV
                        <input 
                          type="file" 
                          accept=".csv" 
                          onChange={(e) => handleFileUpload(e, type)} 
                          className="hidden" 
                        />
                      </label>
                      
                      {uploadMessages[type] && (
                        <span className={`text-[10px] truncate max-w-[150px] font-medium ${
                          uploadMessages[type].status === 'SUCCESS' ? 'text-emerald-400' :
                          uploadMessages[type].status === 'ERROR' ? 'text-rose-400' : 'text-indigo-400'
                        }`}>
                          {uploadMessages[type].text}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSubSection === 'workloads' && (
            <div className="space-y-6 animate-fade-in">
              <WorkloadHeatmap workloadData={workloads} />
            </div>
          )}

          {activeSubSection === 'schedules' && (
            <div className="space-y-6 animate-fade-in">
              {conflicts.length > 0 && (
                <ConflictReport 
                  unresolvedAllocations={conflicts} 
                  facultyList={workloads} 
                  onOverrideSuccess={fetchData} 
                />
              )}

              <div className="space-y-4">
                <div className="flex items-center gap-4 justify-between">
                  <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    <ListFilter className="w-5 h-5 text-brand-500" />
                    Class Timetable Explorer
                  </h3>
                  <select
                    value={selectedClassId}
                    onChange={(e) => setSelectedClassId(e.target.value)}
                    className="glass-input rounded-xl px-3 py-1.5 text-xs text-slate-200 border-slate-800"
                  >
                    {classes.map(c => (
                      <option key={c.id} value={c.id} className="bg-darkbg-card">{c.name}</option>
                    ))}
                  </select>
                </div>
                <TimetableGrid 
                  slots={timetable} 
                  title={classes.find(c => c.id.toString() === selectedClassId)?.name || 'Class Timetable'}
                  subTitle="Base generated slot matrices"
                />
              </div>
            </div>
          )}

          {activeSubSection === 'swaps' && (
            <div className="glass-panel rounded-2xl p-6 glow-accent-sm animate-fade-in">
              <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <ListFilter className="w-5 h-5 text-indigo-400" />
                Hour Swap Request Tracker
              </h3>
              {swaps.length === 0 ? (
                <div className="p-8 text-center text-slate-500 italic border border-dashed border-slate-800/60 rounded-xl text-xs">
                  No swap requests recorded.
                </div>
              ) : (
                <div className="overflow-x-auto text-xs">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-darkbg-border text-slate-500 font-semibold">
                        <th className="py-2.5">Participants</th>
                        <th className="py-2.5">Slot A</th>
                        <th className="py-2.5">Slot B (Swap)</th>
                        <th className="py-2.5">Reason</th>
                        <th className="py-2.5 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {swaps.map(swap => (
                        <tr key={swap.id} className="border-b border-slate-900/60 hover:bg-slate-900/5">
                          <td className="py-3 font-semibold text-slate-200">
                            {swap.sender_name} ↔ {swap.receiver_name}
                          </td>
                          <td className="py-3 text-slate-300">
                            {swap.date_a} | Period {swap.period_a}
                          </td>
                          <td className="py-3 text-slate-300">
                            {swap.date_b ? `${swap.date_b} | Period ${swap.period_b}` : 'N/A (One-way)'}
                          </td>
                          <td className="py-3 text-slate-400 italic">"{swap.reason}"</td>
                          <td className="py-3 text-right">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              swap.status === 'APPROVED' ? 'bg-emerald-950/50 text-emerald-300 border border-emerald-900/50' :
                              swap.status === 'REJECTED' ? 'bg-rose-950/50 text-rose-300 border border-rose-900/50' :
                              swap.status === 'PENDING_APPROVAL' ? 'bg-indigo-950/50 text-indigo-300 border border-indigo-900/50 animate-pulse' :
                              'bg-slate-950/50 text-slate-400 border border-slate-900/50'
                            }`}>
                              {swap.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </DashboardLayout>
  );
}
