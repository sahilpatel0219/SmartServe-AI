import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { notifications as notificationsApi } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import { Card, EmptyState, ErrorState, Loading, PageHeader } from '../components/ui';

const SEVERITY = {
  danger: { icon: 'bi-exclamation-octagon-fill', color: 'var(--danger)' },
  warning: { icon: 'bi-exclamation-triangle-fill', color: 'var(--warning)' },
  info: { icon: 'bi-info-circle-fill', color: 'var(--info)' },
};

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsApi.list,
  });

  const markRead = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllRead = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: () => {
      toast.success('All notifications marked read.');
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={4} />;

  return (
    <>
      <PageHeader
        title="Notifications"
        subtitle={data.unread ? `${data.unread} unread alert(s).` : 'You’re all caught up.'}
      >
        {data.unread > 0 && (
          <button type="button" className="btn btn-outline" onClick={() => markAllRead.mutate()} disabled={markAllRead.isPending}>
            <i className="bi bi-check2-all" /> Mark all read
          </button>
        )}
      </PageHeader>

      {!data.notifications.length ? (
        <EmptyState
          icon="bi-bell-slash"
          title="No Alerts"
          desc="Low-stock, expiry, waste-risk, and health-score alerts appear here once there is data to generate them from."
        />
      ) : (
        <Card>
          {data.notifications.map((n) => {
            const meta = SEVERITY[n.severity] || SEVERITY.info;
            return (
              <div
                key={n.id}
                className="flex items-start gap-3"
                style={{
                  padding: 'var(--space-4) 0',
                  borderBottom: '1px solid var(--hairline)',
                  opacity: n.read ? 0.55 : 1,
                }}
              >
                <i className={`bi ${meta.icon}`} style={{ color: meta.color, marginTop: 3 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="text-sm">{n.message}</div>
                  <div className="text-xs text-faint mt-2">
                    {n.created_at ? new Date(n.created_at).toLocaleString() : ''}
                  </div>
                </div>
                {!n.read && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-sm"
                    onClick={() => markRead.mutate(n.id)}
                    aria-label="Mark read"
                  >
                    <i className="bi bi-check2" />
                  </button>
                )}
              </div>
            );
          })}
        </Card>
      )}
    </>
  );
}
