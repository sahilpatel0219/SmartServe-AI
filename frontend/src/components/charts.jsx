/**
 * Recharts wrappers. Every color comes from useChartColors(), which re-reads the
 * CSS custom properties whenever the theme changes — so charts repaint on toggle.
 */
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

import { useChartColors } from '../context/ThemeContext';

const AXIS_FONT = 11;

function useAxisProps(colors) {
  return {
    stroke: colors.muted,
    tick: { fill: colors.muted, fontSize: AXIS_FONT },
    tickLine: false,
  };
}

function tooltipStyle(colors) {
  return {
    contentStyle: {
      background: colors.surface,
      border: `1px solid ${colors.hairline}`,
      borderRadius: 10,
      color: colors.text,
      fontSize: 12,
    },
    labelStyle: { color: colors.muted },
    itemStyle: { color: colors.text },
  };
}

const compact = (n) =>
  Math.abs(n) >= 1000 ? `${(n / 1000).toFixed(n % 1000 === 0 ? 0 : 1)}k` : String(n);

/** Revenue + profit over time. */
export function RevenueTrendChart({ labels, revenue, profit, height = 280 }) {
  const colors = useChartColors();
  const axis = useAxisProps(colors);
  const data = labels.map((label, i) => ({
    label,
    revenue: revenue[i] ?? 0,
    profit: profit?.[i] ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={colors.brand} stopOpacity={0.35} />
            <stop offset="100%" stopColor={colors.brand} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={colors.hairline} vertical={false} />
        <XAxis dataKey="label" {...axis} />
        <YAxis {...axis} tickFormatter={compact} width={48} />
        <Tooltip {...tooltipStyle(colors)} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
        <Legend wrapperStyle={{ fontSize: 12, color: colors.muted }} />
        <Area
          type="monotone" dataKey="revenue" name="Revenue"
          stroke={colors.brand} strokeWidth={2} fill="url(#revFill)"
        />
        <Line type="monotone" dataKey="profit" name="Profit" stroke={colors.success} strokeWidth={2} dot={false} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

/** Horizontal ranking bar chart (top items). */
export function RankBarChart({ labels, values, height = 300, label = 'Revenue' }) {
  const colors = useChartColors();
  const axis = useAxisProps(colors);
  const data = labels.map((name, i) => ({ name, value: values[i] ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
        <CartesianGrid stroke={colors.hairline} horizontal={false} />
        <XAxis type="number" {...axis} tickFormatter={compact} />
        <YAxis type="category" dataKey="name" {...axis} width={120} />
        <Tooltip {...tooltipStyle(colors)} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
        <Bar dataKey="value" name={label} fill={colors.brand} radius={[0, 6, 6, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Day-of-week or hourly distribution. */
export function DistributionChart({ labels, values, height = 240, label = 'Revenue' }) {
  const colors = useChartColors();
  const axis = useAxisProps(colors);
  const data = labels.map((name, i) => ({ name, value: values[i] ?? 0 }));
  const max = Math.max(...data.map((d) => d.value), 0);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 4 }}>
        <CartesianGrid stroke={colors.hairline} vertical={false} />
        <XAxis dataKey="name" {...axis} tickFormatter={(v) => String(v).slice(0, 3)} />
        <YAxis {...axis} tickFormatter={compact} width={48} />
        <Tooltip {...tooltipStyle(colors)} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
        <Bar dataKey="value" name={label} radius={[6, 6, 0, 0]}>
          {data.map((entry, i) => (
            // Highlight the peak so the busiest day/hour reads at a glance.
            <Cell key={i} fill={entry.value === max && max > 0 ? colors.brand : colors.brandSoft} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Forecast line — visually distinct from actuals (dashed). */
export function ForecastChart({ dates, values, height = 280 }) {
  const colors = useChartColors();
  const axis = useAxisProps(colors);
  const data = dates.map((label, i) => ({ label, value: values[i] ?? 0 }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid stroke={colors.hairline} vertical={false} />
        <XAxis dataKey="label" {...axis} />
        <YAxis {...axis} tickFormatter={compact} width={48} />
        <Tooltip {...tooltipStyle(colors)} formatter={(v) => `₹${Number(v).toLocaleString('en-IN')}`} />
        <Line
          type="monotone" dataKey="value" name="Predicted revenue"
          stroke={colors.info} strokeWidth={2} strokeDasharray="5 4"
          dot={{ r: 3, fill: colors.info }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
