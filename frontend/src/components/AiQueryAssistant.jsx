import React, { useState } from 'react';
import { Bot, Sparkles, Send, Loader2, Info } from 'lucide-react';
import { API_BASE_URL } from '../context/AuthContext';

export const AiQueryAssistant = () => {
  const [query, setQuery] = useState('');
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setResponse(null);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/api/hod/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ query: query.trim() })
      });
      const data = await res.json();
      if (res.ok) {
        setResponse(data);
      } else {
        setResponse({ message: "An error occurred while processing your query.", data: [] });
      }
    } catch (err) {
      console.error(err);
      setResponse({ message: "Network error. Please try again.", data: [] });
    } finally {
      setLoading(false);
    }
  };

  const suggestionQueries = [
    "Who is free on Monday period 1",
    "Who is overloaded?",
    "Who teaches Machine Learning",
    "Where is Santhi on Tuesday"
  ];

  return (
    <div className="glass-panel rounded-2xl p-6 glow-accent-sm animate-slide-up mt-6 border border-brand-500/30">
      <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2 mb-4">
        <Bot className="w-5 h-5 text-brand-400" />
        AI Query Assistant
      </h3>

      <div className="text-xs text-slate-400 mb-4 flex items-center gap-2 bg-slate-900/50 p-3 rounded-xl border border-slate-800">
        <Info className="w-4 h-4 text-brand-400 shrink-0" />
        <span>Ask questions in plain English to instantly query the scheduling database. Example: <em>"Who is free on Monday period 1?"</em></span>
      </div>

      <form onSubmit={handleSubmit} className="relative mb-6">
        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask the Adaptive Engine Core..."
            className="w-full bg-slate-950/80 border border-slate-700/80 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500/50 transition-all placeholder:text-slate-500"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-brand-500 hover:bg-brand-600 disabled:bg-slate-800 disabled:text-slate-500 text-white rounded-xl px-5 flex items-center justify-center transition-colors border border-brand-400/20 shadow-lg shadow-brand-500/20 shrink-0"
          >
            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </form>

      <div className="flex flex-wrap gap-2 mb-6">
        {suggestionQueries.map((sq, idx) => (
          <button
            key={idx}
            onClick={() => setQuery(sq)}
            className="text-[10px] bg-slate-900 border border-slate-700/50 hover:bg-brand-500/20 hover:border-brand-500/30 text-slate-300 px-3 py-1.5 rounded-full transition-colors flex items-center gap-1.5"
          >
            <Sparkles className="w-3 h-3 text-brand-400" />
            {sq}
          </button>
        ))}
      </div>

      {response && (
        <div className="bg-slate-950 rounded-xl p-5 border border-slate-800 animate-fade-in relative overflow-hidden">
          {/* Subtle background glow based on intent */}
          <div className="absolute top-0 right-0 w-32 h-32 bg-brand-500/5 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none"></div>
          
          <div className="flex items-start gap-3 relative z-10">
            <div className="bg-brand-500/20 p-2 rounded-lg border border-brand-500/30 shrink-0">
              <Bot className="w-5 h-5 text-brand-400" />
            </div>
            <div className="space-y-3">
              <p className="text-sm text-slate-200 font-medium">
                {response.message}
              </p>
              
              {response.data && response.data.length > 0 && (
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
                  {response.data.map((item, idx) => (
                    <li key={idx} className="text-xs bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/80 text-slate-300 flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-brand-400 shrink-0"></div>
                      {item}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
