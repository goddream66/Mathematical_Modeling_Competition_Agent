import type { SessionSummary } from "../types";

type HistoryPanelProps = {
  sessions: SessionSummary[];
  activeSessionId: string | null;
  busy: boolean;
  onCreate: () => void;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
};

export function HistoryPanel(props: HistoryPanelProps) {
  const { sessions, activeSessionId, busy, onCreate, onSelect, onDelete } = props;

  return (
    <section className="panel history-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Workspace</p>
          <h2>Session History</h2>
        </div>
        <button className="accent-button compact-button" disabled={busy} onClick={onCreate}>
          New Session
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="muted-block">No saved sessions yet.</div>
      ) : (
        <div className="history-list">
          {sessions.map((session) => {
            const active = session.session_id === activeSessionId;
            return (
              <article className={`history-card ${active ? "active" : ""}`} key={session.session_id}>
                <button
                  className="history-select"
                  disabled={busy}
                  onClick={() => onSelect(session.session_id)}
                  type="button"
                >
                  <strong>{session.messages[0]?.slice(0, 48) || "Untitled session"}</strong>
                  <span>{session.updated_at}</span>
                  <span>{session.report_ready ? "draft ready" : "draft pending"}</span>
                </button>
                <button
                  className="ghost-button compact-button"
                  disabled={busy}
                  onClick={() => onDelete(session.session_id)}
                  type="button"
                >
                  Delete
                </button>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
