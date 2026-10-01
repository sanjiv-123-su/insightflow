import React from 'react';
import { Terminal, Play, Database, Table, Copy, Check } from 'lucide-react';

export const SQLPreview: React.FC = () => {
  const [copied, setCopied] = React.useState(false);

  const query = `SELECT
  region,
  SUM(revenue) AS total_revenue
FROM sales
GROUP BY region
ORDER BY total_revenue DESC;`;

  const handleCopy = () => {
    navigator.clipboard.writeText(query);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="py-20 md:py-28 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Column: Heading and Description */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-blue-50 border border-blue-200/60 text-blue-700 text-xs font-semibold uppercase tracking-wider">
              <Terminal className="w-3.5 h-3.5" />
              Developer &amp; Analyst Workspace
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
              From Visual Analysis to SQL
            </h2>

            <p className="text-base text-slate-600 leading-relaxed">
              For analysts who want more control, InsightFlow provides an integrated SQL workspace for exploring data directly. Query transformed tables, compute custom aggregates, and export results with zero friction.
            </p>

            <div className="space-y-3 pt-2 text-sm text-slate-700">
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-600" />
                <span>Standard ANSI SQL dialect powered by analytical compute</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-600" />
                <span>Instant schema auto-completion for columns and tables</span>
              </div>
              <div className="flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-600" />
                <span>Export queries directly into shareable dashboards</span>
              </div>
            </div>
          </div>

          {/* Right Column: Code Editor & Result Table Visual */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-800 bg-slate-900 shadow-xl overflow-hidden text-slate-100 font-mono text-xs">
              {/* Editor Tab Bar */}
              <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-4 py-2.5">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
                    <div className="w-2.5 h-2.5 rounded-full bg-slate-700" />
                  </div>
                  <span className="text-slate-600 mx-1">|</span>
                  <div className="flex items-center gap-1.5 text-slate-300 font-sans text-xs">
                    <Database className="w-3.5 h-3.5 text-blue-400" />
                    <span>query_sales_summary.sql</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
                    title="Copy Query"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                  <button
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-blue-600 hover:bg-blue-500 text-white font-sans text-xs font-semibold shadow-xs transition-colors"
                  >
                    <Play className="w-3 h-3 fill-white" />
                    Run Query
                  </button>
                </div>
              </div>

              {/* Code Snippet Area */}
              <div className="p-5 bg-slate-900 space-y-1 text-slate-200 leading-relaxed">
                <div>
                  <span className="text-blue-400 font-bold">SELECT</span>
                </div>
                <div className="pl-4 text-slate-300">
                  region,
                </div>
                <div className="pl-4">
                  <span className="text-amber-400 font-bold">SUM</span>(revenue){' '}
                  <span className="text-blue-400 font-bold">AS</span> total_revenue
                </div>
                <div>
                  <span className="text-blue-400 font-bold">FROM</span> sales
                </div>
                <div>
                  <span className="text-blue-400 font-bold">GROUP BY</span> region
                </div>
                <div>
                  <span className="text-blue-400 font-bold">ORDER BY</span> total_revenue{' '}
                  <span className="text-blue-400 font-bold">DESC</span>;
                </div>
              </div>

              {/* Result Table Header Bar */}
              <div className="border-t border-slate-800 bg-slate-950/60 px-4 py-2 flex items-center justify-between text-[11px] text-slate-400 font-sans">
                <div className="flex items-center gap-1.5">
                  <Table className="w-3.5 h-3.5 text-blue-400" />
                  <span>Query Results (3 rows returned in 12ms)</span>
                </div>
                <span className="text-emerald-400 font-medium">Status: Success (200)</span>
              </div>

              {/* Result Table */}
              <div className="bg-slate-900/90 overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/40">
                      <th className="py-2.5 px-4 font-semibold uppercase tracking-wider text-[10px]">
                        Region
                      </th>
                      <th className="py-2.5 px-4 font-semibold uppercase tracking-wider text-[10px] text-right">
                        Revenue
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono">
                    <tr className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-4 text-slate-200 font-medium">East</td>
                      <td className="py-2.5 px-4 text-right font-bold text-blue-400">₹8.4M</td>
                    </tr>
                    <tr className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-4 text-slate-200 font-medium">West</td>
                      <td className="py-2.5 px-4 text-right font-bold text-blue-400">₹6.7M</td>
                    </tr>
                    <tr className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-2.5 px-4 text-slate-200 font-medium">South</td>
                      <td className="py-2.5 px-4 text-right font-bold text-blue-400">₹5.1M</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
