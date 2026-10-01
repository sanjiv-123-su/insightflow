import React from 'react';
import { Upload, ShieldCheck, BarChart3, Lightbulb } from 'lucide-react';
import { FeatureCard } from './FeatureCard';

export const Features: React.FC = () => {
  const features = [
    {
      title: 'Upload Your Data',
      description:
        'Bring CSV and Excel datasets into InsightFlow and start analyzing them in minutes.',
      icon: Upload,
      badge: 'Step 1',
    },
    {
      title: 'Understand Data Quality',
      description:
        'Automatically identify missing values, duplicates, data types, and potential quality issues.',
      icon: ShieldCheck,
      badge: 'Step 2',
    },
    {
      title: 'Analyze Performance',
      description:
        'Explore revenue, customers, products, regions, trends, and other important business metrics.',
      icon: BarChart3,
      badge: 'Step 3',
    },
    {
      title: 'Discover Insights',
      description:
        'Turn analytical results into clear, understandable business insights.',
      icon: Lightbulb,
      badge: 'Step 4',
    },
  ];

  return (
    <section id="features" className="py-20 md:py-28 bg-slate-50/50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-2">
            Features
          </h2>
          <p className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            From Raw Data to Business Decisions
          </p>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            InsightFlow brings the complete analytics workflow into one place.
          </p>
        </div>

        {/* 4 Feature Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((f) => (
            <FeatureCard
              key={f.title}
              title={f.title}
              description={f.description}
              icon={f.icon}
              badge={f.badge}
            />
          ))}
        </div>
      </div>
    </section>
  );
};
