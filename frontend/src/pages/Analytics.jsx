import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { analytics as analyticsApi } from '../api/endpoints';
import { DistributionChart, RankBarChart, RevenueTrendChart } from '../components/charts';
import {
  BentoCell, ErrorState, Loading, PageHeader, StatCard, UploadPrompt, rupees,
} from '../components/ui';

const PERIODS = [
  ['7', '7 days'],
  ['30', '30 days'],
  ['90', '90 days'],
  ['365', '1 year'],
];

export default function Analytics() {
  const [period, setPeriod] = useState('30');
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['analytics', period],
    queryFn: () => analyticsApi.get(period),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  if (!data.has_data) {
    return (
      <>
        <PageHeader title="Analytics" />
        <UploadPrompt
          title="No Sales Data Yet"
          desc="Analytics is computed entirely from your uploaded sales history. Upload it to see revenue trends, top items, and your busiest days."
        />
      </>
    );
  }

  const { kpis, chart_data: chart } = data;

  return (
    <>
      <PageHeader title="Analytics" subtitle="Revenue, profit, and demand patterns from your own sales records.">
        <div className="flex gap-2 flex-wrap">
          {PERIODS.map(([value, label]) => (
            <button
              key={value}
              type="button"
              className={`btn btn-sm ${period === value ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setPeriod(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </PageHeader>

      <div className="bento">
        <BentoCell span={2}>
          <StatCard flat label="Total Revenue" value={kpis.total_revenue} prefix="₹" icon="bi-currency-rupee" tone="success" change={kpis.wow_change} />
        </BentoCell>
        <BentoCell span={2}>
          <StatCard flat label="Total Profit" value={kpis.total_profit} prefix="₹" icon="bi-graph-up-arrow" tone="success" />
        </BentoCell>
        <BentoCell span={2}>
          <StatCard flat label="Avg Order Value" value={kpis.avg_order_value} prefix="₹" icon="bi-tag" tone="info" />
        </BentoCell>

        <BentoCell span={6}>
          <div className="flex justify-between items-center mb-4">
            <span className="card-title">Revenue &amp; Profit</span>
            <span className="text-xs text-muted">Total cost {rupees(kpis.total_cost)} · {kpis.total_orders} records</span>
          </div>
          <RevenueTrendChart labels={chart.daily_labels} revenue={chart.daily_revenue} profit={chart.daily_profit} />
        </BentoCell>

        <BentoCell span={3}>
          <span className="card-title">Top Items</span>
          <div className="mt-4">
            {chart.top_items_labels?.length ? (
              <RankBarChart labels={chart.top_items_labels} values={chart.top_items_revenue} />
            ) : (
              <p className="text-sm text-muted">Your sales file has no item names, so per-item ranking isn’t available.</p>
            )}
          </div>
        </BentoCell>

        <BentoCell span={3}>
          <span className="card-title">Revenue by Day of Week</span>
          <div className="mt-4">
            <DistributionChart labels={chart.dow_labels} values={chart.dow_data} />
          </div>
        </BentoCell>

        {chart.hour_data?.length > 0 && (
          <BentoCell span={6}>
            <span className="card-title">Revenue by Hour</span>
            <div className="mt-4">
              <DistributionChart
                labels={chart.hour_data.map((h) => `${h.hour}:00`)}
                values={chart.hour_data.map((h) => h.revenue)}
              />
            </div>
          </BentoCell>
        )}
      </div>
    </>
  );
}
