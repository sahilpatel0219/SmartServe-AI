import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { ml } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { ForecastChart } from '../components/charts';
import {
  Badge, BentoCell, EmptyState, ErrorState, Loading, PageHeader, ProgressBar, rupees,
} from '../components/ui';

const MATRIX = [
  ['stars', 'Stars', 'High margin, high volume — protect these.', 'success'],
  ['plowhorses', 'Plowhorses', 'Popular but thin margin — reprice or re-cost.', 'info'],
  ['puzzles', 'Puzzles', 'Good margin, low volume — promote these.', 'warning'],
  ['dogs', 'Dogs', 'Low margin, low volume — consider removing.', 'danger'],
];

export default function Report() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const statusQuery = useQuery({ queryKey: ['ml', 'status'], queryFn: ml.status });
  const resultsQuery = useQuery({
    queryKey: ['ml', 'results'],
    queryFn: ml.results,
    // A 404 here just means "no analysis run yet" — not an error worth retrying.
    retry: false,
    enabled: statusQuery.data?.has_enough === true,
  });

  const runMutation = useMutation({
    mutationFn: ml.run,
    onSuccess: () => {
      toast.success('Analysis complete. Your forecasts and insights are ready.');
      queryClient.invalidateQueries({ queryKey: ['ml'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
    },
    onError: (err) => toast.error(err.message),
  });

  if (statusQuery.isLoading) return <Loading rows={3} />;
  if (statusQuery.error) return <ErrorState error={statusQuery.error} onRetry={statusQuery.refetch} />;

  const { sales_count: salesCount, has_enough: hasEnough } = statusQuery.data;

  // The data gate: below 30 sales records the backend refuses to run, and we
  // show the upload prompt rather than anything that looks like a result.
  if (!hasEnough) {
    return (
      <>
        <PageHeader title="AI Report" />
        <EmptyState
          icon="bi-cpu"
          title="Not Enough Data Yet"
          desc={`AI analysis needs at least 30 sales records — you have ${salesCount}. Upload more sales history and this will unlock. We won't estimate from thin data.`}
          actionLabel="Upload Data"
          actionTo="/upload"
        />
        <div style={{ maxWidth: 440, margin: '0 auto' }}>
          <ProgressBar value={Math.min(100, (salesCount / 30) * 100)} />
          <p className="text-xs text-muted text-center mt-2">{salesCount} of 30 records</p>
        </div>
      </>
    );
  }

  const results = resultsQuery.data;
  const noResultsYet = resultsQuery.error?.status === 404 || (!results && !resultsQuery.isLoading);

  return (
    <>
      <PageHeader
        title="AI Report"
        subtitle="Forecast, profitability, waste risk, and health score — all trained on your own data."
      >
        <button
          type="button"
          className="btn btn-primary"
          onClick={() => runMutation.mutate()}
          disabled={runMutation.isPending}
        >
          {runMutation.isPending ? <span className="spinner" /> : <><i className="bi bi-play-fill" /> Run Analysis</>}
        </button>
      </PageHeader>

      {runMutation.isPending && (
        <div className="mb-6">
          <ProgressBar indeterminate />
          <p className="text-xs text-muted mt-2">
            Training on {salesCount} records — forecasting, profitability, waste, health score.
          </p>
        </div>
      )}

      {noResultsYet && !runMutation.isPending && (
        <EmptyState
          icon="bi-play-circle"
          title="No Analysis Run Yet"
          desc="You have enough data. Run the analysis to generate your forecast, menu matrix, waste risk, and health score."
          actionLabel="Run Analysis"
          onAction={() => runMutation.mutate()}
        />
      )}

      {resultsQuery.isLoading && <Loading rows={3} />}

      {results && (
        <div className="bento">
          <BentoCell span={2}>
            <div className="stat-value">{results.health?.total_score != null ? Math.round(results.health.total_score) : '—'}</div>
            <div className="stat-label">Health Score / 100</div>
          </BentoCell>
          <BentoCell span={2}>
            <div className="stat-value">{rupees(results.latest?.waste?.estimated_loss_inr)}</div>
            <div className="stat-label">Estimated Waste Risk</div>
          </BentoCell>
          <BentoCell span={2}>
            <div className="stat-value">{rupees(results.latest?.forecast?.total_forecast)}</div>
            <div className="stat-label">Forecast Total</div>
          </BentoCell>

          {results.forecast_dates?.length > 0 && (
            <BentoCell span={6}>
              <span className="card-title">Revenue Forecast</span>
              <p className="text-xs text-muted mt-2 mb-4">
                Predicted, not guaranteed. Accuracy has not been validated against held-out data yet.
              </p>
              <ForecastChart dates={results.forecast_dates} values={results.forecast_values} />
            </BentoCell>
          )}

          {/* Menu engineering matrix */}
          {MATRIX.map(([key, label, desc, tone]) => (
            <BentoCell span={3} key={key}>
              <div className="flex justify-between items-center">
                <span className="card-title">{label}</span>
                <Badge variant={tone}>{results[key]?.length || 0}</Badge>
              </div>
              <p className="text-xs text-muted mt-2">{desc}</p>
              {results[key]?.length ? (
                <ul style={{ listStyle: 'none', marginTop: 'var(--space-3)' }}>
                  {results[key].slice(0, 6).map((item, i) => (
                    <li
                      key={i}
                      className="flex justify-between items-center text-sm"
                      style={{ padding: '6px 0', borderBottom: i < results[key].length - 1 ? '1px solid var(--hairline)' : 'none' }}
                    >
                      <span className="truncate" style={{ maxWidth: '60%' }}>
                        {typeof item === 'string' ? item : item.item || item.item_name || item.name || '—'}
                      </span>
                      {typeof item === 'object' && item !== null && (
                        <span className="text-muted text-xs tabular-nums">
                          {item.total_revenue !== undefined ? rupees(item.total_revenue) : ''}
                          {item.margin_pct !== undefined ? ` · ${item.margin_pct}%` : ''}
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted mt-2 mb-0">None in this quadrant.</p>
              )}
            </BentoCell>
          ))}

          {results.waste_items?.length > 0 && (
            <BentoCell span={3}>
              <span className="card-title">Highest Waste Risk</span>
              <ul style={{ listStyle: 'none', marginTop: 'var(--space-3)' }}>
                {results.waste_items.map((item, i) => (
                  <li key={i} className="flex justify-between text-sm" style={{ padding: '5px 0', borderBottom: '1px solid var(--hairline)' }}>
                    <span>{item.item || item.item_name || item.name || '—'}</span>
                    <span className="text-warning tabular-nums">{rupees(item.estimated_loss ?? item.loss)}</span>
                  </li>
                ))}
              </ul>
            </BentoCell>
          )}

          {results.insights?.length > 0 && (
            <BentoCell span={3}>
              <span className="card-title">Insights</span>
              <ul style={{ listStyle: 'none', marginTop: 'var(--space-3)' }}>
                {results.insights.slice(0, 8).map((insight) => (
                  <li key={insight._id} className="flex items-start gap-2 text-sm" style={{ padding: '6px 0' }}>
                    <i className="bi bi-lightbulb" style={{ color: 'var(--warning)', marginTop: 3 }} />
                    <span>{insight.text}</span>
                  </li>
                ))}
              </ul>
            </BentoCell>
          )}
        </div>
      )}
    </>
  );
}
