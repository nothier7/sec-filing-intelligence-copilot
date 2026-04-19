"use client";

import { FormEvent, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type BenchmarkIssuer = "all" | "aapl" | "msft";

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
  },
  {
    accessionNumber: "0000950170-25-100235",
    label: "Microsoft 2025 Form 10-K",
    period: "FY 2025",
    formType: "10-K",
    filedDate: "2025-07-30"
  },
  {
    accessionNumber: "0001193125-25-256321",
    label: "Microsoft Q1 2026 Form 10-Q",
    period: "Q1 FY 2026",
    formType: "10-Q",
    filedDate: "2025-10-29"
  },
  {
    accessionNumber: "0001193125-26-027207",
    label: "Microsoft Q2 2026 Form 10-Q",
    period: "Q2 FY 2026",
    formType: "10-Q",
    filedDate: "2026-01-28"
  }
];

const sampleQuestions = [
  {
    question: "How much revenue did Apple report in 2025?",
    accessionNumber: "0000320193-25-000079",
    sectionType: "mda"
  },
  {
    question: "How much revenue did Microsoft report in fiscal 2025?",
    accessionNumber: "0000950170-25-100235",
    sectionType: "mda"
  },
  {
    question: "What trade, tariff, and AI export control risks does Microsoft describe?",
    accessionNumber: "0001193125-26-027207",
    sectionType: "risk_factors"
  },
  {
    question: "Should I buy this stock?",
    accessionNumber: "0000320193-25-000079",
    sectionType: "all"
  }
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
    accuracy: 31.3,
    numericAccuracy: 16.7,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 74,
    latency: "52.3 ms"
  },
  {
    variant: "Filtered RAG",
    role: "Metadata-aware retrieval",
    accuracy: 52.1,
    numericAccuracy: 12.5,
    groundedAccuracy: 0,
    refusalAccuracy: 75,
    evidenceRecall: 100,
    latency: "47.1 ms"
  },
  {
    variant: "GPT-5 mini closed book",
    role: "Generic model baseline",
    accuracy: 8.3,
    numericAccuracy: 0,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 16.7,
    latency: "API"
  },
  {
    variant: "GPT-5 mini + retrieved context",
    role: "External model with excerpts",
    accuracy: 37.5,
    numericAccuracy: 50,
    groundedAccuracy: 0,
    refusalAccuracy: 50,
    evidenceRecall: 100,
    latency: "API"
  },
  {
    variant: "GPT-5 mini + web search",
    role: "External model with web access",
    accuracy: 41.7,
    numericAccuracy: 45.8,
    groundedAccuracy: 0,
    refusalAccuracy: 75,
    evidenceRecall: 16.7,
    latency: "API"
  },
  {
    variant: "Filtered RAG + XBRL",
    role: "Retrieval plus structured facts",
    accuracy: 100,
    numericAccuracy: 100,
    groundedAccuracy: 100,
    refusalAccuracy: 100,
    evidenceRecall: 100,
    latency: "50.2 ms"
  },
  {
    variant: "Guarded LLM + XBRL",
    role: "Polished answer with fact guards",
    accuracy: 100,
    numericAccuracy: 100,
    groundedAccuracy: 100,
    refusalAccuracy: 100,
    evidenceRecall: 100,
    latency: "2.0 s"
  }
];

const benchmarkDatasets: Record<
  BenchmarkIssuer,
  {
    label: string;
    title: string;
    summary: string;
    facts: { label: string; value: string }[];
    rows: typeof benchmarkRows;
    generated: string;
  }
> = {
  all: {
    label: "Apple + Microsoft",
    title: "Structured SEC facts generalize across Apple and Microsoft.",
    summary:
      "The benchmark averages Apple and Microsoft filing evaluations across exact numeric accuracy, grounded validation, refusal behavior, and citation recall.",
    facts: [
      { label: "Questions", value: "48" },
      { label: "Filings", value: "4" },
      { label: "Issuers", value: "AAPL + MSFT" },
      { label: "Model baseline", value: "gpt-5-mini" }
    ],
    rows: benchmarkRows,
    generated: "Generated 2026-04-19"
  },
  aapl: {
    label: "Apple",
    title: "Apple filings stay grounded when revenue and expense questions vary.",
    summary:
      "Apple questions cover the FY 2025 Form 10-K and Q1 FY 2026 Form 10-Q, including numeric facts, risk language, controls, and refusal cases.",
    facts: [
      { label: "Questions", value: "24" },
      { label: "Filings", value: "2" },
      { label: "Issuer", value: "AAPL" },
      { label: "Best accuracy", value: "100%" }
    ],
    rows: [
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
        latency: "45.6 ms"
      },
      {
        variant: "Filtered RAG",
        role: "Metadata-aware retrieval",
        accuracy: 54.2,
        numericAccuracy: 16.7,
        groundedAccuracy: 0,
        refusalAccuracy: 75,
        evidenceRecall: 100,
        latency: "38.7 ms"
      },
      {
        variant: "GPT-5 mini closed book",
        role: "Generic model baseline",
        accuracy: 8.3,
        numericAccuracy: 0,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 16.7,
        latency: "API"
      },
      {
        variant: "GPT-5 mini + retrieved context",
        role: "External model with excerpts",
        accuracy: 41.7,
        numericAccuracy: 58.3,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 100,
        latency: "API"
      },
      {
        variant: "GPT-5 mini + web search",
        role: "External model with web access",
        accuracy: 62.5,
        numericAccuracy: 75,
        groundedAccuracy: 0,
        refusalAccuracy: 100,
        evidenceRecall: 16.7,
        latency: "API"
      },
      {
        variant: "Filtered RAG + XBRL",
        role: "Retrieval plus structured facts",
        accuracy: 100,
        numericAccuracy: 100,
        groundedAccuracy: 100,
        refusalAccuracy: 100,
        evidenceRecall: 100,
        latency: "41.9 ms"
      },
      {
        variant: "Guarded LLM + XBRL",
        role: "Polished answer with fact guards",
        accuracy: 100,
        numericAccuracy: 100,
        groundedAccuracy: 100,
        refusalAccuracy: 100,
        evidenceRecall: 100,
        latency: "2.1 s"
      }
    ],
    generated: "Apple eval · 2026-04-19"
  },
  msft: {
    label: "Microsoft",
    title: "Microsoft filings expose where generic baselines lose grounding.",
    summary:
      "Microsoft questions cover the FY 2025 Form 10-K and FY 2026 quarterly filings, including financial facts, AI/export-control risks, segments, and refusal cases.",
    facts: [
      { label: "Questions", value: "24" },
      { label: "Filings", value: "2" },
      { label: "Issuer", value: "MSFT" },
      { label: "Best accuracy", value: "100%" }
    ],
    rows: [
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
        accuracy: 29.2,
        numericAccuracy: 16.7,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 64.6,
        latency: "58.9 ms"
      },
      {
        variant: "Filtered RAG",
        role: "Metadata-aware retrieval",
        accuracy: 50,
        numericAccuracy: 8.3,
        groundedAccuracy: 0,
        refusalAccuracy: 75,
        evidenceRecall: 100,
        latency: "55.6 ms"
      },
      {
        variant: "GPT-5 mini closed book",
        role: "Generic model baseline",
        accuracy: 8.3,
        numericAccuracy: 0,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 16.7,
        latency: "API"
      },
      {
        variant: "GPT-5 mini + retrieved context",
        role: "External model with excerpts",
        accuracy: 33.3,
        numericAccuracy: 41.7,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 100,
        latency: "API"
      },
      {
        variant: "GPT-5 mini + web search",
        role: "External model with web access",
        accuracy: 20.8,
        numericAccuracy: 16.7,
        groundedAccuracy: 0,
        refusalAccuracy: 50,
        evidenceRecall: 16.7,
        latency: "API"
      },
      {
        variant: "Filtered RAG + XBRL",
        role: "Retrieval plus structured facts",
        accuracy: 100,
        numericAccuracy: 100,
        groundedAccuracy: 100,
        refusalAccuracy: 100,
        evidenceRecall: 100,
        latency: "58.5 ms"
      },
      {
        variant: "Guarded LLM + XBRL",
        role: "Polished answer with fact guards",
        accuracy: 100,
        numericAccuracy: 100,
        groundedAccuracy: 100,
        refusalAccuracy: 100,
        evidenceRecall: 100,
        latency: "1.9 s"
      }
    ],
    generated: "Microsoft eval · 2026-04-19"
  }
};

const benchmarkFailures = [
  {
    label: "Closed-book limit",
    text: "GPT-5 mini refused issuer-specific filing questions without local evidence. The XBRL path answers exact values from parsed SEC facts."
  },
  {
    label: "Web-search limit",
    text: "Web search can find public numbers, but it still has 0% grounded numeric accuracy because it is not validating against local XBRL rows."
  },
  {
    label: "Structured fix",
    text: "The guarded path keeps XBRL facts authoritative, lets GPT-5 mini polish only supported answers, and falls back when validation fails."
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

type AnswerMode = "extractive" | "llm";
type SynthesisStatus = "not_requested" | "succeeded" | "fallback" | "unavailable";

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
  answer_mode: AnswerMode;
  fallback_answer?: string;
  synthesis_model?: string;
  synthesis_status: SynthesisStatus;
  synthesis_reason?: string;
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
  const [question, setQuestion] = useState(sampleQuestions[0].question);
  const [answerMode, setAnswerMode] = useState<AnswerMode>("llm");
  const [askResponse, setAskResponse] = useState<AskResponse | null>(null);
  const [compareResponse, setCompareResponse] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [benchmarkIssuer, setBenchmarkIssuer] = useState<BenchmarkIssuer>("all");

  const selectedFiling = useMemo(
    () => filings.find((filing) => filing.accessionNumber === accessionNumber),
    [accessionNumber]
  );

  async function submitAsk(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    setAskResponse(null);
    setCompareResponse(null);
    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          accession_number: accessionNumber,
          question,
          answer_mode: answerMode,
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
    setCompareResponse(null);
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
            <h1 id="workspace-title">Ask SEC filings with citations and XBRL checks.</h1>
          </div>
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
                  <option value="business">Business</option>
                  <option value="mda">MD&A</option>
                  <option value="financial_statements">Financial Statements</option>
                  <option value="controls">Controls</option>
                  <option value="legal_proceedings">Legal Proceedings</option>
                </select>

                <span className="field-label" id="answer-mode-label">
                  Answer style
                </span>
                <div
                  className="answer-mode-toggle"
                  role="radiogroup"
                  aria-labelledby="answer-mode-label"
                >
                  <button
                    className={answerMode === "llm" ? "active" : ""}
                    type="button"
                    role="radio"
                    aria-checked={answerMode === "llm"}
                    onClick={() => setAnswerMode("llm")}
                  >
                    Guarded LLM
                  </button>
                  <button
                    className={answerMode === "extractive" ? "active" : ""}
                    type="button"
                    role="radio"
                    aria-checked={answerMode === "extractive"}
                    onClick={() => setAnswerMode("extractive")}
                  >
                    Extractive
                  </button>
                </div>
                <p className="mode-help">
                  Guarded LLM uses the cited answer only and falls back when the checks fail.
                </p>

                <label htmlFor="question">Question</label>
                <textarea
                  id="question"
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                />

                <button disabled={isLoading || !question.trim()} type="submit">
                  {isLoading
                    ? answerMode === "llm"
                      ? "Checking and polishing..."
                      : "Running retrieval..."
                    : "Ask with citations"}
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
              <BenchmarkBrief
                benchmarkIssuer={benchmarkIssuer}
                onBenchmarkIssuerChange={setBenchmarkIssuer}
              />
            )}

            <div className="sample-block" aria-label="Sample questions">
              {sampleQuestions.map((sampleQuestion) => (
                <button
                  key={sampleQuestion.question}
                  type="button"
                  onClick={() => {
                    setMode("ask");
                    setAskResponse(null);
                    setCompareResponse(null);
                    setError(null);
                    setQuestion(sampleQuestion.question);
                    setAccessionNumber(sampleQuestion.accessionNumber);
                    setSectionType(sampleQuestion.sectionType);
                  }}
                >
                  {sampleQuestion.question}
                </button>
              ))}
            </div>
          </section>

          <section className="answer-panel" aria-label="Research result">
            <div className="filing-strip">
              {mode === "benchmark" ? (
                <>
                  <span>Benchmark</span>
                  <strong>{benchmarkDatasets[benchmarkIssuer].label}</strong>
                  <span>{benchmarkDatasets[benchmarkIssuer].facts[0].value} real questions</span>
                </>
              ) : (
                <>
                  <span>{selectedFiling?.formType}</span>
                  <strong>{selectedFiling?.period}</strong>
                  <span>{selectedFiling?.filedDate}</span>
                  <span>{selectedFiling?.label}</span>
                </>
              )}
            </div>

            {mode === "benchmark" ? (
              <BenchmarkResult benchmarkIssuer={benchmarkIssuer} />
            ) : (
              <>
                {error ? <div className="error-box">{error}</div> : null}
                {isLoading ? <LoadingState mode={mode} answerMode={answerMode} /> : null}
                {!askResponse && !compareResponse && !error && !isLoading ? <EmptyState /> : null}
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

function BenchmarkBrief({
  benchmarkIssuer,
  onBenchmarkIssuerChange
}: {
  benchmarkIssuer: BenchmarkIssuer;
  onBenchmarkIssuerChange: (issuer: BenchmarkIssuer) => void;
}) {
  const dataset = benchmarkDatasets[benchmarkIssuer];
  return (
    <section className="benchmark-brief" aria-label="Benchmark summary">
      <p className="panel-kicker">Tracked benchmark</p>
      <h2>Real filing questions, measured against generic model baselines.</h2>
      <p>{dataset.summary}</p>
      <label htmlFor="benchmark-issuer">Company filter</label>
      <select
        id="benchmark-issuer"
        value={benchmarkIssuer}
        onChange={(event) => onBenchmarkIssuerChange(event.target.value as BenchmarkIssuer)}
      >
        <option value="all">Apple + Microsoft</option>
        <option value="aapl">Apple</option>
        <option value="msft">Microsoft</option>
      </select>
      <div className="brief-grid">
        {dataset.facts.map((fact) => (
          <Metric key={fact.label} label={fact.label} value={fact.value} />
        ))}
      </div>
    </section>
  );
}

function EmptyState() {
  return (
    <div className="empty-state">
      <p className="panel-kicker">Ready</p>
      <h2>Ask a filing question and get a cited answer.</h2>
      <p>
        Try the revenue questions first. They return SEC citations plus a validated
        XBRL fact when the filing contains the requested metric.
      </p>
    </div>
  );
}

function LoadingState({ mode, answerMode }: { mode: Mode; answerMode: AnswerMode }) {
  const message =
    mode === "compare"
      ? "Comparing the selected filings and collecting cited changes."
      : answerMode === "llm"
        ? "Retrieving filing evidence, validating XBRL facts, then polishing the answer."
        : "Retrieving filing evidence and checking citations.";

  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-spinner" aria-hidden="true" />
      <div>
        <p className="panel-kicker">Thinking</p>
        <strong>{message}</strong>
      </div>
    </div>
  );
}

function BenchmarkResult({ benchmarkIssuer }: { benchmarkIssuer: BenchmarkIssuer }) {
  const dataset = benchmarkDatasets[benchmarkIssuer];
  return (
    <div className="result-stack benchmark-result">
      <div className="answer-heading">
        <p className="panel-kicker">Evaluation</p>
        <span>{dataset.generated}</span>
      </div>
      <h2>{dataset.title}</h2>

      <div className="benchmark-scoreboard" aria-label="Benchmark headline metrics">
        <Metric label="Best overall accuracy" value={bestMetric(dataset.rows, "accuracy")} />
        <Metric
          label="Best grounded numeric accuracy"
          value={bestMetric(dataset.rows, "groundedAccuracy")}
        />
        <Metric label="Guarded synthesis latency" value={guardedLatency(dataset.rows)} />
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
            {dataset.rows.map((row) => (
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

function bestMetric(
  rows: typeof benchmarkRows,
  key: "accuracy" | "groundedAccuracy" | "numericAccuracy"
) {
  return `${Math.max(...rows.map((row) => row[key])).toFixed(0)}%`;
}

function guardedLatency(rows: typeof benchmarkRows) {
  return rows.find((row) => row.variant === "Guarded LLM + XBRL")?.latency ?? "n/a";
}

function AskResult({ response }: { response: AskResponse }) {
  return (
    <div className="result-stack">
      <section className={`answer-card ${response.supported ? "supported" : "unsupported"}`}>
        <div className="answer-heading">
          <p className="panel-kicker">
            {response.supported ? "Supported answer" : "Insufficient evidence"}
          </p>
          <ConfidenceBadge confidence={response.confidence} />
        </div>
        <h2>{response.answer}</h2>
      </section>
      <div className="metric-grid">
        <Metric label="Query type" value={response.query_type} />
        <Metric label="Answer mode" value={formatAnswerMode(response.answer_mode)} />
        <Metric label="Synthesis" value={formatSynthesisStatus(response)} />
        <Metric label="Retrieved chunks" value={String(response.retrieval_count)} />
        <Metric label="Citations" value={String(response.citations.length)} />
      </div>

      {response.synthesis_status !== "not_requested" ? (
        <section
          className={`synthesis-line ${response.synthesis_status}`}
          aria-label="LLM synthesis status"
        >
          <p className="panel-kicker">Synthesis guard</p>
          <strong>{formatSynthesisStatus(response)}</strong>
          <span>{synthesisMessage(response)}</span>
        </section>
      ) : null}

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

function ConfidenceBadge({ confidence }: { confidence: number }) {
  const percent = Math.round(confidence * 100);
  const tone = percent >= 80 ? "high" : percent >= 50 ? "medium" : "low";
  return <span className={`confidence-badge ${tone}`}>{percent}% confidence</span>;
}

function formatAnswerMode(answerMode: AnswerMode) {
  return answerMode === "llm" ? "Guarded LLM" : "Extractive";
}

function formatSynthesisStatus(response: AskResponse) {
  if (response.synthesis_status === "succeeded") {
    return response.synthesis_model ? `Succeeded · ${response.synthesis_model}` : "Succeeded";
  }
  if (response.synthesis_status === "unavailable") {
    return "Unavailable";
  }
  if (response.synthesis_status === "fallback") {
    return "Fallback";
  }
  return "Not requested";
}

function synthesisMessage(response: AskResponse) {
  if (response.synthesis_status === "succeeded") {
    return "The polished answer passed citation, refusal, and numeric grounding checks.";
  }
  if (response.synthesis_status === "unavailable") {
    return `Using the deterministic cited answer: ${response.synthesis_reason ?? "not available"}.`;
  }
  return `Using the deterministic cited answer: ${response.synthesis_reason ?? "guard check"}.`;
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
