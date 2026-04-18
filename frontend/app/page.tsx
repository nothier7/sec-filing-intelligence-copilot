const sampleQuestions = [
  "What changed in risk factors since the previous 10-K?",
  "What were the main drivers of revenue growth?",
  "How does the filing describe liquidity and capital resources?"
];

export default function Home() {
  return (
    <main className="app-shell">
      <section className="workspace" aria-labelledby="workspace-title">
        <div className="hero-image" aria-hidden="true" />

        <div className="toolbar">
          <div>
            <p className="eyebrow">Public filing research</p>
            <h1 id="workspace-title">SEC Filing Intelligence Copilot</h1>
          </div>
          <div className="status-pill">Foundation build</div>
        </div>

        <div className="research-grid">
          <section className="control-surface" aria-label="Research controls">
            <label htmlFor="company">Company</label>
            <select id="company" disabled defaultValue="">
              <option value="">Demo corpus pending</option>
            </select>

            <label htmlFor="filing">Filing</label>
            <select id="filing" disabled defaultValue="">
              <option value="">No filings indexed yet</option>
            </select>

            <label htmlFor="question">Question</label>
            <textarea
              id="question"
              placeholder="Ask about risk factors, MD&A, liquidity, or financial facts."
              disabled
            />

            <button type="button" disabled>
              Ask with citations
            </button>
          </section>

          <section className="answer-panel" aria-label="Answer preview">
            <p className="panel-kicker">Answer</p>
            <h2>Cited answers will appear here.</h2>
            <p>
              The first milestone establishes the app shell. SEC ingestion,
              retrieval, citations, and numeric grounding will connect through
              the backend API in later milestones.
            </p>

            <div className="sample-block" aria-label="Sample questions">
              {sampleQuestions.map((question) => (
                <span key={question}>{question}</span>
              ))}
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

