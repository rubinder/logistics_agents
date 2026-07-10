import "./DecisionStamp.css";

import type { CSSProperties } from "react";

import type { Decision } from "../api/types";
import { labelColor } from "./signal";

export interface DecisionStampProps {
  decision: Decision;
}

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * The rail's terminus: the decision label stamped large, like a customs
 * ink-stamp on a waybill, colored by its signal, with confidence and the
 * exception chips underneath.
 */
export function DecisionStamp({ decision }: DecisionStampProps) {
  const style = { "--stamp-color": labelColor(decision.label) } as CSSProperties;

  return (
    <div className="decision-stamp" style={style} role="status">
      <div className="decision-stamp-plate">
        <span className="decision-stamp-label">{decision.label}</span>
        <span className="decision-stamp-confidence mono">
          {formatConfidence(decision.confidence)} confidence
        </span>
      </div>
      {decision.exceptions.length > 0 && (
        <ul className="decision-stamp-chips">
          {decision.exceptions.map((exception, index) => (
            <li key={`${exception.type}-${index}`} className="decision-stamp-chip mono">
              {exception.type}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
