import { TREND_COLORS, normalizeTrend } from './chartTheme';

// Icon + label pairing for trend direction — never color alone (dataviz skill:
// status colors are reserved and always ship with an icon + label).
const TREND_GLYPH = {
  up: '▲',
  down: '▼',
  flat: '▬',
  unknown: '–',
};

export function TrendBadge({ trend }) {
  const { direction, label } = normalizeTrend(trend);
  return (
    <span className="trend-badge" style={{ color: TREND_COLORS[direction] }}>
      <span className="trend-badge-glyph" aria-hidden="true">
        {TREND_GLYPH[direction]}
      </span>
      {label}
    </span>
  );
}

export default function StatTile({ label, value, trend }) {
  return (
    <div className="stat-tile">
      <div className="label">{label}</div>
      <div className="value">{trend !== undefined ? <TrendBadge trend={trend} /> : value}</div>
    </div>
  );
}
