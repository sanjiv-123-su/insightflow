import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { CheckCircle2, TrendingUp, Layers, PieChart } from 'lucide-react';

const monthlyComparison = [
  { month: 'May', direct: 180, partner: 120 },
  { month: 'Jun', direct: 220, partner: 160 },
  { month: 'Jul', direct: 270, partner: 190 },
  { month: 'Aug', direct: 310, partner: 230 },
  { month: 'Sep', direct: 390, partner: 280 },
];

export const AnalyticsPreview: React.FC = () => {
  const bullets = [
    'Revenue trends with automatic month-over-month trajectory',
    'Customer performance and high-value account segmentation',
    'Product analysis ranking catalog items by sales volume and margin',
    'Regional performance breakdown across geographic markets',
    'Business KPIs computed instantly from detected columns',
  ];

  return (
    <section id="analytics" className="py-20 md:py-28 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          {/* Left Side: Copy and Bullets */}
          <div className="lg:col-span-5 space-y-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-blue-50 border border-blue-200/60 text-blue-700 text-xs font-semibold uppercase tracking-wider">
              <TrendingUp className="w-3.5 h-3.5" />
              Automated Analytics
            </div>

            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 leading-tight">
              See What Your Data Is Telling You
            </h2>

            <p className="text-base text-slate-600 leading-relaxed">
              Go beyond static spreadsheets and quickly understand trends, performance, and
              hidden opportunities without manual pivot tables or complicated formulas.
            </p>

            <ul className="space-y-3 pt-2">
              {bullets.map((point) => (
                <li key={point} className="flex items-start gap-3 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Right Side: Polished Analytics Visualization Card */}
          <div className="lg:col-span-7">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 sm:p-7 shadow-lg shadow-slate-200/50 space-y-6">
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-2">
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Channel &amp; Category Performance
                  </h3>
                  <p className="text-xs text-slate-500">Direct vs Partner distribution</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1 text-slate-600">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-600" /> Direct
                  </span>
                  <span className="flex items-center gap-1 text-slate-600">
                    <span className="w-2.5 h-2.5 rounded-full bg-indigo-400" /> Partner
                  </span>
                </div>
              </div>

              {/* Bar Chart */}
              <div className="h-56 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={monthlyComparison} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <XAxis dataKey="month" stroke="#94A3B8" fontSize={11} tickLine={false} />
                    <YAxis
                      stroke="#94A3B8"
                      fontSize={11}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `₹${v}k`}
                    />
                    <Tooltip
                      formatter={(val: unknown) => [`₹${Number(val)}k`, 'Sales']}
                      contentStyle={{
                        borderRadius: '8px',
                        border: '1px solid #E2E8F0',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="direct" fill="#2563EB" radius={[4, 4, 0, 0]} maxBarSize={28} />
                    <Bar dataKey="partner" fill="#818CF8" radius={[4, 4, 0, 0]} maxBarSize={28} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Bottom 2 mini widgets: Category Comparison + Regional Overview */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-slate-100">
                {/* Category Comparison */}
                <div className="rounded-xl bg-slate-50/70 p-4 border border-slate-100">
                  <div className="flex items-center justify-between mb-3 text-xs">
                    <span className="font-bold text-slate-900 flex items-center gap-1.5">
                      <PieChart className="w-3.5 h-3.5 text-blue-600" /> Category Share
                    </span>
                    <span className="text-slate-400">Total 100%</span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div>
                      <div className="flex justify-between text-slate-600 mb-1">
                        <span>SaaS Subscriptions</span>
                        <span className="font-semibold text-slate-900">54%</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1 rounded-full overflow-hidden">
                        <div className="bg-blue-600 h-full w-[54%]" />
                      </div>
                    </div>
                    <div>
                      <div className="flex justify-between text-slate-600 mb-1">
                        <span>Professional Services</span>
                        <span className="font-semibold text-slate-900">32%</span>
                      </div>
                      <div className="w-full bg-slate-200 h-1 rounded-full overflow-hidden">
                        <div className="bg-indigo-500 h-full w-[32%]" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Regional Performance */}
                <div className="rounded-xl bg-slate-50/70 p-4 border border-slate-100">
                  <div className="flex items-center justify-between mb-3 text-xs">
                    <span className="font-bold text-slate-900 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-emerald-600" /> Top Region
                    </span>
                    <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                      +14.2% YoY
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">
                    <strong className="text-slate-900">North Territory</strong> accounts for ₹8.4M with the highest average order value of ₹1,320.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
