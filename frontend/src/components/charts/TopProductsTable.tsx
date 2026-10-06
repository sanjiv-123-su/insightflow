import React from 'react';
import type { TopProductPoint } from '../../types';
import { Package, Award } from 'lucide-react';


interface TopProductsTableProps {
  products: TopProductPoint[];
  title?: string;
  subtitle?: string;
}

export const TopProductsTable: React.FC<TopProductsTableProps> = ({
  products,
  title = 'Top Products',
  subtitle = 'Best performing products by total sales',
}) => {
  if (!products || products.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center items-center text-center h-[340px]">
        <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 mb-3">
          <Package className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-slate-200">{title}</h4>
        <p className="text-xs text-slate-400 mt-1 max-w-xs">
          No product column identified in this dataset.
        </p>
      </div>
    );
  }

  const maxRevenue = Math.max(...products.map((p) => p.revenue), 1);

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-900">{title}</h4>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>
        <span className="text-xs text-blue-700 font-medium bg-blue-50 px-2.5 py-1 rounded-lg border border-blue-200/80 flex items-center gap-1">
          <Award className="w-3.5 h-3.5" />
          Top {products.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 font-semibold">
              <th className="pb-3 w-12">#</th>
              <th className="pb-3">Product</th>
              <th className="pb-3 text-right">Orders</th>
              {products.some((p) => p.units_sold !== null && p.units_sold !== undefined) && (
                <th className="pb-3 text-right">Units</th>
              )}
              <th className="pb-3 text-right">Revenue</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {products.map((item, index) => {
              const percentage = (item.revenue / maxRevenue) * 100;
              return (
                <tr key={`${item.product}-${index}`} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-3 font-mono text-slate-500">
                    <span
                      className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold ${
                        index === 0
                          ? 'bg-amber-100 text-amber-800 border border-amber-300'
                          : index === 1
                          ? 'bg-slate-100 text-slate-700 border border-slate-300'
                          : index === 2
                          ? 'bg-amber-50 text-amber-800 border border-amber-200'
                          : 'text-slate-500'
                      }`}
                    >
                      {index + 1}
                    </span>
                  </td>
                  <td className="py-3 font-medium text-slate-900">
                    <div className="max-w-[200px] truncate" title={item.product}>
                      {item.product}
                    </div>
                    {/* Visual bar */}
                    <div className="w-24 bg-slate-100 h-1 rounded-full mt-1.5 overflow-hidden">
                      <div
                        className="bg-blue-600 h-full rounded-full"
                        style={{ width: `${percentage}%` }}
                      />
                    </div>
                  </td>
                  <td className="py-3 text-right text-slate-600 font-mono">{item.orders}</td>
                  {products.some((p) => p.units_sold !== null && p.units_sold !== undefined) && (
                    <td className="py-3 text-right text-slate-600 font-mono">
                      {item.units_sold ?? '—'}
                    </td>
                  )}
                  <td className="py-3 text-right font-bold text-slate-900 font-mono">
                    {new Intl.NumberFormat('en-US', {
                      style: 'currency',
                      currency: 'USD',
                      maximumFractionDigits: 0,
                    }).format(item.revenue)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
