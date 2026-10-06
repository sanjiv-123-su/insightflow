import React from 'react';
import type { TopCustomerPoint } from '../../types';
import { Users, UserCheck } from 'lucide-react';


interface TopCustomersTableProps {
  customers: TopCustomerPoint[];
  title?: string;
  subtitle?: string;
}

export const TopCustomersTable: React.FC<TopCustomersTableProps> = ({
  customers,
  title = 'Top Customers',
  subtitle = 'High-value customer accounts',
}) => {
  if (!customers || customers.length === 0) {
    return (
      <div className="glass-panel rounded-2xl p-6 flex flex-col justify-center items-center text-center h-[340px]">
        <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3">
          <Users className="w-6 h-6" />
        </div>
        <h4 className="text-base font-semibold text-slate-900">{title}</h4>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">
          No customer column identified in this dataset.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-2xl p-6 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-900">{title}</h4>
          <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>
        </div>
        <span className="text-xs text-emerald-700 font-medium bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200 flex items-center gap-1">
          <UserCheck className="w-3.5 h-3.5" />
          Top {customers.length}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-slate-200 text-slate-500 font-semibold">
              <th className="pb-3">Customer</th>
              <th className="pb-3 text-right">Orders</th>
              <th className="pb-3 text-right">Avg. Spend</th>
              <th className="pb-3 text-right">Total Revenue</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {customers.map((item, index) => (
              <tr key={`${item.customer}-${index}`} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-3 font-medium text-slate-900">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700 font-semibold text-[11px] shrink-0">
                      {item.customer.charAt(0).toUpperCase()}
                    </div>
                    <span className="max-w-[150px] truncate" title={item.customer}>
                      {item.customer}
                    </span>
                  </div>
                </td>
                <td className="py-3 text-right text-slate-600 font-mono">{item.orders}</td>
                <td className="py-3 text-right text-slate-600 font-mono">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(item.average_spend)}
                </td>
                <td className="py-3 text-right font-bold text-slate-900 font-mono">
                  {new Intl.NumberFormat('en-US', {
                    style: 'currency',
                    currency: 'USD',
                  }).format(item.revenue)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
