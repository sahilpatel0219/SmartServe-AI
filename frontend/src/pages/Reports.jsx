import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { reports as reportsApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { Card, ErrorState, Loading, PageHeader, UploadPrompt } from '../components/ui';

const PERIODS = [
  ['7', '7 days'],
  ['30', '30 days'],
  ['90', '90 days'],
  ['365', '1 year'],
];

const REPORTS = [
  { key: 'sales', label: 'Sales Report', desc: 'Daily revenue and transaction counts', icon: 'bi-currency-rupee', color: 'var(--brand)', flag: 'has_sales', periodic: true },
  { key: 'inventory', label: 'Inventory Report', desc: 'Stock levels, costs, and reorder status', icon: 'bi-box-seam', color: 'var(--warning)', flag: 'has_inventory' },
  { key: 'customers', label: 'Customer Report', desc: 'Customers with visits and total spend', icon: 'bi-people', color: 'var(--info)', flag: 'has_customers' },
  { key: 'staff', label: 'Staff Report', desc: 'Team members, roles, and details', icon: 'bi-person-badge', color: 'var(--brand)', flag: 'has_staff' },
  { key: 'orders', label: 'Order Report', desc: 'Orders with customer, total, type, and status', icon: 'bi-receipt', color: 'var(--success)', flag: 'has_orders' },
];

export default function Reports() {
  const { toast } = useToast();
  const [period, setPeriod] = useState('30');
  const [downloading, setDownloading] = useState('');

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['reports', 'status'],
    queryFn: reportsApi.status,
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={3} />;

  const available = REPORTS.filter((r) => data[r.flag]);

  const download = async (reportType, fmt, usePeriod) => {
    const token = `${reportType}-${fmt}`;
    setDownloading(token);
    try {
      await reportsApi.download(reportType, fmt, usePeriod ? period : undefined);
    } catch (err) {
      toast.error(err.message || 'Download failed.');
    } finally {
      setDownloading('');
    }
  };

  return (
    <>
      <PageHeader title="Reports" subtitle="Download your business data as Excel or PDF. Generated from your uploaded records." />

      {!available.length ? (
        <UploadPrompt title="No Data to Report" desc="Upload sales or inventory data first, and report downloads will appear here." />
      ) : (
        <>
          {data.has_sales && (
            <div className="flex gap-2 flex-wrap mb-6 items-center">
              <span className="text-sm text-muted">Sales period:</span>
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
          )}

          <div className="flex flex-col gap-4" style={{ maxWidth: 640, margin: '0 auto' }}>
            {available.map((report) => (
              <Card
                key={report.key}
                title={report.label}
                subtitle={report.desc}
                icon={report.icon}
                iconColor={report.color}
              >
                <div className="flex gap-2 flex-wrap">
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => download(report.key, 'excel', report.periodic)}
                    disabled={downloading === `${report.key}-excel`}
                  >
                    {downloading === `${report.key}-excel` ? <span className="spinner" /> : <><i className="bi bi-file-earmark-excel" /> Excel</>}
                  </button>
                  <button
                    type="button"
                    className="btn btn-outline btn-sm"
                    onClick={() => download(report.key, 'pdf', report.periodic)}
                    disabled={downloading === `${report.key}-pdf`}
                  >
                    {downloading === `${report.key}-pdf` ? <span className="spinner" /> : <><i className="bi bi-file-earmark-pdf" /> PDF</>}
                  </button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </>
  );
}
