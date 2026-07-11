import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { ShieldAlert, BarChart3, AlertTriangle } from 'lucide-react';

export const WorkloadHeatmap = ({ workloadData = [] }) => {
  
  // Format data for Recharts
  const chartData = workloadData.map(fac => ({
    name: fac.name ? fac.name.replace("Dr. ", "").replace("Prof. ", "") : "Unknown",
    workload: fac.current_hours || 0,
    capacity: fac.max_hours || 16,
    burnout: Math.round((fac.burnout_risk || 0) * 100),
    ratio: (fac.current_hours || 0) / Math.max(1, fac.max_hours || 16)
  }));

  // Identify high burnout risks
  const highRiskFaculties = workloadData.filter(fac => fac.burnout_risk > 0.6);

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-darkbg border border-darkbg-border p-3 rounded-xl text-xs leading-relaxed shadow-xl">
          <p className="font-bold text-slate-100">{payload[0].name === "workload" ? "Current Workload" : "Max Capacity"}</p>
          <div className="mt-1 space-y-0.5 text-slate-300">
            <p>Dr. {data.name}</p>
            <p>Hours: <span className="font-bold text-slate-100">{data.workload} hrs</span> / {data.capacity} hrs</p>
            <p>Burnout Risk: <span className={`font-bold ${data.burnout > 60 ? 'text-rose-400' : 'text-emerald-400'}`}>{data.burnout}%</span></p>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up">
      {/* Visual Workload Bar Chart */}
      <div className="lg:col-span-2 glass-panel rounded-2xl p-6 glow-accent-sm">
        <h3 className="text-lg font-bold text-slate-100 mb-6 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-brand-500" />
          Faculty Load Allocation
        </h3>
        
        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-500 italic">
            No data available to display workload chart.
          </div>
        ) : (
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2943" vertical={false} />
                <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
                <Bar dataKey="workload" fill="#3b4eff" radius={[4, 4, 0, 0]} name="Current Load" />
                <Bar dataKey="capacity" fill="#1f2943" radius={[4, 4, 0, 0]} name="Max Capacity" opacity={0.5} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Burnout Risk Alerts */}
      <div className="glass-panel rounded-2xl p-6 glow-accent-sm flex flex-col">
        <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-rose-500" />
          Burnout Risk Alerts
        </h3>
        
        <p className="text-xs text-slate-400 mb-4">
          Lightweight machine learning warnings predicting fatigue risk indicators.
        </p>

        <div className="flex-1 overflow-y-auto max-h-[220px] space-y-3 pr-1">
          {highRiskFaculties.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center p-4 border border-dashed border-slate-800 rounded-xl text-slate-500 italic text-xs">
              All faculty members are operating within safe workload fatigue bounds.
            </div>
          ) : (
            highRiskFaculties.map(fac => {
              const riskPercent = Math.round(fac.burnout_risk * 100);
              return (
                <div key={fac.faculty_id} className="p-3 rounded-xl border border-rose-500/20 bg-rose-950/10 text-xs">
                  <div className="flex justify-between items-start">
                    <span className="font-bold text-slate-200">{fac.name}</span>
                    <span className="font-mono bg-rose-500/20 text-rose-300 font-bold px-1.5 py-0.5 rounded text-[10px]">
                      {riskPercent}% Risk
                    </span>
                  </div>
                  <div className="mt-2 text-slate-400 flex items-start gap-1.5 text-[11px]">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                    <span>
                      Approaching max hours limit ({fac.current_hours}/{fac.max_hours}h). Avoid assigning extra substitute periods.
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
