import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';

import { dashboard as dashboardApi } from '../api/endpoints';
import {
  BentoCell, ErrorState, Loading, PageHeader, ProgressBar, StatCard, UploadPrompt, rupees,
} from '../components/ui';

export default function Dashboard() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: dashboardApi.get,
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  const { kpis, data_readiness: readiness, latest_insights: insights, kpi_date } = data;
  const hasAnyData = readiness.items.some((i) => i.done);

  return (
    <>
      <PageHeader
        title="Dashboard"
        subtitle={kpi_date ? `Latest figures from ${kpi_date} — the most recent day in your data.` : 'Your business at a glance.'}
      >
        <Link to="/report" className="btn btn-primary">
          <i className="bi bi-cpu" /> Analyze My Business
        </Link>
      </PageHeader>

      {!hasAnyData ? (
        <UploadPrompt
          title="No Data Yet"
          desc="Upload your sales, inventory, and menu data to activate your dashboard. Every KPI here is computed from your own records — nothing is simulated."
        />
      ) : (
        <div className="bento">
          <BentoCell span={2}>
            <StatCard flat label="Revenue" value={kpis.today_revenue} prefix="₹" icon="bi-currency-rupee" tone="success" />
          </BentoCell>
          <BentoCell span={2}>
            <StatCard flat label="Profit" value={kpis.today_profit} prefix="₹" icon="bi-graph-up-arrow" tone="success" />
          </BentoCell>
          <BentoCell span={2}>
            <StatCard flat label="Orders" value={kpis.today_orders} icon="bi-receipt" tone="info" />
          </BentoCell>

          <BentoCell span={2}>
            <StatCard flat label="Inventory Alerts" value={kpis.inventory_alerts} icon="bi-exclamation-triangle" tone="warning" />
          </BentoCell>
          <BentoCell span={2}>
            <StatCard flat label="Active Customers" value={kpis.active_customers} icon="bi-people" tone="info" />
          </BentoCell>
          <BentoCell span={2}>
            <StatCard flat label="Forecasted Sales" value={kpis.forecasted_sales} prefix="₹" icon="bi-cpu" tone="info" />
          </BentoCell>

          {/* Data readiness */}
          <BentoCell span={3}>
            <div className="flex justify-between items-center mb-5">
              <span className="card-title">Data Readiness</span>
              <span className="badge badge-brand">{readiness.score}%</span>
            </div>
            <ProgressBar value={readiness.score} />
            <div className="mt-5" style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {readiness.items.map((item) => (
                <div
                  key={item.label}
                  className="flex items-center gap-3 text-sm"
                  style={{ padding: '9px 0', borderBottom: '1px solid var(--hairline)' }}
                >
                  <i
                    className={`bi ${item.done ? 'bi-check-circle-fill' : 'bi-circle'}`}
                    style={{ color: item.done ? 'var(--success)' : 'var(--text-faint)', fontSize: '1rem' }}
                  />
                  <span className={item.done ? '' : 'text-muted'}>{item.label}</span>
                </div>
              ))}
            </div>
            {readiness.score < 100 && (
              <Link to="/upload" className="btn btn-outline btn-sm mt-5">
                <i className="bi bi-cloud-upload" /> Add missing data
              </Link>
            )}
          </BentoCell>

          {/* Health score + waste — AI-derived, null until an analysis has run.
              alignSelf: start keeps it sized to its own content instead of
              stretching to match the taller Data Readiness cell beside it. */}
          <BentoCell span={3} style={{ alignSelf: 'start' }}>
            <span className="card-title">AI Signals</span>
            <div
              className="flex mt-5"
              style={{ background: 'var(--glass-bg)', borderRadius: 'var(--r-md)', border: '1px solid var(--glass-border)' }}
            >
              <div className="flex-1 text-center" style={{ padding: 'var(--space-4)' }}>
                <div className="stat-value">{kpis.health_score ?? '—'}</div>
                <div className="stat-label">Health Score {kpis.health_score !== null && <span className="text-muted">/ 100</span>}</div>
              </div>
              <div style={{ width: 1, background: 'var(--hairline)' }} />
              <div className="flex-1 text-center" style={{ padding: 'var(--space-4)' }}>
                <div className="stat-value">{kpis.food_waste === null ? '—' : rupees(kpis.food_waste)}</div>
                <div className="stat-label">Waste Risk</div>
              </div>
            </div>
            {kpis.health_score === null && (
              <p className="text-sm text-muted mt-5 mb-0">
                Run an analysis to generate these. They stay blank until there is enough real data —
                we never show a placeholder score.
              </p>
            )}
          </BentoCell>

          {/* Latest insights */}
          <BentoCell span={6}>
            <span className="card-title">Latest AI Insights</span>
            {insights?.length ? (
              <ul style={{ listStyle: 'none', marginTop: 'var(--space-4)' }}>
                {insights.map((insight) => (
                  <li key={insight._id} className="flex items-start gap-3 text-sm" style={{ padding: '8px 0', borderBottom: '1px solid var(--hairline)' }}>
                    <i className="bi bi-lightbulb" style={{ color: 'var(--warning)', marginTop: 3 }} />
                    <span>{insight.text}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-muted mt-4 mb-0">
                No insights yet. <Link to="/report">Run an analysis</Link> once you have at least 30 days of sales history.
              </p>
            )}
          </BentoCell>
        </div>
      )}
    </>
  );
}
