import React from 'react';
import { UploadCloud, SearchCode, LineChart, CheckCircle } from 'lucide-react';

export const HowItWorks: React.FC = () => {
  const steps = [
    {
      num: '01',
      tag: 'Upload',
      title: 'Upload your CSV or Excel dataset.',
      desc: 'Seamless ingestion supporting multiple sheets, custom delimiters, and automatic encoding detection.',
      icon: UploadCloud,
    },
    {
      num: '02',
      tag: 'Profile',
      title: 'InsightFlow examines structure and data quality.',
      desc: 'Instant column-level statistical audit detecting types, missing values, duplicates, and anomalies.',
      icon: SearchCode,
    },
    {
      num: '03',
      tag: 'Analyze',
      title: 'Explore metrics, trends, and patterns.',
      desc: 'Automatic detection of revenue, order, customer, and date attributes for immediate analytics.',
      icon: LineChart,
    },
    {
      num: '04',
      tag: 'Understand',
      title: 'Turn your analysis into actionable insights.',
      desc: 'Interactive visual leaderboards, geographic breakdowns, and decision-ready executive reports.',
      icon: CheckCircle,
    },
  ];

  return (
    <section id="how-it-works" className="py-20 md:py-28 bg-white border-y border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-blue-600 mb-2">
            Workflow
          </h2>
          <p className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900">
            How InsightFlow Works
          </p>
          <p className="mt-4 text-base sm:text-lg text-slate-600">
            A continuous four-stage pipeline designed to take you from unorganized spreadsheets to crystal-clear decisions.
          </p>
        </div>

        {/* 4-Step Process with Connecting Line on Desktop */}
        <div className="relative">
          {/* Connecting line on desktop */}
          <div
            className="hidden lg:block absolute top-7 left-12 right-12 h-0.5 bg-slate-200 -z-0"
            aria-hidden="true"
          />

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 sm:gap-6 relative z-10">
            {steps.map((step) => {
              const Icon = step.icon;
              return (
                <div
                  key={step.num}
                  className="flex flex-col items-start bg-white lg:bg-transparent"
                >
                  {/* Step Icon Badge */}
                  <div className="w-14 h-14 rounded-2xl bg-white border-2 border-slate-200 flex items-center justify-center text-slate-700 shadow-xs mb-5 group-hover:border-blue-600">
                    <Icon className="w-6 h-6 text-blue-600" />
                  </div>

                  {/* Step Number & Tag */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-mono text-xs font-bold text-blue-600 tracking-wider">
                      {step.num}
                    </span>
                    <span className="text-xs text-slate-400">&mdash;</span>
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
                      {step.tag}
                    </span>
                  </div>

                  {/* Step Title & Details */}
                  <h3 className="text-base font-bold text-slate-900 mb-2 leading-snug">
                    {step.title}
                  </h3>
                  <p className="text-xs text-slate-600 leading-relaxed">
                    {step.desc}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};
