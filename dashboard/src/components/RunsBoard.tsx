import "./RunsBoard.css";

export interface RunsBoardProps {
  /** Run ids, newest first (as returned by `listRuns()`). */
  runIds: string[];
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
}

/**
 * A departures-board-style list of recent runs: newest at the top, each row
 * a mono run id, the selected row lit up like an active gate. Selecting a
 * row drives `RunView`.
 */
export function RunsBoard({ runIds, selectedRunId, onSelect }: RunsBoardProps) {
  return (
    <div className="runs-board panel" role="region" aria-label="Recent runs">
      <div className="runs-board-header">
        <span className="runs-board-title">Runs</span>
      </div>
      {runIds.length === 0 ? (
        <p className="runs-board-empty">No runs yet.</p>
      ) : (
        <ul className="runs-board-list">
          {runIds.map((runId) => {
            const selected = runId === selectedRunId;
            return (
              <li key={runId}>
                <button
                  type="button"
                  className={`runs-board-row mono ${selected ? "runs-board-row--selected" : ""}`}
                  aria-pressed={selected}
                  onClick={() => onSelect(runId)}
                >
                  {runId}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
