import React from 'react';
import { UploadCloud, ShieldCheck, BarChart3, Lightbulb } from 'lucide-react';

export const ValueStrip: React.FC = () => {
  const capabilities = [
    {
      title: 'Data Upload',
      description: 'Instant CSV & XLSX parsing with auto type inference',
      icon: UploadCloud,
    },
    {
      title: 'Data Quality',
      description: 'Automated null audit, anomaly & duplicate detection',
      icon: ShieldCheck,
    },
    {
      title: 'Analytics',
      description: 'Dynamic revenue, order, and customer cohort calculations',
      icon: BarChart3,
    },
    {
      title: 'Business Insights',
      description: 'Regional trends, performance rankings & decision metrics',
      icon: Lightbulb,
    },
  ];

  return (
    <section className="border-y border-slate-200/90 bg-white py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <p className="text-center text-xs font-semibold uppercase tracking-widest text-slate-400 mb-8">
          Everything you need to move from data to decisions
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8">
          {capabilities.map((cap) => {
            const Icon = cap.icon;
            return (
              <div
                key={cap.title}
                className="flex items-start gap-3.5 p-3 rounded-xl hover:bg-slate-50 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-blue-50 border border-blue-100 flex items-center justify-center text-blue-600 shrink-0">
                  <Icon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {cap.title}
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                    {cap.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
