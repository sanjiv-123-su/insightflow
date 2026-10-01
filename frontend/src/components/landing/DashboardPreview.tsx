import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import {
  TrendingUp,
  ShoppingCart,
  Users,
  DollarSign,
  FileSpreadsheet,
  CheckCircle2,
  ChevronDown,
  Layers,
  Search,
} from 'lucide-react';

const chartData = [
  { month: 'Apr', revenue: 3.2 },
  { month: 'May', revenue: 4.1 },
  { month: 'Jun', revenue: 4.8 },
  { month: 'Jul', revenue: 5.6 },
  { month: 'Aug', revenue: 6.9 },
  { month: 'Sep', revenue: 8.4 },
];

export const DashboardPreview: React.FC = () => {
  return (
    <div className="relative mx-auto w-full max-w-5xl rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-200/60 overflow-hidden text-left">
      {/* SaaS Window Chrome / Application Topbar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/90 px-4 py-2.5 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <div className="flex gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
            <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
            <div className="w-2.5 h-2.5 rounded-full bg-slate-300" />
          </div>
          <span className="ml-2 text-slate-300">|</span>
          <div className="flex items-center gap-1.5 text-slate-700 font-medium ml-1">
            <FileSpreadsheet className="w-3.5 h-3.5 text-blue-600" />
            <span>ecommerce_sales_q3.csv</span>
            <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <CheckCircle2 className="w-2.5 h-2.5" /> Ready
            </span>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-md border border-slate-200 text-slate-400">
            <Search className="w-3 h-3" />
            <span className="text-[11px]">Filter metrics...</span>
          </div>
          <div className="flex items-center gap-1 font-medium text-slate-600">
            <span>Last 6 Months</span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </div>
        </div>
      </div>

      {/* Main SaaS Dashboard Body */}
      <div className="p-5 sm:p-6 space-y-5 bg-white">
        {/* KPI Cards Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          {/* Revenue */}
          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Revenue</span>
              <DollarSign className="w-4 h-4 text-blue-600" />
            </div>
            <div className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              ₹24.5M
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 mt-1">
              <TrendingUp className="w-3 h-3" />
              <span>+12.4% vs prev</span>
            </div>
          </div>

          {/* Orders */}
          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Orders</span>
              <ShoppingCart className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              18,542
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 mt-1">
              <TrendingUp className="w-3 h-3" />
              <span>+5.2% vs prev</span>
            </div>
          </div>

          {/* Customers */}
          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Customers</span>
              <Users className="w-4 h-4 text-indigo-600" />
            </div>
            <div className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              7,821
            </div>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-emerald-600 mt-1">
              <TrendingUp className="w-3 h-3" />
              <span>+8.1% vs prev</span>
            </div>
          </div>

          {/* Growth */}
          <div className="rounded-xl border border-slate-100 bg-slate-50/70 p-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Growth</span>
              <Layers className="w-4 h-4 text-amber-600" />
            </div>
            <div className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              +8.4%
            </div>
            <div className="text-[11px] text-slate-500 mt-1">
              Quarterly MoM index
            </div>
          </div>
        </div>

        {/* Charts & Breakdown Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Revenue Overview Line Chart (2 cols) */}
          <div className="lg:col-span-2 rounded-xl border border-slate-200/90 p-4 sm:p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h4 className="text-sm font-bold text-slate-900">Revenue Overview</h4>
                <p className="text-xs text-slate-500">Monthly trend trajectory</p>
              </div>
              <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-md border border-blue-100">
                Current FY26
              </span>
            </div>

            <div className="h-52 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="heroGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="month"
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={{ stroke: '#E2E8F0' }}
                  />
                  <YAxis
                    stroke="#94A3B8"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(val) => `₹${val}M`}
                  />
                  <Tooltip
                    formatter={(val) => [`₹${val}M`, 'Revenue']}
                    contentStyle={{
                      backgroundColor: '#FFFFFF',
                      borderRadius: '8px',
                      border: '1px solid #E2E8F0',
                      boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
                      fontSize: '12px',
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="revenue"
                    stroke="#2563EB"
                    strokeWidth={2.5}
                    fill="url(#heroGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Revenue by Region Breakdown (1 col) */}
          <div className="rounded-xl border border-slate-200/90 p-4 sm:p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-bold text-slate-900">Revenue by Region</h4>
                <span className="text-[11px] text-slate-400">Total Share</span>
              </div>

              <div className="space-y-3 pt-1">
                {[
                  { region: 'North', amount: '₹8.4M', pct: 34, color: 'bg-blue-600' },
                  { region: 'West', amount: '₹6.8M', pct: 28, color: 'bg-indigo-500' },
                  { region: 'South', amount: '₹5.2M', pct: 21, color: 'bg-emerald-500' },
                  { region: 'East', amount: '₹4.1M', pct: 17, color: 'bg-amber-500' },
                ].map((item) => (
                  <div key={item.region} className="text-xs">
                    <div className="flex justify-between font-medium text-slate-700 mb-1">
                      <span>{item.region}</span>
                      <span className="font-semibold text-slate-900">{item.amount}</span>
                    </div>
                    <div className="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
                      <div
                        className={`${item.color} h-full rounded-full`}
                        style={{ width: `${item.pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500">
              <span>Coverage: 4 zones</span>
              <span className="font-medium text-blue-600">View Map &rarr;</span>
            </div>
          </div>
        </div>

        {/* Top Products Row */}
        <div className="rounded-xl border border-slate-200/90 p-4 sm:p-5">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-bold text-slate-900">Top Products</h4>
            <span className="text-xs text-slate-500 font-medium">Ranked by revenue</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-100 text-slate-400 font-semibold">
                  <th className="pb-2">Product Name</th>
                  <th className="pb-2 text-right">Orders</th>
                  <th className="pb-2 text-right">Units</th>
                  <th className="pb-2 text-right">Revenue</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 font-medium text-slate-700">
                <tr>
                  <td className="py-2.5 font-semibold text-slate-900">Enterprise Cloud Suite</td>
                  <td className="py-2.5 text-right font-mono">4,120</td>
                  <td className="py-2.5 text-right font-mono">8,940</td>
                  <td className="py-2.5 text-right font-bold text-slate-900 font-mono">₹6.8M</td>
                </tr>
                <tr>
                  <td className="py-2.5 font-semibold text-slate-900">Analytics Pro Add-on</td>
                  <td className="py-2.5 text-right font-mono">3,450</td>
                  <td className="py-2.5 text-right font-mono">5,200</td>
                  <td className="py-2.5 text-right font-bold text-slate-900 font-mono">₹4.5M</td>
                </tr>
                <tr>
                  <td className="py-2.5 font-semibold text-slate-900">Automated Pipeline Sync</td>
                  <td className="py-2.5 text-right font-mono">2,890</td>
                  <td className="py-2.5 text-right font-mono">4,100</td>
                  <td className="py-2.5 text-right font-bold text-slate-900 font-mono">₹3.9M</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
