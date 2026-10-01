import React from 'react';
import { LandingNavbar } from '../components/landing/LandingNavbar';
import { Hero } from '../components/landing/Hero';
import { ValueStrip } from '../components/landing/ValueStrip';
import { Features } from '../components/landing/Features';
import { HowItWorks } from '../components/landing/HowItWorks';
import { AnalyticsPreview } from '../components/landing/AnalyticsPreview';
import { DataQualityPreview } from '../components/landing/DataQualityPreview';
import { SQLPreview } from '../components/landing/SQLPreview';
import { CTA } from '../components/landing/CTA';
import { LandingFooter } from '../components/landing/LandingFooter';

export const LandingPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Sticky Clean Navbar */}
      <LandingNavbar />

      {/* Main Content Sections */}
      <main className="flex-1">
        {/* 1. Hero with Live SaaS Visual Preview */}
        <Hero />

        {/* 2. Value Strip: 4 capabilities */}
        <ValueStrip />

        {/* 3. Features: From Raw Data to Business Decisions */}
        <Features />

        {/* 4. How It Works: 4-stage pipeline */}
        <HowItWorks />

        {/* 5. Analytics Preview: Visual trends, category & regional breakdown */}
        <AnalyticsPreview />

        {/* 6. Data Quality Differentiator: Audit report & column indicators */}
        <DataQualityPreview />

        {/* 7. Developer & Analyst SQL Workspace Preview */}
        <SQLPreview />

        {/* 8. Final Conversion CTA */}
        <CTA />
      </main>

      {/* Professional Footer */}
      <LandingFooter />
    </div>
  );
};

export default LandingPage;
