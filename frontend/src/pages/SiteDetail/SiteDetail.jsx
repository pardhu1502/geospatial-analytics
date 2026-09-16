import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import apiClient from '../../api/client';
import SiteAnalyticsCharts from '../../components/charts/SiteAnalyticsCharts';

export default function SiteDetail() {
  const { projectId, siteId } = useParams();
  const [site, setSite] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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
            <h1>{site.name}</h1>
            <div className="meta-row">
              <span className={`badge badge-${site.site_type}`}>{site.site_type}</span>
              {typeof site.area_hectares === 'number' && (
                <span>{site.area_hectares.toFixed(2)} hectares</span>
              )}
            </div>
          </div>

          <SiteAnalyticsCharts siteId={siteId} />
        </>
      )}
    </div>
  );
}
