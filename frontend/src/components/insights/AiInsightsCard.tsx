import React, { useState } from 'react';
import {
  Sparkles,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  RotateCw,
  Layers,
  MapPin,
  Lightbulb,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  BrainCircuit,
  Info,
} from 'lucide-react';
import type { AiInsightsResponse } from '../../types';

interface AiInsightsCardProps {
  insights: AiInsightsResponse | null;
  loading: boolean;
  onRegenerate: () => void;
  isRegenerating: boolean;
}

export const AiInsightsCard: React.FC<AiInsightsCardProps> = ({
  insights,
  loading,
  onRegenerate,
  isRegenerating,
}) => {
  const [showFacts, setShowFacts] = useState(false);

  if (loading) {
    return (
      <div className="glass-panel rounded-2xl p-6 border border-brand-500/20 shadow-xl space-y-4 animate-pulse">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-500/20" />
            <div className="space-y-1.5">
              <div className="w-36 h-4 rounded bg-slate-800" />
              <div className="w-48 h-3 rounded bg-slate-900" />
            </div>
          </div>
        </div>
        <div className="space-y-2 py-4">
          <div className="w-3/4 h-6 rounded bg-slate-800" />
          <div className="w-full h-4 rounded bg-slate-900" />
          <div className="w-5/6 h-4 rounded bg-slate-900" />
        </div>
      </div>
    );
  }

  if (!insights) {
    return null;
  }

  const isDecline =
    insights.headline.toLowerCase().includes('decreased') ||
    insights.headline.toLowerCase().includes('declined') ||
    insights.headline.toLowerCase().includes('down');

  const isGrowth =
    insights.headline.toLowerCase().includes('increased') ||
    insights.headline.toLowerCase().includes('grew') ||
    insights.headline.toLowerCase().includes('surged');

  return (
    <div className="glass-panel rounded-2xl p-6 border border-blue-200/80 shadow-xs relative overflow-hidden space-y-6 group animate-in fade-in duration-300">
      {/* Background ambient gradient glow */}
      <div className="absolute -right-20 -top-20 w-80 h-80 bg-blue-50/50 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-4 border-b border-slate-100 relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200/80 flex items-center justify-center text-blue-600 shadow-2xs">
            <Sparkles className="w-5 h-5 text-blue-600" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center gap-1.5">
                AI Business Insights
              </h3>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <ShieldCheck className="w-3 h-3" /> Grounded in Verified Metrics
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Natural language explanation of analytical findings and verified drivers
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[11px] text-slate-600 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-lg font-mono">
            {insights.provider === 'gemini' ? 'Gemini 1.5' : 'Grounded Engine'}
          </span>

          <button
            onClick={onRegenerate}
            disabled={isRegenerating}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white hover:bg-slate-50 border border-slate-200 text-slate-700 hover:text-slate-900 text-xs font-semibold shadow-2xs transition-all disabled:opacity-50 cursor-pointer"
            title="Recompute AI insights against latest metrics"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRegenerating ? 'animate-spin text-blue-600' : ''}`} />
            <span>{isRegenerating ? 'Updating...' : 'Regenerate'}</span>
          </button>
        </div>
      </div>

      {/* Main Headline Banner */}
      <div className="relative z-10 p-5 rounded-2xl bg-gradient-to-r from-blue-50/60 via-slate-50 to-white border border-blue-100 space-y-2">
        <div className="flex items-start gap-3">
          <div
            className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 border ${
              isDecline
                ? 'bg-rose-50 border-rose-200 text-rose-600'
                : isGrowth
                ? 'bg-emerald-50 border-emerald-200 text-emerald-600'
                : 'bg-blue-50 border-blue-200 text-blue-600'
            }`}
          >
            {isDecline ? (
              <TrendingDown className="w-5 h-5" />
            ) : isGrowth ? (
              <TrendingUp className="w-5 h-5" />
            ) : (
              <BrainCircuit className="w-5 h-5" />
            )}
          </div>
          <div>
            <h4 className="text-lg lg:text-xl font-bold text-slate-900 tracking-tight leading-snug">
              {insights.headline}
            </h4>
            <p className="text-xs sm:text-sm text-slate-600 mt-1 leading-relaxed">
              {insights.summary}
            </p>
          </div>
        </div>
      </div>

      {/* Key Driver Cards Grid (Category & Regional Breakdown) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 relative z-10">
        {/* Category Contribution Card */}
        {insights.category_insight && (
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 hover:border-slate-300 transition-colors space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <Layers className="w-3.5 h-3.5 text-blue-600" />
              <span>Category Contribution</span>
            </div>
            <p className="text-sm font-medium text-slate-800 leading-relaxed">
              {insights.category_insight}
            </p>
          </div>
        )}

        {/* Regional Contribution Card */}
        {insights.regional_insight && (
          <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-200/80 hover:border-slate-300 transition-colors space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">
              <MapPin className="w-3.5 h-3.5 text-sky-600" />
              <span>Regional Contribution</span>
            </div>
            <p className="text-sm font-medium text-slate-800 leading-relaxed">
              {insights.regional_insight}
            </p>
          </div>
        )}
      </div>

      {/* Key Drivers & Strategic Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 relative z-10 pt-1">
        {/* Key Drivers */}
        {insights.key_drivers.length > 0 && (
          <div className="space-y-3">
            <h5 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />
              Key Verified Drivers
            </h5>
            <ul className="space-y-2 text-xs text-slate-700">
              {insights.key_drivers.map((driver, idx) => (
                <li key={idx} className="flex items-start gap-2 bg-slate-50/60 p-2.5 rounded-lg border border-slate-200/70">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-1.5 shrink-0" />
                  <span className="leading-relaxed">{driver}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Actionable Recommendations */}
        {insights.recommendations.length > 0 && (
          <div className="space-y-3">
            <h5 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-600" />
              Strategic Recommendations
            </h5>
            <ul className="space-y-2 text-xs text-slate-700">
              {insights.recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-2 bg-slate-50/60 p-2.5 rounded-lg border border-slate-200/70">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 shrink-0" />
                  <span className="leading-relaxed">{rec}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Verified Facts Collapsible Debug/Audit Drawer */}
      <div className="relative z-10 pt-2 border-t border-slate-100">
        <button
          onClick={() => setShowFacts(!showFacts)}
          className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-mono transition-colors cursor-pointer"
        >
          <Info className="w-3.5 h-3.5" />
          <span>{showFacts ? 'Hide Verified Grounding Facts' : 'Inspect Verified Grounding Facts'}</span>
          {showFacts ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>

        {showFacts && (
          <div className="mt-3 p-3 rounded-xl bg-slate-900 border border-slate-800 text-[11px] font-mono text-slate-200 overflow-x-auto max-h-48 animate-in fade-in duration-150">
            <pre>{JSON.stringify(insights.verified_facts, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
};

export default AiInsightsCard;
