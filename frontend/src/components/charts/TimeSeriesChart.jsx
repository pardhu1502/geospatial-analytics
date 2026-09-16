import Highcharts from 'highcharts';
import HighchartsReact from 'highcharts-react-official';
import { baseChartOptions, formatPointTooltip } from './chartTheme';

// A single-series time chart (area or line) for one metric. Kept as one small
// reusable component rather than three bespoke ones since carbon/biodiversity/ndvi
// only differ by color, mark type, and number formatting.
//
// Deliberately one chart per metric rather than a combined dual-axis chart: the
// dataviz skill treats two y-scales on one plot as the #1 chart mistake (a shared
// axis silently misleads on relative magnitude/slope). carbon_tons, biodiversity_index
// (0-100) and ndvi (0-1) live on incomparable scales, so three small-multiple charts
// sharing the same x (time) axis is the honest read.
export default function TimeSeriesChart({
  dates,
  values,
  color,
  type = 'line',
  decimals = 1,
  suffix = '',
  yAxisMin,
  yAxisMax,
}) {
  const data = dates.map((d, i) => [d, values[i]]);

  const areaFillColor = Highcharts.color(color).setOpacity(0.12).get('rgba');

  const options = {
    ...baseChartOptions(),
    chart: {
      ...baseChartOptions().chart,
      type,
      height: 260,
    },
    yAxis: {
      ...baseChartOptions().yAxis,
      min: yAxisMin,
      max: yAxisMax,
      labels: {
        ...baseChartOptions().yAxis.labels,
        formatter() {
          return Highcharts.numberFormat(this.value, decimals);
        },
      },
    },
    tooltip: {
      ...baseChartOptions().tooltip,
      formatter() {
        return formatPointTooltip(Highcharts, this.x, this.y, { decimals, suffix });
      },
    },
    series: [
      {
        name: 'value',
        data,
        color,
        lineWidth: 2,
        fillColor: type === 'area' ? areaFillColor : undefined,
        marker: {
          enabled: true,
          radius: 4,
          lineWidth: 2,
          lineColor: 'var(--color-surface)',
          states: { hover: { radius: 6 } },
        },
      },
    ],
  };

  return (
    <div className="chart-body">
      <HighchartsReact
        highcharts={Highcharts}
        options={options}
        containerProps={{ style: { width: '100%' } }}
      />
    </div>
  );
}
