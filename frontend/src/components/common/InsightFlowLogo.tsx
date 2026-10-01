import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
  showText?: boolean;
  textClassName?: string;
}

export const InsightFlowLogo: React.FC<LogoProps> = ({
  className = '',
  size = 28,
  showText = true,
  textClassName = 'text-slate-900',
}) => {
  return (
    <div className={`inline-flex items-center gap-2.5 ${className}`}>
      {/* Abstract data-flow icon: Three distinct data points converging into an insight node */}
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
        aria-hidden="true"
      >
        {/* Background rounded container */}
        <rect width="32" height="32" rx="8" fill="#2563EB" />
        
        {/* Connecting flow paths */}
        <path
          d="M8 8C14 8 16 16 23 16"
          stroke="#93C5FD"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
        <path
          d="M8 16H23"
          stroke="#BFDBFE"
          strokeWidth="1.75"
          strokeLinecap="round"
        />
        <path
          d="M8 24C14 24 16 16 23 16"
          stroke="#93C5FD"
          strokeWidth="1.75"
          strokeLinecap="round"
        />

        {/* 3 Source Data Points */}
        <circle cx="8" cy="8" r="2.25" fill="#FFFFFF" />
        <circle cx="8" cy="16" r="2.25" fill="#FFFFFF" />
        <circle cx="8" cy="24" r="2.25" fill="#FFFFFF" />

        {/* Converged Insight Point */}
        <circle cx="23" cy="16" r="3" fill="#FFFFFF" />
        <circle cx="23" cy="16" r="1.5" fill="#2563EB" />
      </svg>

      {showText && (
        <span
          className={`font-bold tracking-tight text-lg leading-none ${textClassName}`}
        >
          Insight<span className="text-blue-600">Flow</span>
        </span>
      )}
    </div>
  );
};
