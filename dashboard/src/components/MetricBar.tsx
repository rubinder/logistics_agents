import "./MetricBar.css";

export type MetricBarTone = "cyan" | "muted" | "reroute";

export interface MetricBarProps {
  label: string;
  /** Metric value in the 0..1 range (clamped before rendering). */
  value: number;
  tone: MetricBarTone;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/**
 * A single labelled instrument bar: a track in the panel/line palette with a
 * fill sized to `value * 100%`, tinted by `tone`. The numeric readout is
 * always rendered as mono text next to the bar (not just implied by width),
 * and the track carries an `aria-label` with the same figure so the value
 * is available to assistive tech either way.
 */
export function MetricBar({ label, value, tone }: MetricBarProps) {
  const clamped = Math.min(Math.max(value, 0), 1);
  const formatted = formatPercent(clamped);

  return (
    <div className="metric-bar">
      <div className="metric-bar-row">
        <span className="metric-bar-label">{label}</span>
        <span className="metric-bar-value mono">{formatted}</span>
      </div>
      <div className="metric-bar-track" role="img" aria-label={`${label}: ${formatted}`}>
        <div
          className={`metric-bar-fill metric-bar-fill--${tone}`}
          style={{ width: `${clamped * 100}%` }}
        />
      </div>
    </div>
  );
}
