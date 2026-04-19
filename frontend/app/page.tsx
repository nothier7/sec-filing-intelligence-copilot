"use client";

import { FormEvent, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const filings = [
  {
    accessionNumber: "0000320193-25-000079",
    label: "Apple 2025 Form 10-K",
    period: "FY 2025",
    formType: "10-K",
    filedDate: "2025-10-31"
  },
  {
    accessionNumber: "0000320193-26-000006",
    label: "Apple Q1 2026 Form 10-Q",
    period: "Q1 FY 2026",
    formType: "10-Q",
    filedDate: "2026-01-30"
  }
];

const sampleQuestions = [
  "How much revenue did Apple report in 2025?",
  "How much revenue did Apple report in Q1 2026?",
  "What supply chain risks does Apple describe?",
  "Should I buy this stock?"
];

const benchmarkRows = [
  {
    variant: "Closed book",
    role: "No filing context",
    accuracy: 8.3,
    numericAccuracy: 0,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 16.7,
    latency: "0.0 ms"
  },
  {
    variant: "Naive RAG",
    role: "Unfiltered retrieval",
    accuracy: 33.3,
    numericAccuracy: 16.7,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 83.3,
    latency: "42.1 ms"
  },
  {
    variant: "Filtered RAG",
    role: "Metadata-aware retrieval",
    accuracy: 54.2,
    numericAccuracy: 16.7,
    groundedAccuracy: 0,
    refusalAccuracy: 75,
    evidenceRecall: 100,
    latency: "37.2 ms"
  },
  {
    variant: "GPT-5 mini closed book",
    role: "Generic model baseline",
    accuracy: 8.3,
    numericAccuracy: 0,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 16.7,
    latency: "cached"
  },
  {
    variant: "GPT-5 mini + retrieved context",
    role: "External model with excerpts",
    accuracy: 41.7,
    numericAccuracy: 58.3,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 100,
    latency: "cached"
  },
  {
    variant: "GPT-5 mini + web search",
    role: "External model with web access",
    accuracy: 62.5,
    numericAccuracy: 75,
    groundedAccuracy: 0,
    refusalAccuracy: 100,
    evidenceRecall: 16.7,
    latency: "cached"
  },
  {
    variant: "Filtered RAG + XBRL",
    role: "Retrieval plus structured facts",
    accuracy: 100,
    numericAccuracy: 100,
    groundedAccuracy: 100,
    refusalAccuracy: 100,
    evidenceRecall: 100,
    latency: "40.2 ms"
  }
];

const benchmarkFacts = [
  { label: "Questions", value: "24" },
  { label: "Filings", value: "2" },
  { label: "Issuer", value: "AAPL" },
  { label: "Model baseline", value: "gpt-5-mini" }
];

const benchmarkFailures = [
  {
    label: "Closed-book limit",
    text: "GPT-5 mini refused the 2025 revenue question without filing evidence. The validated XBRL value is $416.161B."
  },
  {
    label: "Web-search limit",
    text: "GPT-5 mini with web search found many public numbers, but still had 0% grounded numeric accuracy."
  },
  {
    label: "Structured fix",
    text: "The XBRL-grounded variant validates financial values against parsed SEC facts before returning the final answer."
  }
];

type Citation = {
  chunk_id: string;
  accession_number?: string;
  section_name?: string;
  section_type?: string;
  source_url?: string;
  source_start?: number;
  source_end?: number;
  score?: number;
  snippet: string;
};

type NumericGrounding = {
  status: string;
  metric_label?: string;
  concept?: string;
  value?: string;
  unit?: string;
  fiscal_year?: number;
  fiscal_quarter?: number;
  fiscal_period?: string;
};

type AskResponse = {
  question: string;
  answer: string;
  query_type: string;
  supported: boolean;
  confidence: number;
  citations: Citation[];
  numeric_grounding: NumericGrounding[];
  retrieval_count: number;
  insufficient_evidence_reason?: string;
};

type CompareCitation = {
  filing_role: string;
  accession_number: string;
  chunk_id: string;
  section_name?: string;
  section_type?: string;
  source_url?: string;
  snippet: string;
};

type ChangeClaim = {
  change_type: string;
  text: string;
  citations: CompareCitation[];
};

type CompareResponse = {
  current_accession_number: string;
  prior_accession_number?: string;
  section_type: string;
  supported: boolean;
  summary: string;
  added_claims: ChangeClaim[];
  removed_claims: ChangeClaim[];
  unchanged_claim_count: number;
  citations: CompareCitation[];
  insufficient_evidence_reason?: string;
};

type Mode = "ask" | "compare" | "benchmark";

export default function Home() {
  const [mode, setMode] = useState<Mode>("ask");
  const [accessionNumber, setAccessionNumber] = useState(filings[0].accessionNumber);
  const [previousAccessionNumber, setPreviousAccessionNumber] = useState(
    filings[1].accessionNumber
  );
  const [sectionType, setSectionType] = useState("all");
  const [question, setQuestion] = useState(sampleQuestions[0]);
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [compareResponse, setCompareResponse] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const selectedFiling = useMemo(
    () => filings.find((filing) => filing.accessionNumber === accessionNumber),
    [accessionNumber]
  );

  async function submitAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setCompareResponse(null);
    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accession_number: accessionNumber,
          question,
          section_type: sectionType === "all" ? undefined : sectionType,
          top_k: 5
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The backend returned an error.");
      }
      setAskResponse(payload);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function submitCompare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setAskResponse(null);
    try {
      const response = await fetch(`${API_BASE_URL}/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accession_number: accessionNumber,
          previous_accession_number: previousAccessionNumber,
          section_type: sectionType === "all" ? "risk_factors" : sectionType,
          max_claims: 5
        })
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The backend returned an error.");
      }
      setCompareResponse(payload);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : "Request failed.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="workspace" aria-labelledby="workspace-title">
        <div className="command-bar">
          <div>
            <p className="eyebrow">Live SEC filing workbench</p>
            <h1 id="workspace-title">Ask Apple filings with citations and XBRL checks.</h1>
          </div>
          <div className="api-chip">Backend: {API_BASE_URL}</div>
        </div>

        <div className="research-grid">
          <section className="control-surface" aria-label="Research controls">
            <div className="source-photo" aria-hidden="true" />
            <div className="mode-switch" aria-label="Workflow mode">
              <button
                className={mode === "ask" ? "active" : ""}
                type="button"
                onClick={() => {
                  setMode("ask");
                  setError(null);
                }}
              >
                Ask
              </button>
              <button
                className={mode === "compare" ? "active" : ""}
                type="button"
                onClick={() => {
                  setMode("compare");
                  setAccessionNumber(filings[1].accessionNumber);
                  setPreviousAccessionNumber(filings[0].accessionNumber);
                  setAskResponse(null);
                  setCompareResponse(null);
                  setError(null);
                  if (sectionType === "all") {
                    setSectionType("risk_factors");
                  }
                }}
              >
                Compare
              </button>
              <button
                className={mode === "benchmark" ? "active" : ""}
                type="button"
                onClick={() => {
                  setMode("benchmark");
                  setAskResponse(null);
                  setCompareResponse(null);
                  setError(null);
                }}
              >
                Benchmark
              </button>
            </div>

            {mode === "ask" ? (
              <form onSubmit={submitAsk}>
                <label htmlFor="filing">Filing</label>
                <select
                  id="filing"
                  value={accessionNumber}
                  onChange={(event) => setAccessionNumber(event.target.value)}
                >
                  {filings.map((filing) => (
                    <option key={filing.accessionNumber} value={filing.accessionNumber}>
                      {filing.label}
                    </option>
                  ))}
                </select>

                <label htmlFor="section">Section filter</label>
                <select
                  id="section"
                  value={sectionType}
                  onChange={(event) => setSectionType(event.target.value)}
                >
                  <option value="all">All sections</option>
                  <option value="risk_factors">Risk Factors</option>
                  <option value="mda">MD&A</option>
                  <option value="financial_statements">Financial Statements</option>
                  <option value="controls">Controls</option>
                </select>

                <label htmlFor="question">Question</label>
                <textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />

                <button disabled={isLoading || !question.trim()} type="submit">
                  {isLoading ? "Running retrieval..." : "Ask with citations"}
                </button>
              </form>
            ) : mode === "compare" ? (
              <form onSubmit={submitCompare}>
                <label htmlFor="current-filing">Current filing</label>
                <select
                  id="current-filing"
                  value={accessionNumber}
                  onChange={(event) => setAccessionNumber(event.target.value)}
                >
                  {filings.map((filing) => (
                    <option key={filing.accessionNumber} value={filing.accessionNumber}>
                      {filing.label}
                    </option>
                  ))}
                </select>

                <label htmlFor="prior-filing">Prior filing</label>
                <select
                  id="prior-filing"
                  value={previousAccessionNumber}
                  onChange={(event) => setPreviousAccessionNumber(event.target.value)}
                >
                  {filings.map((filing) => (
                    <option key={filing.accessionNumber} value={filing.accessionNumber}>
                      {filing.label}
                    </option>
                  ))}
                </select>

                <label htmlFor="compare-section">Section</label>
                <select
                  id="compare-section"
                  value={sectionType === "all" ? "risk_factors" : sectionType}
                  onChange={(event) => setSectionType(event.target.value)}
                >
                  <option value="risk_factors">Risk Factors</option>
                  <option value="mda">MD&A</option>
                </select>

                <button disabled={isLoading} type="submit">
                  {isLoading ? "Comparing filings..." : "Compare section changes"}
                </button>
              </form>
            ) : (
              <BenchmarkBrief />
            )}

            <div className="sample-block" aria-label="Sample questions">
              {sampleQuestions.map((sampleQuestion) => (
                <button
                  key={sampleQuestion}
                  type="button"
                  onClick={() => {
                    setMode("ask");
                    setAskResponse(null);
                    setCompareResponse(null);
                    setError(null);
                    setQuestion(sampleQuestion);
                    setSectionType(sampleQuestion.includes("supply") ? "risk_factors" : "all");
                  }}
                >
                  {sampleQuestion}
                </button>
              ))}
            </div>
          </section>

          <section className="answer-panel" aria-label="Research result">
            <div className="filing-strip">
              {mode === "benchmark" ? (
                <>
                  <span>Apple eval</span>
                  <strong>24 real questions</strong>
                  <span>2025 10-K + Q1 2026 10-Q</span>
                  <code>gpt-5-mini baseline</code>
                </>
              ) : (
                <>
                  <span>{selectedFiling?.formType}</span>
                  <strong>{selectedFiling?.period}</strong>
                  <span>{selectedFiling?.filedDate}</span>
                  <code>{accessionNumber}</code>
                </>
              )}
            </div>

            {mode === "benchmark" ? (
              <BenchmarkResult />
            ) : (
              <>
                {error ? <div className="error-box">{error}</div> : null}
                {!askResponse && !compareResponse && !error ? <EmptyState /> : null}
                {askResponse ? <AskResult response={askResponse} /> : null}
                {compareResponse ? <CompareResult response={compareResponse} /> : null}
              </>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function BenchmarkBrief() {
  return (
    <section className="benchmark-brief" aria-label="Benchmark summary">
      <p className="panel-kicker">Tracked benchmark</p>
      <h2>Real filing questions, measured against generic model baselines.</h2>
      <p>
        The benchmark uses Apple’s FY2025 10-K and Q1 FY2026 10-Q to test numeric
        accuracy, grounded numeric accuracy, refusal behavior, and citation recall.
      </p>
      <div className="brief-grid">
        {benchmarkFacts.map((fact) => (
          <Metric key={fact.label} label={fact.label} value={fact.value} />
        ))}
      </div>
      <code className="benchmark-command">
        .venv/bin/python -m sec_copilot.cli run-eval --variant improved_rag_xbrl
      </code>
    </section>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <p className="panel-kicker">Ready</p>
      <h2>Run a question against the local SEC database.</h2>
      <p>
        Try the revenue questions first. They should return a cited answer plus a
        validated XBRL fact when the backend is using `data/sec_copilot_real.db`.
      </p>
    </div>
  );
}

function BenchmarkResult() {
  return (
    <div className="result-stack benchmark-result">
      <div className="answer-heading">
        <p className="panel-kicker">Evaluation</p>
        <span>Generated 2026-04-19</span>
      </div>
      <h2>Structured SEC facts beat context-only answers on grounded financial QA.</h2>

      <div className="benchmark-scoreboard" aria-label="Benchmark headline metrics">
        <Metric label="Best overall accuracy" value="100%" />
        <Metric label="Best grounded numeric accuracy" value="100%" />
        <Metric label="OpenAI web grounded accuracy" value="0%" />
      </div>

      <div className="benchmark-table-wrap">
        <table className="benchmark-table">
          <thead>
            <tr>
              <th scope="col">Variant</th>
              <th scope="col">Accuracy</th>
              <th scope="col">Numeric</th>
              <th scope="col">Grounded numeric</th>
              <th scope="col">Refusal</th>
              <th scope="col">Evidence</th>
              <th scope="col">Latency</th>
            </tr>
          </thead>
          <tbody>
            {benchmarkRows.map((row) => (
              <tr key={row.variant} className={row.groundedAccuracy === 100 ? "winner-row" : ""}>
                <th scope="row">
                  <strong>{row.variant}</strong>
                  <span>{row.role}</span>
                </th>
                <ScoreCell value={row.accuracy} />
                <ScoreCell value={row.numericAccuracy} />
                <ScoreCell value={row.groundedAccuracy} />
                <ScoreCell value={row.refusalAccuracy} />
                <ScoreCell value={row.evidenceRecall} />
                <td>{row.latency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="failure-grid" aria-label="Benchmark takeaways">
        {benchmarkFailures.map((failure) => (
          <article key={failure.label}>
            <p className="panel-kicker">{failure.label}</p>
            <p>{failure.text}</p>
          </article>
        ))}
      </section>
    </div>
  );
}

function ScoreCell({ value }: { value: number }) {
  return (
    <td>
      <span className="score-value">{value.toFixed(value % 1 === 0 ? 0 : 1)}%</span>
      <span className="score-track" aria-hidden="true">
        <span style={{ width: `${value}%` }} />
      </span>
    </td>
  );
}

function AskResult({ response }: { response: AskResponse }) {
  return (
    <div className="result-stack">
      <div className="answer-heading">
        <p className="panel-kicker">{response.supported ? "Supported answer" : "Insufficient evidence"}</p>
        <span>{Math.round(response.confidence * 100)}% confidence</span>
      </div>
      <h2>{response.answer}</h2>
      <div className="metric-grid">
        <Metric label="Query type" value={response.query_type} />
        <Metric label="Retrieved chunks" value={String(response.retrieval_count)} />
        <Metric label="Citations" value={String(response.citations.length)} />
      </div>

      {response.numeric_grounding.length ? (
        <section className="fact-line" aria-label="Numeric grounding">
          <p className="panel-kicker">XBRL grounding</p>
          {response.numeric_grounding.map((fact) => (
            <div key={`${fact.concept}-${fact.value}`}>
              <strong>
                {fact.status}: {fact.value} {fact.unit}
              </strong>
              <span>
                {fact.metric_label} · {fact.fiscal_period} {fact.fiscal_year} · {fact.concept}
              </span>
            </div>
          ))}
        </section>
      ) : null}

      <CitationList citations={response.citations} />
    </div>
  );
}

function CompareResult({ response }: { response: CompareResponse }) {
  return (
    <div className="result-stack">
      <div className="answer-heading">
        <p className="panel-kicker">{response.supported ? "Section comparison" : "Unsupported"}</p>
        <span>{response.unchanged_claim_count} unchanged</span>
      </div>
      <h2>{response.summary}</h2>
      <div className="change-grid">
        <ChangeColumn title="Added claims" claims={response.added_claims} />
        <ChangeColumn title="Removed claims" claims={response.removed_claims} />
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) {
    return null;
  }
  return (
    <section className="citation-list" aria-label="Citations">
      <p className="panel-kicker">Citations</p>
      {citations.map((citation) => (
        <article key={citation.chunk_id}>
          <header>
            <strong>{citation.section_name ?? citation.section_type ?? "Filing evidence"}</strong>
            <code>{citation.chunk_id}</code>
          </header>
          <p>{citation.snippet}</p>
          {citation.source_url ? (
            <a href={citation.source_url} rel="noreferrer" target="_blank">
              Open SEC source
            </a>
          ) : null}
        </article>
      ))}
    </section>
  );
}

function ChangeColumn({ title, claims }: { title: string; claims: ChangeClaim[] }) {
  return (
    <section>
      <p className="panel-kicker">{title}</p>
      {claims.length ? (
        claims.map((claim) => (
          <article key={`${claim.change_type}-${claim.text}`}>
            <p>{claim.text}</p>
            <code>{claim.citations[0]?.chunk_id ?? "No citation"}</code>
          </article>
        ))
      ) : (
        <p className="muted-copy">No claims returned.</p>
      )}
    </section>
  );
}
