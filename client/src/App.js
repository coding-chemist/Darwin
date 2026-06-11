import React, { useState } from 'react';
import StartScreen from './components/StartScreen';
import InterviewRoom from './components/InterviewRoom';
import EvaluationReport from './components/EvaluationReport';
import DarwinLogo from './components/DarwinLogo';

export default function App() {
  const [stage, setStage] = useState('start');
  const [sessionData, setSessionData] = useState(null);
  const [evaluationData, setEvaluationData] = useState(null);

  return (
    <div className="flex flex-col h-screen overflow-hidden relative z-10">
      {/* Frosted nav — exact match to coding-chemist */}
      <header className="flex-shrink-0 flex items-center justify-between px-6 h-[52px] z-50" style={{background:"rgba(245,245,247,0.82)",backdropFilter:"saturate(180%) blur(24px)",WebkitBackdropFilter:"saturate(180%) blur(24px)",borderBottom:"1px solid rgba(0,0,0,0.07)"}}>
        <div className="flex items-center gap-2.5">
          <DarwinLogo size={26} />
          <span className="font-mono text-[0.82rem] font-semibold tracking-[-0.01em] text-ink">
            <span className="gradient-text">Darwin</span>
          </span>
        </div>
        <div className="flex items-center gap-4">
          {stage === 'interview' && sessionData && (
            <span className="font-mono text-xs text-mid">
              {sessionData.candidateName}
            </span>
          )}
          {stage === 'evaluation' && (
            <button
              onClick={() => { setSessionData(null); setEvaluationData(null); setStage('start'); }}
              className="font-mono text-xs text-mid hover:text-ink transition-colors"
            >← new session</button>
          )}
          <a href="https://github.com/coding-chemist" target="_blank" rel="noreferrer"
            className="font-mono text-[0.73rem] font-medium text-mid hover:text-ink transition-colors tracking-[0.03em]">
            GitHub ↗
          </a>
        </div>
      </header>

      {stage === 'start'      && <StartScreen onStart={d => { setSessionData(d); setStage('interview'); }} />}
      {stage === 'interview'  && <InterviewRoom sessionData={sessionData} onSubmit={ev => { setEvaluationData(ev); setStage('evaluation'); }} />}
      {stage === 'evaluation' && <EvaluationReport evaluation={evaluationData} sessionData={sessionData} onRestart={() => { setSessionData(null); setEvaluationData(null); setStage('start'); }} />}
    </div>
  );
}