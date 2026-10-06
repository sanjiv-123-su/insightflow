import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { MonthlyRevenuePoint } from '../../types';

import { TrendingUp } from 'lucide-react';

interface RevenueTrendChartProps {
  data: MonthlyRevenuePoint[];
  title?: string;
  subtitle?: string;
  height?: number;
}

const formatCurrency = (value: number) => {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value?: number; payload?: MonthlyRevenuePoint }[];
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const point = payload[0].payload as MonthlyRevenuePoint;
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-lg text-xs">
        <p className="font-bold text-slate-900 mb-1.5">{label}</p>
        <div className="space-y-1">
          <p className="flex items-center justify-between gap-4 text-slate-600">
            <span>Revenue:</span>
            <span className="font-bold text-blue-600 font-mono">
              {new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
              }).format(point.revenue)}
            </span>
          </p>
          <p className="flex items-center justify-between gap-4 text-slate-500">
            <span>Orders:</span>
            <span className="font-medium text-slate-800 font-mono">{point.orders}</span>
          </p>
          {point.growth_percentage !== null && point.growth_percentage !== undefined && (
            <p className="flex items-center justify-between gap-4 text-slate-500 pt-0.5">
              <span>Growth:</span>
              <span
                className={`font-semibold font-mono text-[11px] px-1.5 py-0.2 rounded border ${
                  point.growth_percentage >= 0
                    ? 'text-emerald-700 bg-emerald-50 border-emerald-200'
                    : 'text-rose-700 bg-rose-50 border-rose-200'
                }`}
              >
                {point.growth_percentage >= 0 ? '+' : ''}
                {point.growth_percentage.toFixed(1)}%
              </span>
            </p>
          )}
        </div>
      </div>
    );
  }
  return null;
};

export const RevenueTrendChart: React.FC<RevenueTrendChartProps> = ({
  data,
  title = 'Revenue Trend',
  subtitle = 'Monthly revenue performance over time',
  height = 320,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center items-center text-center h-[360px]">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3">
          <TrendingUp className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No time-series date column found or date data is empty in this dataset.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-900">{title}</h4>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs text-slate-600 font-medium bg-slate-50 px-2.5 py-1 rounded-lg border border-slate-200">
            <span className="w-2 h-2 rounded-full bg-blue-600"></span>
            Monthly Revenue
          </span>
        </div>
      </div>

      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2563EB" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#2563EB" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" opacity={0.8} vertical={false} />
            <XAxis
              dataKey="period"
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
              tickFormatter={formatCurrency}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="revenue"
              stroke="#2563EB"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#revenueGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
