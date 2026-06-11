import React, { useState } from 'react';
import api from '../api';
import DarwinLogo from './DarwinLogo';

export default function StartScreen({ onStart }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [errors, setErrors] = useState({});
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sessionCreated, setSessionCreated] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const validate = () => {
    const e = {};
    if (!name.trim()) e.name = 'Required';
    if (!email.trim()) e.email = 'Required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) e.email = 'Invalid email';
    setErrors(e);
    return !Object.keys(e).length;
  };

  const handleStart = async (e) => {
    e.preventDefault();
    if (!validate()) return;
    setLoading(true);
    try {
      const res = await api.post('/api/session/create', { candidate_name: name.trim(), candidate_email: email.trim() });
      setSessionId(res.data.session_id);
      setTasks(res.data.tasks);
      setSessionCreated(true);
    } catch { setErrors({ form: 'Could not create session. Please try again.' }); }
    finally { setLoading(false); }
  };

  if (!sessionCreated) {
    return (
      <div className="flex-1 relative z-10 flex overflow-hidden">
        {/* Left — dark brand panel */}
        <div className="hidden lg:flex w-[44%] flex-col justify-between p-12"
          style={{ background: 'linear-gradient(140deg, #022c22 0%, #064e3b 50%, #065f46 100%)' }}>
          <div className="flex items-center gap-3 rise-in">
            <DarwinLogo size={32} color="#34d399" />
            <span className="font-mono text-base font-semibold tracking-[-0.01em] text-emerald-300">Darwin</span>
          </div>
          <div className="rise-in" style={{ animationDelay: '0.1s' }}>
            <p className="font-mono text-[0.62rem] font-semibold tracking-[0.16em] uppercase text-emerald-600 mb-4">
              Behavior Analytics · Building
            </p>
            <h1 className="font-mono text-4xl font-semibold leading-none mb-5"
              style={{ letterSpacing: '-0.045em', color: '#ecfdf5' }}>
              Naturalist for<br />modern developers.
            </h1>
            <p className="text-sm font-light text-emerald-200/70 leading-relaxed mb-10" style={{ letterSpacing: '0.02em' }}>
              Watches how you code with AI — prompting clarity, debugging patterns, iterative thinking. A 7-agent panel judges what makes you effective.
            </p>
            <div className="space-y-4">
              {[
                { num: '01', label: '7-dimension evaluation', sub: 'code · prompting · AI collaboration' },
                { num: '02', label: 'Underspecified tasks', sub: 'requirements revealed through dialogue' },
                { num: '03', label: 'Multi-LLM panel', sub: 'Groq · Mistral · Cohere verdict' },
              ].map(({ num, label, sub }) => (
                <div key={num} className="flex items-start gap-3">
                  <span className="font-mono text-[0.7rem] font-semibold text-emerald-500 w-6 flex-shrink-0 mt-0.5">{num}</span>
                  <div>
                    <div className="font-mono text-sm font-semibold text-emerald-100" style={{ letterSpacing: '-0.02em' }}>{label}</div>
                    <div className="font-mono text-[0.7rem] text-emerald-600 mt-0.5">{sub}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="font-mono text-[0.7rem] text-emerald-800 rise-in" style={{ animationDelay: '0.3s' }}>
            Sindhuja Sivaraman · Senior Engineer AI/ML
          </div>
        </div>

        {/* Right — form */}
        <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto bg-transparent">
          <div className="w-full max-w-[420px] glass-card p-10">
            <div className="flex items-center gap-2.5 mb-8 lg:hidden rise-in">
              <DarwinLogo size={28} />
              <span className="font-mono font-semibold gradient-text">Darwin</span>
            </div>

            <div className="mb-8 rise-in">
              <h2 className="font-mono text-2xl font-semibold text-ink" style={{ letterSpacing: '-0.04em' }}>
                Start your session
              </h2>
              <p className="text-sm font-light text-mid mt-2 leading-relaxed" style={{ letterSpacing: '0.01em' }}>
                Tasks are intentionally underspecified — use the AI panel to discover the full requirements.
              </p>
            </div>

            <form onSubmit={handleStart} noValidate className="space-y-4 rise-in" style={{ animationDelay: '0.15s' }}>
              <div>
                <label className="section-label block mb-2">Full Name</label>
                <input
                  type="text" value={name} autoFocus
                  onChange={e => { setName(e.target.value); setErrors(p => ({...p, name:''})); }}
                  placeholder="Jane Smith"
                  className={`w-full px-4 py-3 rounded-xl border text-sm text-ink bg-white/80 backdrop-blur transition-all focus:outline-none focus:ring-2 focus:ring-darwin-600/30 focus:border-darwin-600 ${errors.name ? 'border-red-400 bg-red-50/50' : 'border-black/10 hover:border-black/20'}`}
                />
                {errors.name && <p className="text-xs text-red-500 mt-1.5">⚠ {errors.name}</p>}
              </div>
              <div>
                <label className="section-label block mb-2">Email</label>
                <input
                  type="email" value={email}
                  onChange={e => { setEmail(e.target.value); setErrors(p => ({...p, email:''})); }}
                  placeholder="jane@company.com"
                  className={`w-full px-4 py-3 rounded-xl border text-sm text-ink bg-white/80 backdrop-blur transition-all focus:outline-none focus:ring-2 focus:ring-darwin-600/30 focus:border-darwin-600 ${errors.email ? 'border-red-400 bg-red-50/50' : 'border-black/10 hover:border-black/20'}`}
                />
                {errors.email && <p className="text-xs text-red-500 mt-1.5">⚠ {errors.email}</p>}
              </div>
              {errors.form && <p className="text-xs text-red-500 bg-red-50 px-3 py-2 rounded-lg">⚠ {errors.form}</p>}
              <button type="submit" disabled={loading} className="darwin-btn-primary w-full py-3 text-sm mt-2">
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                    </svg> Creating session…
                  </span>
                ) : 'Begin Interview →'}
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 relative z-10 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-10">
        <div className="mb-6 rise-in">
          <p className="section-label mb-2">Choose a Task</p>
          <p className="text-sm font-light text-mid" style={{ letterSpacing: '0.01em' }}>
            Each problem is intentionally underspecified. Ask the AI assistant to clarify requirements before writing any code.
          </p>
        </div>
        <div className="space-y-3">
          {tasks.map((task, idx) => (
            <div
              key={task.id}
              onClick={() => onStart({ sessionId, candidateName: name.trim(), candidateEmail: email.trim(), selectedTask: task })}
              className="glass-card p-7 cursor-pointer rise-in"
              style={{ animationDelay: `${0.1 + idx * 0.07}s` }}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <h3 className="mono-heading text-base text-ink">{task.title}</h3>
                <span className="eyebrow flex-shrink-0">{task.difficulty}</span>
              </div>
              <p className="text-[0.92rem] text-mid leading-relaxed mb-4">{task.description}</p>
              <div className="flex items-center justify-between">
                <span className="darwin-tag">→ clarify with AI first</span>
                <span className="font-mono text-[0.68rem] text-mid/50">{String(idx+1).padStart(2,'0')}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}