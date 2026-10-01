import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BarChart2, ShieldCheck, Zap } from 'lucide-react';
import { DashboardPreview } from './DashboardPreview';

export const Hero: React.FC = () => {
  return (
    <section className="relative pt-12 pb-20 md:pt-16 md:pb-28 overflow-hidden">
      {/* Subtle radial ambient glow - minimal, non-distracting */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[400px] bg-gradient-to-b from-blue-100/60 to-transparent rounded-full blur-3xl pointer-events-none -z-10"
        aria-hidden="true"
      />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        {/* Category Pill / Trust Indicator */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200/80 text-blue-700 text-xs font-semibold tracking-wider uppercase mb-6 shadow-xs animate-in fade-in duration-300">
          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
          Analytics Platform for Modern Teams
        </div>

        {/* Main Headline */}
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-slate-900 max-w-4xl mx-auto leading-[1.12]">
          Turn Raw Data Into <span className="text-blue-600">Clear Insights</span>
        </h1>

        {/* Supporting Copy */}
        <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl mx-auto font-normal leading-relaxed">
          Upload your data, understand its quality, analyze performance, and
          discover actionable business insights &mdash; all in one platform.
        </p>

        {/* CTA Buttons */}
        <div className="mt-8 sm:mt-10 flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4">
          <Link
            to="/register"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-semibold text-base transition-all shadow-sm hover:shadow-md cursor-pointer"
          >
            <span>Get Started Free</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/dashboard"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-white hover:bg-slate-100 border border-slate-300 text-slate-800 font-semibold text-base transition-colors shadow-xs"
          >
            <BarChart2 className="w-4 h-4 text-slate-500" />
            <span>Explore Dashboard</span>
          </Link>
        </div>

        {/* Quick Micro Value Props */}
        <div className="mt-6 flex items-center justify-center gap-6 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <Zap className="w-3.5 h-3.5 text-blue-600" /> Fast setup
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Automated data validation
          </span>
          <span className="hidden sm:flex items-center gap-1.5">
            CSV &amp; Excel supported
          </span>
        </div>

        {/* Dashboard Visual Preview */}
        <div className="mt-12 sm:mt-16 relative">
          <DashboardPreview />
        </div>
      </div>
    </section>
  );
};
