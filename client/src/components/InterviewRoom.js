import React, { useState, useEffect, useRef } from 'react';
import api from '../api';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';

export default function InterviewRoom({ sessionData, onSubmit }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [code, setCode] = useState('# Write your solution here\n\n');
  const [language, setLanguage] = useState('python');
  const [output, setOutput] = useState(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const endRef = useRef(null);
  const { sessionId, selectedTask } = sessionData;

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => {
    setMessages([{ role: 'assistant', content: `**${selectedTask.title}**\n\n${selectedTask.description}\n\n---\nThis task is intentionally underspecified. Ask me clarifying questions to discover the full requirements before you start coding.` }]);
  }, [selectedTask]);

  const sendChat = async (text, isError = false) => {
    try {
      const res = await api.post('/api/chat', { session_id: sessionId, message: text, task_id: selectedTask.id, is_error_message: isError });
      setMessages(prev => [...prev, { role: 'assistant', content: res.data.response }]);
    } catch (e) { console.error(e); }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: text }]);
    setLoading(true);
    await sendChat(text);
    setLoading(false);
  };

  const handleRun = async () => {
    setLoading(true); setOutput(null);
    try {
      const res = await api.post('/api/code/execute', { session_id: sessionId, code, language, task_id: selectedTask.id });
      const result = res.data;
      setOutput(result);
      if (!result.success && result.error) {
        const msg = `I ran my code and got this error:\n\`\`\`\n${result.error}\n\`\`\`\nCan you help me understand what went wrong?`;
        setMessages(prev => [...prev, { role: 'user', content: msg, isAutoError: true }]);
        await sendChat(msg, true);
      }
    } catch { setOutput({ success: false, error: 'Execution failed.', output: '' }); }
    finally { setLoading(false); }
  };

  const handleSubmit = async () => {
    if (!window.confirm('Submit your session for evaluation?')) return;
    setSubmitting(true);
    try { const res = await api.post('/api/session/submit', { session_id: sessionId }); onSubmit(res.data); }
    catch { alert('Submission failed.'); setSubmitting(false); }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative z-10">
      {/* Task bar */}
      <div className="flex-shrink-0 flex items-center justify-between px-5 py-2.5 bg-white/60 backdrop-blur border-b border-black/5 gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="mono-heading text-sm text-ink">{selectedTask.title}</span>
            <span className="eyebrow">{selectedTask.difficulty}</span>
          </div>
          <p className="text-[0.72rem] text-mid mt-0.5" style={{ letterSpacing: '0.02em' }}>
            Clarify → Code → Submit
          </p>
        </div>
        <button onClick={handleSubmit} disabled={submitting} className="darwin-btn-secondary text-xs">
          {submitting ? '⏳ Evaluating…' : '✓ Submit'}
        </button>
      </div>

      {/* Panels */}
      <div className="flex-1 flex overflow-hidden gap-px" style={{ background: 'rgba(0,0,0,0.06)' }}>
        {/* Chat */}
        <div className="w-[38%] min-w-[280px] flex flex-col bg-white/80 backdrop-blur overflow-hidden">
          <div className="flex-shrink-0 flex items-center gap-2 px-4 py-2 border-b border-black/5">
            <span className="w-1.5 h-1.5 rounded-full bg-darwin-600 blink" />
            <span className="section-label">AI Assistant</span>
          </div>
          <div className="flex-1 overflow-y-auto p-3 flex flex-col gap-2.5">
            {messages.map((msg, i) => (
              <div key={i} className={`flex flex-col max-w-[93%] ${msg.role==='user'||msg.isAutoError ? 'self-end items-end' : 'self-start items-start'}`}>
                <span className="font-mono text-[10px] font-semibold text-mid uppercase tracking-wider mb-1 px-0.5">
                  {msg.isAutoError ? 'error · auto' : msg.role==='user' ? 'you' : 'darwin ai'}
                </span>
                <div className={`px-3 py-2 rounded-xl text-[0.875rem] leading-relaxed ${
                  msg.isAutoError ? 'bg-red-50 border border-red-200 text-red-700 rounded-br-sm'
                  : msg.role==='user' ? 'bg-darwin-600 text-white rounded-br-sm'
                  : 'bg-white border border-black/8 text-ink rounded-bl-sm shadow-sm'
                }`}>
                  <ReactMarkdown components={{
                    code: ({inline,children,...p}) => inline
                      ? <code className="font-mono text-[0.8em] bg-black/8 px-1 py-0.5 rounded" {...p}>{children}</code>
                      : <code className="font-mono text-[0.8em]" {...p}>{children}</code>,
                    pre: ({children}) => <pre className="my-1.5 rounded overflow-auto text-xs">{children}</pre>
                  }}>{msg.content}</ReactMarkdown>
                </div>
              </div>
            ))}
            {loading && (
              <div className="self-start flex flex-col items-start max-w-[93%]">
                <span className="font-mono text-[10px] font-semibold text-mid uppercase tracking-wider mb-1 px-0.5">darwin ai</span>
                <div className="flex gap-1.5 bg-white border border-black/8 px-3 py-2.5 rounded-xl rounded-bl-sm shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-mid dot-1" />
                  <span className="w-1.5 h-1.5 rounded-full bg-mid dot-2" />
                  <span className="w-1.5 h-1.5 rounded-full bg-mid dot-3" />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
          <form onSubmit={handleSend} className="flex-shrink-0 flex gap-2 p-3 border-t border-black/5 bg-white/60">
            <input
              value={input} onChange={e => setInput(e.target.value)}
              placeholder="Ask a clarifying question…" disabled={loading||submitting}
              className="flex-1 px-3 py-2 text-sm border border-black/10 rounded-xl bg-white/80 text-ink focus:outline-none focus:ring-2 focus:ring-darwin-600/20 focus:border-darwin-600 transition disabled:opacity-50"
            />
            <button type="submit" disabled={loading||submitting||!input.trim()} className="darwin-btn-primary px-3 py-2 text-sm">↑</button>
          </form>
        </div>

        {/* Code */}
        <div className="flex-1 flex flex-col bg-white/80 backdrop-blur overflow-hidden">
          <div className="flex-shrink-0 flex items-center gap-2 px-4 py-2 border-b border-black/5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 blink" />
            <span className="section-label">Code Editor</span>
          </div>
          <div className="flex-shrink-0 flex items-center gap-2.5 px-4 py-2 border-b border-black/5">
            <select value={language} onChange={e => setLanguage(e.target.value)} disabled={submitting}
              className="font-mono text-xs px-2.5 py-1.5 border border-black/10 rounded-lg bg-white/80 text-ink cursor-pointer focus:outline-none focus:ring-1 focus:ring-darwin-600/20">
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
            </select>
            <button onClick={handleRun} disabled={loading||submitting} className="darwin-btn-primary text-xs px-3 py-1.5">
              {loading ? '▷ Running…' : '▶ Run'}
            </button>
          </div>
          <div className="flex-1 overflow-hidden">
            <Editor height="100%" language={language} value={code} onChange={v => setCode(v||'')}
              theme="vs-light"
              options={{ minimap:{enabled:false}, fontSize:13, lineNumbers:'on', scrollBeyondLastLine:false, automaticLayout:true, fontFamily:'"JetBrains Mono", "Fira Code", monospace', padding:{top:12} }}
            />
          </div>
          {output && (
            <div className="flex-shrink-0 border-t border-black/5 p-3 bg-white/60 max-h-40 overflow-y-auto">
              <div className={`font-mono text-xs font-semibold mb-1.5 ${output.success?'text-darwin-700':'text-red-600'}`}>
                {output.success ? '✓ output' : '✗ error'}
              </div>
              <pre className={`font-mono text-xs whitespace-pre-wrap ${output.success?'text-darwin-800':'text-red-700'}`}>
                {output.success ? output.output||'(no output)' : output.error}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}