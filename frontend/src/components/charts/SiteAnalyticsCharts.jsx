import { useEffect, useState } from 'react';
import apiClient from '../../api/client';
import StatTile from './StatTile';
import TimeSeriesChart from './TimeSeriesChart';
import { CHART_COLORS, formatCompactNumber } from './chartTheme';
import './SiteAnalyticsCharts.css';

// Fills in the SiteDetail analytics section: a stat-tile summary row plus one
// time-series chart per metric (carbon_tons, biodiversity_index, ndvi). See
// TimeSeriesChart.jsx for why these are three separate charts rather than one
// dual-axis chart.
export default function SiteAnalyticsCharts({ siteId }) {
  const [metrics, setMetrics] = useState(null);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [metricsError, setMetricsError] = useState('');
  const [summaryError, setSummaryError] = useState('');
  const [showTable, setShowTable] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setMetricsError('');
    setSummaryError('');

    Promise.allSettled([
      apiClient.get(`/sites/${siteId}/metrics`),
      apiClient.get(`/sites/${siteId}/analytics/summary`),
    ]).then(([metricsResult, summaryResult]) => {
      if (cancelled) return;

      if (metricsResult.status === 'fulfilled') {
        setMetrics(Array.isArray(metricsResult.value.data) ? metricsResult.value.data : []);
      } else {
        setMetricsError(
          metricsResult.reason?.response?.data?.detail || 'Could not load metrics for this site.'
        );
      }

      if (summaryResult.status === 'fulfilled') {
        setSummary(summaryResult.value.data);
      } else {
        setSummaryError(
          summaryResult.reason?.response?.data?.detail || 'Could not load the analytics summary.'
        );
      }

      setLoading(false);
    });

    return () => {
      cancelled = true;
    };
  }, [siteId]);

  if (loading) {
    return (
      <div className="site-analytics-charts">
        <p className="empty-state">Loading analytics…</p>
      </div>
    );
  }

  const hasMetrics = Array.isArray(metrics) && metrics.length > 0;
  const bothFailed = metricsError && summaryError;

  if (bothFailed) {
    return (
      <div className="site-analytics-charts">
        <div className="error-banner">{metricsError}</div>
      </div>
    );
  }

  const dates = hasMetrics ? metrics.map((m) => Date.parse(m.date)) : [];

  return (
    <div className="site-analytics-charts">
      {summaryError && <div className="error-banner">{summaryError}</div>}

      {summary && (
        <div className="stat-row">
          <StatTile
            label="Total carbon sequestered"
            value={formatCompactNumber(summary.total_carbon_tons, { decimals: 1, suffix: ' t' })}
          />
          <StatTile
            label="Avg biodiversity index"
            value={formatCompactNumber(summary.avg_biodiversity_index, {
              decimals: 1,
              suffix: ' / 100',
            })}
          />
          <StatTile
            label="Avg NDVI"
            value={formatCompactNumber(summary.avg_ndvi, { decimals: 2 })}
          />
          <StatTile label="Trend" trend={summary.trend} />
        </div>
      )}

      {metricsError && !hasMetrics && <div className="error-banner">{metricsError}</div>}

      {!metricsError && !hasMetrics && (
        <p className="empty-state">
          No metrics recorded for this site yet — charts will appear once monthly data comes in.
        </p>
      )}

      {hasMetrics && (
        <>
          <div className="card chart-card">
            <h3>Carbon sequestered over time</h3>
            <TimeSeriesChart
              dates={dates}
              values={metrics.map((m) => m.carbon_tons)}
              color={CHART_COLORS.carbon}
              type="area"
              decimals={1}
              suffix=" t"
              yAxisMin={0}
            />
          </div>

          <div className="charts-grid">
            <div className="card chart-card">
              <h3>Biodiversity index</h3>
              <TimeSeriesChart
                dates={dates}
                values={metrics.map((m) => m.biodiversity_index)}
                color={CHART_COLORS.biodiversity}
                type="line"
                decimals={1}
                yAxisMin={0}
                yAxisMax={100}
              />
            </div>

            <div className="card chart-card">
              <h3>NDVI (vegetation health)</h3>
              <TimeSeriesChart
                dates={dates}
                values={metrics.map((m) => m.ndvi)}
                color={CHART_COLORS.ndvi}
                type="line"
                decimals={2}
                yAxisMin={0}
                yAxisMax={1}
              />
            </div>
          </div>

          <button
            type="button"
            className="btn btn-secondary table-toggle"
            onClick={() => setShowTable((v) => !v)}
            aria-expanded={showTable}
          >
            {showTable ? 'Hide data table' : 'Show data table'}
          </button>

          {showTable && (
            <div className="card table-card">
              <div className="table-scroll">
                <table className="metrics-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Carbon (t)</th>
                      <th>Biodiversity index</th>
                      <th>NDVI</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metrics.map((m) => (
                      <tr key={m.date}>
                        <td>{m.date}</td>
                        <td>{formatCompactNumber(m.carbon_tons, { decimals: 1 })}</td>
                        <td>{formatCompactNumber(m.biodiversity_index, { decimals: 1 })}</td>
                        <td>{formatCompactNumber(m.ndvi, { decimals: 2 })}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
