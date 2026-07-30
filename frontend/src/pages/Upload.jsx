import { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { uploads } from '../api/endpoints';
import { useToast } from '../context/ToastContext';
import {
  Badge, Card, ErrorState, Loading, Modal, PageHeader, ProgressBar,
} from '../components/ui';

const ICONS = {
  sales: 'bi-currency-rupee',
  inventory: 'bi-box-seam',
  menu: 'bi-journal-text',
  orders: 'bi-receipt',
  customers: 'bi-people',
};

export default function Upload() {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [preview, setPreview] = useState(null); // { uploadType, result }

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['uploads'],
    queryFn: uploads.center,
  });

  const validateMutation = useMutation({
    mutationFn: ({ uploadType, file }) => uploads.validate(uploadType, file),
    onSuccess: (result, { uploadType }) => {
      if (result.committed_immediately) {
        toast.success(`${result.row_count} rows imported.`);
        queryClient.invalidateQueries({ queryKey: ['uploads'] });
        queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      } else {
        setPreview({ uploadType, result });
      }
    },
    onError: (err) => toast.error(err.message),
  });

  const confirmMutation = useMutation({
    mutationFn: ({ uploadType, token }) => uploads.confirm(uploadType, token),
    onSuccess: (result) => {
      toast.success(`${result.row_count} rows imported.`);
      setPreview(null);
      // Fresh data changes every downstream screen.
      queryClient.invalidateQueries();
    },
    onError: (err) => toast.error(err.message),
  });

  if (error) return <ErrorState error={error} onRetry={refetch} />;
  if (isLoading || !data) return <Loading rows={3} />;

  return (
    <>
      <PageHeader
        title="Upload Data"
        subtitle="Everything the AI produces is derived from these files. CSV or Excel, validated before anything is saved."
      />

      <Card title="Overall readiness" className="mb-6">
        <div className="flex items-center gap-4">
          <div style={{ flex: 1 }}>
            <ProgressBar value={data.readiness_score} />
          </div>
          <span className="fw-semi tabular-nums">{data.readiness_score}%</span>
        </div>
        <p className="text-sm text-muted mt-4 mb-0">
          {data.done_count} of {data.upload_types.length} data types uploaded. Sales history is the
          one AI forecasting cannot work without — it needs roughly 30 days.
        </p>
      </Card>

      <div className="grid grid-2 gap-4">
        {data.upload_types.map((type) => (
          <UploadCard
            key={type.key}
            type={type}
            busy={validateMutation.isPending && validateMutation.variables?.uploadType === type.key}
            onFile={(file) => validateMutation.mutate({ uploadType: type.key, file })}
          />
        ))}
      </div>

      {data.datasets?.length > 0 && (
        <Card title="Upload history" className="mt-6">
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>File</th>
                  <th style={{ textAlign: 'right' }}>Rows</th>
                  <th>Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {data.datasets.map((d) => (
                  <tr key={d._id}>
                    <td><Badge variant="brand">{d.type}</Badge></td>
                    <td className="truncate" style={{ maxWidth: 260 }}>{d.filename}</td>
                    <td style={{ textAlign: 'right' }}>{d.row_count?.toLocaleString('en-IN')}</td>
                    <td className="text-muted text-sm">
                      {d.uploaded_at ? new Date(d.uploaded_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {preview && (
        <PreviewModal
          uploadType={preview.uploadType}
          result={preview.result}
          busy={confirmMutation.isPending}
          onCancel={() => setPreview(null)}
          onConfirm={() => confirmMutation.mutate({ uploadType: preview.uploadType, token: preview.result.upload_token })}
        />
      )}
    </>
  );
}

function UploadCard({ type, onFile, busy }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handleFiles = (files) => {
    if (files?.length) onFile(files[0]);
  };

  return (
    <div className="card">
      <div className="card-header">
        <div style={{ minWidth: 0 }}>
          <span className="card-title">{type.label}</span>
          <div className="text-muted text-sm mt-2">{type.desc}</div>
        </div>
        {type.done ? (
          <Badge variant="success"><i className="bi bi-check-lg" /> Done</Badge>
        ) : (
          <i className={`bi ${ICONS[type.key]}`} style={{ fontSize: '1.4rem', color: 'var(--text-faint)' }} />
        )}
      </div>
      <div className="card-body">
        <button
          type="button"
          className={`dropzone ${dragging ? 'dragging' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); handleFiles(e.dataTransfer.files); }}
          disabled={busy}
        >
          {busy ? (
            <span className="spinner" />
          ) : (
            <>
              <div className="dropzone-icon"><i className="bi bi-cloud-arrow-up" /></div>
              <div className="fw-semi text-sm">Drop a file or click to browse</div>
              <div className="text-xs text-muted mt-2">CSV or Excel</div>
            </>
          )}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          className="sr-only"
          onChange={(e) => { handleFiles(e.target.files); e.target.value = ''; }}
        />

        <div className="form-text mt-4">Expected columns: {type.columns}</div>
        <a
          href={uploads.templateUrl(type.key)}
          className="btn btn-ghost btn-sm mt-2"
          onClick={(e) => {
            // The template endpoint needs an Authorization header, so fetch it
            // through the API layer rather than letting the browser navigate.
            e.preventDefault();
            downloadTemplate(type.key);
          }}
        >
          <i className="bi bi-download" /> Download template
        </a>
      </div>
    </div>
  );
}

async function downloadTemplate(uploadType) {
  const { default: client } = await import('../api/client');
  const response = await client.get(`/uploads/${uploadType}/template/`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = `smartserve_${uploadType}_template.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function PreviewModal({ uploadType, result, onConfirm, onCancel, busy }) {
  return (
    <Modal
      title={`Preview — ${uploadType}`}
      onClose={onCancel}
      footer={
        <>
          <button type="button" className="btn btn-outline" onClick={onCancel} disabled={busy}>
            Cancel
          </button>
          <button type="button" className="btn btn-primary" onClick={onConfirm} disabled={busy}>
            {busy ? <span className="spinner" /> : `Import ${result.row_count} rows`}
          </button>
        </>
      }
    >
      <p className="text-sm text-muted">
        <strong>{result.filename}</strong> — {result.row_count} rows parsed. Nothing has been saved yet.
      </p>

      {result.has_errors && (
        <div className="alert alert-warning">
          <i className="bi bi-exclamation-triangle-fill" />
          <div>
            <div className="fw-semi">{result.row_errors.length} row issue(s) found</div>
            <ul className="text-xs mt-2" style={{ paddingLeft: '1rem' }}>
              {result.row_errors.slice(0, 8).map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="table-wrap mt-4">
        <table className="data-table">
          <thead>
            <tr>
              {result.preview_cols.map((c) => (
                <th key={c}>{c.replace(/_/g, ' ')}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {result.preview_rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{cell || '—'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Modal>
  );
}
