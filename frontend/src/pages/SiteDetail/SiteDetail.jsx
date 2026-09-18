import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import apiClient from '../../api/client';
import SiteAnalyticsCharts from '../../components/charts/SiteAnalyticsCharts';

function ConfirmDeleteSiteModal({ site, onCancel, onConfirm, deleting, error }) {
  return (
    <div className="modal-backdrop" onClick={onCancel}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>Delete site?</h2>
        {error && <div className="error-banner">{error}</div>}
        <p>
          You&apos;re about to delete <strong>{site.name}</strong> and all of its recorded metrics.
          This cannot be undone.
        </p>
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn btn-danger" onClick={onConfirm} disabled={deleting}>
            {deleting ? 'Deleting...' : 'Delete site'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function SiteDetail() {
  const { projectId, siteId } = useParams();
  const navigate = useNavigate();
  const [site, setSite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError('');
    apiClient
      .get(`/sites/${siteId}`)
      .then(({ data }) => {
        if (!cancelled) setSite(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.response?.data?.detail || 'Could not load site.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [siteId]);

  const confirmDelete = async () => {
    setDeleting(true);
    setDeleteError('');
    try {
      await apiClient.delete(`/sites/${siteId}`);
      navigate(`/projects/${projectId}`);
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Could not delete site. Please try again.');
      setDeleting(false);
    }
  };

  return (
    <div className="page-container">
      <Link to={`/projects/${projectId}`} className="back-link">
        ← Back to project map
      </Link>

      {loading && <p>Loading site...</p>}
      {error && <div className="error-banner">{error}</div>}

      {site && (
        <>
          <div className="site-detail-header">
            <div>
              <h1>{site.name}</h1>
              <div className="meta-row">
                <span className={`badge badge-${site.site_type}`}>{site.site_type}</span>
                {typeof site.area_hectares === 'number' && (
                  <span>{site.area_hectares.toFixed(2)} hectares</span>
                )}
              </div>
            </div>
            <button
              type="button"
              className="btn btn-danger"
              onClick={() => setConfirmingDelete(true)}
            >
              Delete site
            </button>
          </div>

          <SiteAnalyticsCharts siteId={siteId} />
        </>
      )}

      {confirmingDelete && site && (
        <ConfirmDeleteSiteModal
          site={site}
          deleting={deleting}
          error={deleteError}
          onCancel={() => {
            setConfirmingDelete(false);
            setDeleteError('');
          }}
          onConfirm={confirmDelete}
        />
      )}
    </div>
  );
}
