import React from 'react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from 'recharts';
import type { CategoryRevenuePoint } from '../../types';

import { PieChart as PieIcon } from 'lucide-react';

interface CategoryDonutChartProps {
  data: CategoryRevenuePoint[];
  title?: string;
  subtitle?: string;
  height?: number;
}

const PALETTE = [
  '#2563eb', // primary blue
  '#0d9488', // teal
  '#4f46e5', // indigo
  '#0284c7', // sky
  '#f59e0b', // amber
  '#10b981', // emerald
  '#8b5cf6', // purple
  '#ec4899', // pink
];

interface CustomTooltipProps {
  active?: boolean;
  payload?: { value?: number; payload?: CategoryRevenuePoint }[];
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const point = payload[0].payload as CategoryRevenuePoint;
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-3.5 shadow-lg text-xs">
        <p className="font-bold text-slate-900 mb-1">{point.category}</p>
        <p className="text-blue-600 font-bold font-mono">
          {new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
          }).format(point.revenue)}
        </p>
        <div className="mt-1 flex items-center justify-between gap-4 text-slate-500">
          <span>Share:</span>
          <span className="font-semibold text-slate-800 font-mono">{point.percentage.toFixed(1)}%</span>
        </div>
        <div className="flex items-center justify-between gap-4 text-slate-500">
          <span>Orders:</span>
          <span className="font-semibold text-slate-800 font-mono">{point.orders}</span>
        </div>
      </div>
    );
  }
  return null;
};

export const CategoryDonutChart: React.FC<CategoryDonutChartProps> = ({
  data,
  title = 'Revenue by Category',
  subtitle = 'Breakdown across product segments',
  height = 320,
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center items-center text-center h-[360px]">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3">
          <PieIcon className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No category column identified in this dataset.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col">
      <div className="mb-2">
        <h4 className="text-base font-bold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
      </div>

      <div style={{ width: '100%', height }} className="flex items-center">
        <div className="w-1/2 h-full">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={55}
                outerRadius={85}
                paddingAngle={4}
                dataKey="revenue"
              >
                {data.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={PALETTE[index % PALETTE.length]}
                    stroke="#ffffff"
                    strokeWidth={2}
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend list with share % */}
        <div className="w-1/2 pl-2 space-y-2 max-h-[260px] overflow-y-auto">
          {data.map((item, idx) => (
            <div key={item.category} className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 truncate mr-2">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: PALETTE[idx % PALETTE.length] }}
                />
                <span className="text-slate-700 font-medium truncate" title={item.category}>
                  {item.category}
                </span>
              </div>
              <div className="text-right shrink-0">
                <span className="font-semibold text-slate-900 font-mono">
                  {item.percentage.toFixed(1)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
