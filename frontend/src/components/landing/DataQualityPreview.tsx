import React from 'react';
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle,
  Database,
} from 'lucide-react';


export const DataQualityPreview: React.FC = () => {
  const columnsQuality = [
    { name: 'customer_id', type: 'VARCHAR', score: 99, status: 'pass' },
    { name: 'revenue', type: 'FLOAT', score: 100, status: 'pass' },
    { name: 'region', type: 'VARCHAR', score: 91, status: 'warning' },
    { name: 'product', type: 'VARCHAR', score: 96, status: 'pass' },
  ];

  return (
    <section id="data-quality" className="py-20 md:py-28 bg-white border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-emerald-50 border border-emerald-200/60 text-emerald-700 text-xs font-semibold uppercase tracking-wider mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            Core Differentiator
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            Know Your Data Before You Trust Your Insights
          </h2>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            InsightFlow helps identify data-quality problems before they affect your executive reporting and business decisions.
          </p>
        </div>

        {/* Visual Quality Report Card */}
        <div className="max-w-4xl mx-auto rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/40 p-6 sm:p-8">
          {/* Card Top: Overall Quality Badge + Audit Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-slate-100 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 shrink-0">
                <Database className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Automated Dataset Health Audit
                </h3>
                <p className="text-xs text-slate-500">
                  Scanned 18,542 rows across 12 schema columns
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="text-right">
                <div className="text-xs text-slate-500 font-medium">Overall Quality</div>
                <div className="text-2xl font-black text-slate-900">94%</div>
              </div>
              <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-bold text-emerald-700 bg-emerald-50 border border-emerald-200">
                <CheckCircle className="w-3.5 h-3.5" /> Excellent
              </span>
            </div>
          </div>

          {/* 4 Summary Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-6 border-b border-slate-100">
            {/* Stat 1: Overall Quality */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-100">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Overall Quality
              </div>
              <div className="text-2xl font-bold text-slate-900">94%</div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                <div className="bg-emerald-600 h-full w-[94%]" />
              </div>
            </div>

            {/* Stat 2: Missing Values */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-100">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Missing Values
              </div>
              <div className="text-2xl font-bold text-slate-900">1.8%</div>
              <div className="text-[11px] text-slate-500 mt-2">
                Across 2 non-critical columns
              </div>
            </div>

            {/* Stat 3: Duplicate Rows */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-100">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Duplicate Rows
              </div>
              <div className="text-2xl font-bold text-slate-900 font-mono">245</div>
              <div className="text-[11px] text-slate-500 mt-2">
                Auto-flagged for deduplication
              </div>
            </div>

            {/* Stat 4: Invalid Values */}
            <div className="p-4 rounded-xl bg-slate-50/70 border border-slate-100">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1">
                Invalid Values
              </div>
              <div className="text-2xl font-bold text-slate-900 font-mono">32</div>
              <div className="text-[11px] text-slate-500 mt-2">
                Type mismatch warnings
              </div>
            </div>
          </div>

          {/* Column Quality Indicators Table */}
          <div className="pt-6">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                Column-Level Quality Indicators
              </h4>
              <span className="text-xs text-slate-400">Sample of schema attributes</span>
            </div>

            <div className="space-y-3">
              {columnsQuality.map((col) => {
                const isPass = col.status === 'pass';
                return (
                  <div
                    key={col.name}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors gap-2 text-xs"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-mono font-bold text-slate-900 bg-white px-2 py-0.5 rounded border border-slate-200">
                        {col.name}
                      </span>
                      <span className="font-mono text-slate-400 text-[11px]">
                        {col.type}
                      </span>
                    </div>

                    <div className="flex items-center gap-4">
                      {/* Bar indicator */}
                      <div className="w-32 bg-slate-200 h-2 rounded-full overflow-hidden hidden sm:block">
                        <div
                          className={`h-full rounded-full ${
                            isPass ? 'bg-emerald-600' : 'bg-amber-500'
                          }`}
                          style={{ width: `${col.score}%` }}
                        />
                      </div>

                      <span className="font-mono font-bold text-slate-900 w-12 text-right">
                        {col.score}%
                      </span>

                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                          isPass
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-amber-50 text-amber-700 border border-amber-200'
                        }`}
                      >
                        {isPass ? (
                          <>
                            <CheckCircle className="w-3 h-3" /> Clean
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="w-3 h-3" /> Check nulls
                          </>
                        )}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
