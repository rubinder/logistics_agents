import "./EvalBoard.css";

import type { EvalReport } from "../api/types";
import { MetricBar } from "./MetricBar";

export interface EvalBoardProps {
  reports: EvalReport[];
}

function formatComposite(value: number): string {
  return value.toFixed(3);
}

/**
 * Per-model eval quality board: a ranked instrument panel of `MetricBar`s
 * (composite / accuracy / F1) per model, plus the rubric/dataset version
 * that produced the run, so reviewers can compare models at a glance and
 * know exactly which rubric produced the numbers. Ranked best-composite-first.
 */
export function EvalBoard({ reports }: EvalBoardProps) {
  const ranked = [...reports].sort((a, b) => b.mean_composite - a.mean_composite);

  return (
    <div className="eval-board panel" role="region" aria-label="Eval quality board">
      <div className="eval-board-header">
        <span className="eval-board-title">Eval Quality Board</span>
        <span className="eval-board-subtitle">Ranked by mean composite</span>
      </div>
      {ranked.length === 0 ? (
        <p className="eval-board-empty">No eval reports yet.</p>
      ) : (
        <ul className="eval-board-list">
          {ranked.map((report, index) => (
            <li key={report.model} className="eval-board-card">
              <div className="eval-board-card-header">
                <span className="eval-board-rank mono">#{index + 1}</span>
                <span className="eval-board-model" data-testid="eval-model">
                  {report.model}
                </span>
                <span className="eval-board-composite mono" data-testid="eval-composite">
                  {formatComposite(report.mean_composite)}
                </span>
                <span className="eval-board-provenance mono">
                  rubric {report.rubric_version} &middot; dataset {report.dataset_version}
                </span>
              </div>
              <div className="eval-board-bars">
                <MetricBar label="Composite" value={report.mean_composite} tone="cyan" />
                <MetricBar label="Label accuracy" value={report.label_accuracy} tone="muted" />
                <MetricBar label="Mean F1" value={report.mean_f1} tone="reroute" />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
