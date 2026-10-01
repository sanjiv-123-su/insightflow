import React from 'react';
import type { LucideIcon } from 'lucide-react';


interface FeatureCardProps {
  title: string;
  description: string;
  icon: LucideIcon;
  badge?: string;
}

export const FeatureCard: React.FC<FeatureCardProps> = ({
  title,
  description,
  icon: Icon,
  badge,
}) => {
  return (
    <div className="group relative rounded-2xl border border-slate-200 bg-white p-7 transition-all duration-200 hover:border-slate-300 hover:shadow-md">
      <div className="flex items-center justify-between mb-5">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-center text-slate-700 group-hover:bg-blue-50 group-hover:text-blue-600 group-hover:border-blue-100 transition-colors">
          <Icon className="w-6 h-6" />
        </div>
        {badge && (
          <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full border border-slate-200/60">
            {badge}
          </span>
        )}
      </div>

      <h3 className="text-lg font-bold text-slate-900 tracking-tight mb-2">
        {title}
      </h3>
      <p className="text-sm text-slate-600 leading-relaxed">
        {description}
      </p>
    </div>
  );
};
