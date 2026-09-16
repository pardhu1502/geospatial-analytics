// Shared color tokens, Highcharts chrome defaults, and small data helpers for the
// SiteDetail analytics charts.
//
// Colors: `carbon` and `biodiversity` reuse the exact hex values already used for
// `.badge-carbon` / `.badge-biodiversity` in src/index.css (--color-carbon,
// --color-biodiversity) so the charts read as the same visual language as the rest
// of the app rather than introducing a competing palette. `ndvi` is new (NDVI has no
// existing token) — chosen and validated with the dataviz skill's palette validator
// (`validate_palette.js`) against the other two so all three clear the CVD /
// normal-vision adjacent-pair gates as well as the chroma floor. `carbon` alone sits
// slightly under the validator's chroma floor (reads a little desaturated) — that is
// the app's pre-existing brand green, kept as-is for consistency rather than
// reintroduced here; it is never asked to carry identity by hue alone (every chart
// and tile pairs it with a text label/title).
export const CHART_COLORS = {
  carbon: '#3b6e4f',
  biodiversity: '#c08a2e',
  ndvi: '#2f5f95',
};

// Status colors reused for the trend indicator. For these environmental metrics
// (carbon sequestered, biodiversity index, vegetation health) an increasing trend is
// the desired direction for a conservation site, so up=good/down=bad is a reasonable
// domain default. Never relied on alone — always paired with an icon glyph + text
// label (see TrendBadge).
export const TREND_COLORS = {
  up: '#1f3d2b',
  down: '#b3452c',
  flat: '#5a6b5a',
  unknown: '#5a6b5a',
};

const CHART_FONT = '"Segoe UI", system-ui, -apple-system, Roboto, sans-serif';

// Chrome (grid/axis/tooltip) is expressed with the app's existing CSS custom
// properties so it always matches the live theme; browsers resolve var() inside the
// inline styles Highcharts' SVG renderer applies, since the chart container sits
// inside the normal DOM cascade.
export function baseChartOptions() {
  return {
    chart: {
      backgroundColor: 'transparent',
      style: { fontFamily: CHART_FONT },
      spacing: [16, 16, 8, 8],
      reflow: true,
    },
    credits: { enabled: false },
    title: { text: undefined },
    // Single-series charts: the card heading above each chart already names the
    // series, so a one-swatch legend box would only restate it (see
    // marks-and-anatomy.md, "A single series needs no legend box").
    legend: { enabled: false },
    xAxis: {
      type: 'datetime',
      dateTimeLabelFormats: { month: '%b %Y', year: '%Y' },
      lineColor: 'var(--color-border)',
      tickColor: 'var(--color-border)',
      gridLineWidth: 0,
      crosshair: { width: 1, color: 'var(--color-border)', dashStyle: 'Solid' },
      labels: { style: { color: 'var(--color-text-muted)', fontSize: '0.78rem' } },
    },
    yAxis: {
      title: { text: null },
      gridLineWidth: 1,
      gridLineColor: 'var(--color-border)',
      gridLineDashStyle: 'Solid',
      lineWidth: 0,
      labels: { style: { color: 'var(--color-text-muted)', fontSize: '0.78rem' } },
    },
    tooltip: {
      useHTML: true,
      shadow: false,
      borderRadius: 8,
      borderWidth: 1,
      borderColor: 'var(--color-border)',
      backgroundColor: 'var(--color-surface)',
      style: { color: 'var(--color-text)' },
    },
    plotOptions: {
      series: {
        animation: { duration: 300 },
        states: { hover: { lineWidthPlus: 0 } },
      },
    },
  };
}

// Builds tooltip HTML for a single-series time chart. Date/value are our own
// formatted numbers, not raw API-provided label strings, so template-literal HTML
// is safe here (contrast with e.g. a series/category name coming straight from an
// API, which should go through textContent, never string-concatenated HTML).
export function formatPointTooltip(Highcharts, x, y, { decimals = 1, suffix = '' } = {}) {
  const date = Highcharts.dateFormat('%b %Y', x);
  const value = Highcharts.numberFormat(y, decimals);
  return (
    `<div style="min-width:110px">` +
    `<div style="color:var(--color-text-muted);font-size:0.72rem;margin-bottom:2px">${date}</div>` +
    `<div style="font-weight:700;font-size:1rem;color:var(--color-text)">${value}${suffix}</div>` +
    `</div>`
  );
}

// Normalizes whatever shape `trend` arrives in from GET /sites/{id}/analytics/summary
// — the contract only says "trend", not its type, so this defensively accepts a
// signed number (delta), a direction string, or an {direction|value} object.
export function normalizeTrend(trend) {
  if (trend === null || trend === undefined) {
    return { direction: 'unknown', label: 'No trend data' };
  }

  if (typeof trend === 'number') {
    if (trend > 0) return { direction: 'up', label: 'Increasing' };
    if (trend < 0) return { direction: 'down', label: 'Decreasing' };
    return { direction: 'flat', label: 'Stable' };
  }

  if (typeof trend === 'object') {
    if (typeof trend.value === 'number') return normalizeTrend(trend.value);
    if (typeof trend.direction === 'string') return normalizeTrend(trend.direction);
    return { direction: 'unknown', label: 'No trend data' };
  }

  if (typeof trend === 'string') {
    const t = trend.toLowerCase();
    if (/^(up|increas|positive|rising|growth)/.test(t))
      return { direction: 'up', label: 'Increasing' };
    if (/^(down|decreas|negative|falling|decline)/.test(t))
      return { direction: 'down', label: 'Decreasing' };
    if (/^(flat|stable|steady|no.?change)/.test(t)) return { direction: 'flat', label: 'Stable' };
    return { direction: 'unknown', label: trend };
  }

  return { direction: 'unknown', label: 'No trend data' };
}

export function formatCompactNumber(value, { decimals = 1, suffix = '' } = {}) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return `${value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })}${suffix}`;
}
