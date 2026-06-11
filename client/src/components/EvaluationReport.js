import React from 'react';
import ReactMarkdown from 'react-markdown';
import DarwinLogo from './DarwinLogo';

const fmt = (v) => (typeof v === 'number' && isFinite(v)) ? v.toFixed(1) : '-';
const scoreColour = (v) => v >= 75 ? 'text-green-600' : v >= 50 ? 'text-amber-600' : 'text-red-600';
const barColour   = (v) => v >= 75 ? 'bg-green-500' : v >= 50 ? 'bg-amber-500' : 'bg-red-500';

function ScoreBar({ value, colour }) {
  return (
    <div className="h-1 w-full bg-gray-100 rounded-full overflow-hidden mt-1.5">
      <div
        className={`h-full rounded-full score-bar-fill ${colour || barColour(value)}`}
        style={{ width: `${Math.min(100, value || 0)}%` }}
      />
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center gap-2">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-widest">{title}</span>
      </div>
      {children}
    </div>
  );
}

const recStyle = (r = '') => {
  const n = r.toLowerCase();
  if (n.includes('strong')) return 'bg-emerald-100 text-emerald-800';
  if (n === 'hire' || n.includes('hire')) return 'bg-green-100 text-green-800';
  if (n.includes('maybe')) return 'bg-amber-100 text-amber-800';
  return 'bg-red-100 text-red-800';
};

export default function EvaluationReport({ evaluation = {}, sessionData, onRestart }) {
  const {
    scores = {}, hiring_recommendation = 'Pending',
    agent_summaries = [], overall_summary = '',
    llm_recommendations = {}, code_review = null, chat_collaboration = null
  } = evaluation;

  const scoreDims = [
    { label: 'Prompting',        key: 'prompting_skill' },
    { label: 'Problem Understanding', key: 'problem_understanding' },
    { label: 'Iteration',        key: 'iteration_refinement' },
    { label: 'Debugging',        key: 'debugging_behavior' },
    { label: 'Production',       key: 'production_thinking' },
    { label: 'Code Quality',     key: 'code_quality' },
    { label: 'AI Collaboration', key: 'chat_collaboration' },
  ];

  return (
    <div className="flex-1 overflow-y-auto bg-gray-50 p-6">
      <div className="max-w-4xl mx-auto space-y-4">

        {/* Header card */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <DarwinLogo size={44} />
            <div>
              <h2 className="text-xl font-bold text-gray-900">Interview Evaluation Report</h2>
              <div className="mt-1 text-sm text-gray-500 space-y-0.5">
                <div>Candidate: <span className="font-medium text-gray-700">{sessionData?.candidateName}</span></div>
                <div>Task: <span className="font-medium text-gray-700">{sessionData?.selectedTask?.title}</span></div>
              </div>
            </div>
          </div>
          <div className="flex flex-col items-end gap-3">
            <span className={`px-4 py-1.5 rounded-lg text-sm font-bold uppercase tracking-wider ${recStyle(hiring_recommendation)}`}>
              {hiring_recommendation}
            </span>
            <div className="text-right">
              <div className={`font-mono text-3xl font-bold ${scoreColour(scores.overall)}`}>{fmt(scores.overall)}</div>
              <div className="text-xs text-gray-400 font-medium">Overall Score</div>
            </div>
          </div>
        </div>

        {/* Score grid */}
        <Section title="Performance Scores">
          <div className="grid grid-cols-2 sm:grid-cols-4 divide-x divide-y divide-gray-100">
            {scoreDims.map(({ label, key }) => {
              const v = scores[key] ?? 0;
              return (
                <div key={key} className="p-4">
                  <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</div>
                  <div className={`font-mono text-2xl font-bold mt-0.5 ${scoreColour(v)}`}>{fmt(v)}</div>
                  <ScoreBar value={v} />
                </div>
              );
            })}
          </div>
        </Section>

        {/* Agent summaries */}
        <Section title="Agent Analysis">
          <div className="divide-y divide-gray-50">
            {agent_summaries.map((a) => (
              <div key={a.agent_role} className="px-5 py-3.5 flex items-start gap-4">
                <div className={`font-mono text-lg font-bold flex-shrink-0 w-14 text-right ${scoreColour(a.score)}`}>
                  {fmt(a.score)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-semibold text-gray-900">{a.agent_role}</div>
                  <p className="text-sm text-gray-500 mt-0.5 leading-relaxed">{a.summary}</p>
                  <div className="font-mono text-xs text-gray-300 mt-1">{a.llm}</div>
                </div>
              </div>
            ))}
          </div>
        </Section>

        {/* Code review */}
        {code_review && (
          <Section title={`Code Review — ${code_review.task_title}`}>
            <div className="p-5 space-y-4">
              {/* Test badge + overall */}
              <div className="flex items-center gap-3 flex-wrap">
                {code_review.tests_total > 0 ? (
                  <span className={`font-mono text-xs font-semibold px-2.5 py-1 rounded-md ${
                    code_review.tests_passed === code_review.tests_total
                      ? 'bg-green-100 text-green-700'
                      : 'bg-red-100 text-red-700'
                  }`}>
                    {code_review.tests_passed}/{code_review.tests_total} tests passed
                  </span>
                ) : (
                  <span className="font-mono text-xs px-2.5 py-1 rounded-md bg-gray-100 text-gray-500">
                    automated tests: n/a ({code_review.language})
                  </span>
                )}
                <span className="ml-auto font-mono text-sm text-gray-500">
                  score: <span className={`font-bold ${scoreColour(code_review.overall_code_score)}`}>{fmt(code_review.overall_code_score)}</span>/100
                </span>
              </div>

              {/* Dimension scores */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {[
                  { label:'Correctness',          val: code_review.correctness_score },
                  { label:'Edge Cases',           val: code_review.edge_case_score },
                  { label:'Code Quality',         val: code_review.quality_score },
                  { label:'Production Readiness', val: code_review.production_score },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</div>
                    <div className={`font-mono text-xl font-bold mt-0.5 ${scoreColour(val)}`}>{fmt(val)}</div>
                    <ScoreBar value={val} />
                  </div>
                ))}
              </div>

              {code_review.llm_summary && (
                <p className="text-sm text-gray-600 leading-relaxed">{code_review.llm_summary}</p>
              )}

              {/* Notes */}
              {[...(code_review.quality_notes||[]), ...(code_review.production_notes||[])].length > 0 && (
                <div className="space-y-1.5">
                  {[...(code_review.quality_notes||[]), ...(code_review.production_notes||[])].map((n, i) => {
                    const isWarn = /no |lack|missing|without/i.test(n);
                    return (
                      <div key={i} className={`text-xs px-3 py-1.5 border-l-2 rounded-r-md leading-relaxed ${
                        isWarn ? 'border-amber-400 bg-amber-50 text-amber-700' : 'border-green-400 bg-green-50 text-green-700'
                      }`}>{n}</div>
                    );
                  })}
                </div>
              )}

              {code_review.final_code_snippet && (
                <div>
                  <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Submitted Code</div>
                  <pre className="font-mono text-xs bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto leading-relaxed">{code_review.final_code_snippet}</pre>
                </div>
              )}
            </div>
          </Section>
        )}

        {/* Chat collaboration */}
        {chat_collaboration && (
          <Section title="AI Collaboration Analysis">
            <div className="p-5 space-y-4">
              <div className="flex gap-6 text-sm text-gray-500 flex-wrap">
                <span><strong className="text-gray-900">{chat_collaboration.total_prompts}</strong> prompts sent</span>
                <span>avg <strong className="text-gray-900">{chat_collaboration.avg_prompt_length}</strong> chars</span>
                <span className="ml-auto font-mono text-sm">
                  collaboration: <span className="font-bold text-violet-600">{fmt(chat_collaboration.overall_chat_score)}</span>/100
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {[
                  { label:'Prompt Clarity',       val: chat_collaboration.prompt_clarity },
                  { label:'Context Loading',       val: chat_collaboration.context_loading },
                  { label:'Iterative Refinement',  val: chat_collaboration.iterative_refinement },
                  { label:'Understanding Depth',   val: chat_collaboration.understanding_depth },
                  { label:'Token Efficiency',      val: chat_collaboration.token_efficiency },
                  { label:'AI as Tool',            val: chat_collaboration.ai_as_tool_score },
                ].map(({ label, val }) => (
                  <div key={label}>
                    <div className="text-xs text-gray-400 font-medium uppercase tracking-wide">{label}</div>
                    <ScoreBar value={val} colour="bg-violet-500" />
                    <div className="font-mono text-xs text-gray-500 mt-1">{fmt(val)}/100</div>
                  </div>
                ))}
              </div>

              {chat_collaboration.summary && (
                <p className="text-sm text-gray-600 leading-relaxed">{chat_collaboration.summary}</p>
              )}

              <div className="grid sm:grid-cols-2 gap-3">
                {chat_collaboration.best_prompt && (
                  <div className="bg-green-50 rounded-lg p-3">
                    <div className="text-xs font-semibold text-green-600 uppercase tracking-wider mb-1.5">💬 Strongest Prompt</div>
                    <p className="text-xs text-green-800 italic leading-relaxed">"{chat_collaboration.best_prompt}"</p>
                  </div>
                )}
                {chat_collaboration.weakest_prompt && (
                  <div className="bg-amber-50 rounded-lg p-3">
                    <div className="text-xs font-semibold text-amber-600 uppercase tracking-wider mb-1.5">⚠ Weakest Prompt</div>
                    <p className="text-xs text-amber-800 italic leading-relaxed">"{chat_collaboration.weakest_prompt}"</p>
                  </div>
                )}
              </div>

              {chat_collaboration.coaching_tip && (
                <div className="flex gap-2.5 bg-violet-50 border border-violet-100 rounded-lg p-3.5">
                  <span className="text-base">💡</span>
                  <div>
                    <div className="text-xs font-semibold text-violet-700 mb-0.5">Coaching Tip</div>
                    <p className="text-sm text-violet-800 leading-relaxed">{chat_collaboration.coaching_tip}</p>
                  </div>
                </div>
              )}
            </div>
          </Section>
        )}

        {/* Overall summary */}
        {overall_summary && (
          <Section title="Overall Assessment">
            <div className="p-5 text-sm text-gray-600 leading-relaxed prose prose-sm max-w-none">
              <ReactMarkdown>{overall_summary}</ReactMarkdown>
            </div>
          </Section>
        )}

        {/* LLM routing */}
        {Object.keys(llm_recommendations).length > 0 && (
          <Section title="LLM Routing">
            <div className="divide-y divide-gray-50">
              {Object.entries(llm_recommendations).map(([model, note]) => (
                <div key={model} className="flex gap-4 px-5 py-2.5 items-start">
                  <span className="font-mono text-xs text-teal-600 flex-shrink-0 w-52">{model}</span>
                  <span className="text-xs text-gray-500 leading-relaxed">{note}</span>
                </div>
              ))}
            </div>
          </Section>
        )}

        <button
          onClick={onRestart}
          className="px-5 py-2.5 bg-gray-900 hover:bg-gray-800 text-white rounded-lg text-sm font-medium transition-colors"
        >
          ← Start New Interview
        </button>

      </div>
    </div>
  );
}