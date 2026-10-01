import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';
import type { RegionRevenuePoint } from '../../types';

import { Globe } from 'lucide-react';

interface RegionBarChartProps {
  data: RegionRevenuePoint[];
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
  payload?: { value?: number; payload?: RegionRevenuePoint }[];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const point = payload[0].payload as RegionRevenuePoint;
    return (
      <div className="rounded-xl border border-slate-700 bg-slate-900/95 p-3 shadow-xl backdrop-blur-md text-xs">
        <p className="font-semibold text-slate-200 mb-1">{point.region}</p>
        <p className="text-cyan-400 font-bold">
          {new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
          }).format(point.revenue)}
        </p>
        <div className="mt-1 flex items-center justify-between gap-4 text-slate-400">
          <span>Share:</span>
          <span className="font-medium text-slate-200">{point.percentage.toFixed(1)}%</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-slate-400">
          <span>Orders:</span>
          <span className="font-medium text-slate-200">{point.orders}</span>
        </div>
      </div>
    );
  }
  return null;
};

export const RegionBarChart: React.FC<RegionBarChartProps> = ({
  data,
  title = 'Revenue by Region',
  subtitle = 'Geographic distribution of sales',
  height = 320,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center items-center text-center h-[360px]">
        <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 mb-3">
          <Globe className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-xs">
          No region column identified in this dataset.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-semibold text-slate-100">{title}</h4>
          <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
        </div>
      </div>

      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.4} vertical={false} />
            <XAxis
              dataKey="region"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              interval={0}
              angle={-25}
              textAnchor="end"
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={formatCurrency}
            />
            <Tooltip content={<CustomTooltip />} />
            <Bar dataKey="revenue" fill="#06b6d4" radius={[6, 6, 0, 0]} maxBarSize={45} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
