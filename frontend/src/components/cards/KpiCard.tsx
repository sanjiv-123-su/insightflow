import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface KpiCardProps {
  title: string;
  value: number | string | null | undefined;
  format?: 'currency' | 'number' | 'percentage' | 'raw';
  change?: number | null;
  changePeriod?: string;
  icon?: React.ReactNode;
  subtitle?: string;
  colorScheme?: 'indigo' | 'emerald' | 'amber' | 'cyan' | 'purple';
}

export const KpiCard: React.FC<KpiCardProps> = ({
  title,
  value,
  format = 'raw',
  change,
  changePeriod = 'vs last period',
  icon,
  subtitle,
  colorScheme = 'indigo',
}) => {
  const formatValue = (val: number | string | null | undefined): string => {
    if (val === null || val === undefined) return '—';
    if (typeof val === 'string') return val;

    switch (format) {
      case 'currency':
        return new Intl.NumberFormat('en-US', {
          style: 'currency',
          currency: 'USD',
          maximumFractionDigits: 2,
        }).format(val);
      case 'number':
        return new Intl.NumberFormat('en-US').format(val);
      case 'percentage':
        return `${val >= 0 ? '+' : ''}${val.toFixed(1)}%`;
      default:
        return String(val);
    }
  };

  const colors = {
    indigo: 'from-indigo-500/10 to-brand-500/5 text-indigo-400 border-indigo-500/20',
    emerald: 'from-emerald-500/10 to-teal-500/5 text-emerald-400 border-emerald-500/20',
    amber: 'from-amber-500/10 to-yellow-500/5 text-amber-400 border-amber-500/20',
    cyan: 'from-cyan-500/10 to-blue-500/5 text-cyan-400 border-cyan-500/20',
    purple: 'from-purple-500/10 to-pink-500/5 text-purple-400 border-purple-500/20',
  };

  const isPositive = change !== undefined && change !== null && change > 0;
  const isNegative = change !== undefined && change !== null && change < 0;
  const isNeutral = change !== undefined && change !== null && change === 0;

  return (
    <div className="glass-panel glass-panel-hover rounded-2xl p-6 relative overflow-hidden group">
      {/* Decorative gradient blur */}
      <div
        className={`absolute -right-8 -top-8 w-28 h-28 rounded-full bg-gradient-to-br ${colors[colorScheme]} blur-2xl opacity-40 group-hover:opacity-70 transition-opacity`}
      />

      <div className="flex items-center justify-between mb-4">
        <span className="text-xs font-semibold tracking-wider uppercase text-slate-400">
          {title}
        </span>
        {icon && (
          <div
            className={`w-10 h-10 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-200 shadow-sm`}
          >
            {icon}
          </div>
        )}
      </div>

      <div className="space-y-1">
        <h3 className="text-2xl lg:text-3xl font-bold tracking-tight text-white">
          {formatValue(value)}
        </h3>

        {(change !== null && change !== undefined) || subtitle ? (
          <div className="flex items-center gap-2 pt-1 flex-wrap">
            {change !== null && change !== undefined && (
              <span
                className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${
                  isPositive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                    : isNegative
                    ? 'bg-rose-500/15 text-rose-400 border border-rose-500/30'
                    : 'bg-slate-700/50 text-slate-400 border border-slate-600/40'
                }`}
              >
                {isPositive && <TrendingUp className="w-3 h-3" />}
                {isNegative && <TrendingDown className="w-3 h-3" />}
                {isNeutral && <Minus className="w-3 h-3" />}
                {isPositive ? `+${change.toFixed(1)}%` : `${change.toFixed(1)}%`}
              </span>
            )}
            <span className="text-xs text-slate-400 font-medium">
              {subtitle || changePeriod}
            </span>
          </div>
        ) : null}
      </div>
    </div>
  );
};
