import { useEffect, useMemo, useState } from 'react'
import { Layout } from '../components/Layout'
import '../styles/evaluation-harness.css'

type ConfigOption = {
  id: string
  label: string
}

type TestSetOption = ConfigOption & {
  case_count: number
}

type TestingConfig = {
  test_sets: TestSetOption[]
  models: ConfigOption[]
  retrieval_strategies: string[]
  defaults: {
    test_set: string
    model: string
    retrieval_strategy: string
    top_k: number
  }
}

type MetricCard = {
  key: string
  label: string
  display: string
  gate: string
  outcome: 'pass' | 'fail' | 'info'
}

type RunSummary = {
  cases: number
  provider_failures: number
  passed_cases: number
  failed_cases: number
  gates_met: boolean | null
  metric_cards: MetricCard[]
}

type EvaluationRun = {
  run_id: string
  status: 'starting' | 'running' | 'stopping' | 'completed' | 'failed' | 'interrupted'
  test_set: string
  test_set_label: string
  model: string
  use_judge: boolean
  judge_model: string | null
  retrieval_strategy: string
  top_k: number
  completed: number
  total: number
  passed: number
  failed: number
  remaining: number
  current_case: string | null
  elapsed_seconds: number
  started_at: string
  finished_at: string | null
  error: string | null
  summary: RunSummary | null
}

type EvaluationMetrics = {
  expected_source_hit?: boolean | null
  top1_source_hit?: boolean | null
  recall_at_k?: number | null
  reciprocal_rank?: number | null
  citation_present?: boolean | null
  citation_valid?: boolean | null
  citation_format_standard?: boolean | null
  refusal_correct?: boolean | null
  provider_available?: boolean | null
  refused?: boolean | null
}

type RetrievedChunk = {
  chunk_id: number
  document_id: number
  chunk_index: number
  filename: string
  source_label: string | null
  similarity: number | null
  content_preview: string
}

type EvaluationJudge = {
  correctness?: number
  faithfulness?: number
  reason?: string
  error?: string
} | null

type EvaluationResult = {
  id: string
  class: string | null
  use_case: string | null
  question: string
  expected_source: string | null
  expected_sources: string[]
  expected_outcome: string | null
  must_refuse: boolean
  model_name: string | null
  retrieval_strategy: string | null
  top_k: number | null
  model_answer: string | null
  retrieved_files: string[]
  retrieved_chunks: RetrievedChunk[]
  metrics: EvaluationMetrics
  judge: EvaluationJudge
  retrieval_latency_ms: number | null
  generation_latency_ms: number | null
  latency_ms: number | null
  status: string
  created_at: string | null
  failures: string[]
}

type EvaluationResultsResponse = {
  run_id: string
  status: string
  completed: number
  results: EvaluationResult[]
}

const TERMINAL = new Set(['completed', 'failed', 'interrupted'])

function readError(payload: unknown, fallback: string): string {
  if (
    payload &&
    typeof payload === 'object' &&
    'detail' in payload &&
    typeof (payload as { detail?: unknown }).detail === 'string'
  ) {
    return (payload as { detail: string }).detail
  }

  return fallback
}

function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  return `${String(minutes).padStart(2, '0')}m ${String(remainingSeconds).padStart(2, '0')}s`
}

function statusLabel(status: EvaluationRun['status']): string {
  if (status === 'starting') return 'STARTING'
  if (status === 'running') return 'RUNNING'
  if (status === 'stopping') return 'STOPPING'
  if (status === 'completed') return 'RUN COMPLETE'
  if (status === 'interrupted') return 'RUN INTERRUPTED'
  return 'RUN FAILED'
}

function formatBooleanMetric(value: boolean | null | undefined): string {
  if (value === true) return 'PASS'
  if (value === false) return 'FAIL'
  return 'N/A'
}

function formatRatio(value: number | null | undefined): string {
  if (typeof value !== 'number') return 'N/A'
  return `${Math.round(value * 100)}%`
}

function formatDecimal(value: number | null | undefined): string {
  if (typeof value !== 'number') return 'N/A'
  return value.toFixed(2)
}

function formatJudgeScore(value: number | undefined): string {
  if (typeof value !== 'number') return 'Not run'
  return `${value.toFixed(1)} / 5`
}

function formatLatencyMs(value: number | null | undefined): string {
  if (typeof value !== 'number') return 'N/A'
  return `${(value / 1000).toFixed(1)}s`
}

export function Testing() {
  const [config, setConfig] = useState<TestingConfig | null>(null)
  const [configError, setConfigError] = useState<string | null>(null)

  const [testSet, setTestSet] = useState('')
  const [model, setModel] = useState('')
  const [useJudge, setUseJudge] = useState(false)
  const [judgeModel, setJudgeModel] = useState('')
  const [retrievalStrategy, setRetrievalStrategy] = useState('hybrid')
  const [topK, setTopK] = useState(6)

  const [run, setRun] = useState<EvaluationRun | null>(null)
  const [starting, setStarting] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const [results, setResults] = useState<EvaluationResult[]>([])
  const [resultsError, setResultsError] = useState<string | null>(null)
  const [resultFilter, setResultFilter] = useState<'all' | 'failed'>('all')
  const [expandedResultId, setExpandedResultId] = useState<string | null>(null)

  const isActive = Boolean(run && !TERMINAL.has(run.status))

  const isCompleteRun = Boolean(
    run &&
    run.status === 'completed' &&
    run.completed === run.total,
  )

  useEffect(() => {
    let cancelled = false

    fetch('/api/testing/config', { credentials: 'include' })
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}))
        if (!response.ok) {
          throw new Error(readError(payload, 'Could not load evaluation settings.'))
        }
        return payload as TestingConfig
      })
      .then((payload) => {
        if (cancelled) return

        setConfig(payload)
        setTestSet(payload.defaults.test_set)
        setModel(payload.defaults.model)
        setJudgeModel(payload.defaults.model)
        setRetrievalStrategy(payload.defaults.retrieval_strategy)
        setTopK(payload.defaults.top_k)
      })
      .catch((error) => {
        if (!cancelled) {
          setConfigError(error instanceof Error ? error.message : 'Could not load evaluation settings.')
        }
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!config) return

    let cancelled = false

    const restoreActiveRun = async () => {
      try {
        const response = await fetch('/api/testing/runs/active', {
          credentials: 'include',
        })

        if (response.status === 404) return

        const payload = await response.json().catch(() => ({}))

        if (!response.ok) {
          throw new Error(readError(payload, 'Could not restore the active evaluation run.'))
        }

        if (!cancelled) {
          setRun(payload as EvaluationRun)
        }
      } catch (error) {
        if (!cancelled) {
          setActionError(
            error instanceof Error ? error.message : 'Could not restore the active evaluation run.',
          )
        }
      }
    }

    void restoreActiveRun()

    return () => {
      cancelled = true
    }
  }, [config])

  const activeRunId = run?.run_id
  const activeRunStatus = run?.status

  useEffect(() => {
    if (!activeRunId || !activeRunStatus || TERMINAL.has(activeRunStatus)) return

    let cancelled = false

    const refresh = async () => {
      try {
        const response = await fetch(`/api/testing/runs/${activeRunId}`, {
          credentials: 'include',
        })
        const payload = await response.json().catch(() => ({}))

        if (!response.ok) {
          throw new Error(readError(payload, 'Could not refresh the evaluation run.'))
        }

        if (!cancelled) {
          setRun(payload as EvaluationRun)
        }
      } catch (error) {
        if (!cancelled) {
          setActionError(
            error instanceof Error ? error.message : 'Could not refresh the evaluation run.',
          )
        }
      }
    }

    const interval = window.setInterval(refresh, 1200)
    void refresh()

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [activeRunId, activeRunStatus])

  const resultRunId = run?.run_id
  const completedResultCount = run?.completed ?? 0

  useEffect(() => {
    if (!resultRunId || completedResultCount === 0) return

    let cancelled = false

    const loadResults = async () => {
      try {
        const response = await fetch(
          `/api/testing/runs/${resultRunId}/results`,
          { credentials: 'include' },
        )

        const payload = await response.json().catch(() => ({}))

        if (!response.ok) {
          throw new Error(
            readError(payload, 'Could not load per-question evaluation results.'),
          )
        }

        if (!cancelled) {
          const resultPayload = payload as EvaluationResultsResponse
          setResults(resultPayload.results)
          setResultsError(null)
        }
      } catch (error) {
        if (!cancelled) {
          setResultsError(
            error instanceof Error
              ? error.message
              : 'Could not load per-question evaluation results.',
          )
        }
      }
    }

    void loadResults()

    return () => {
      cancelled = true
    }
  }, [resultRunId, completedResultCount])

  const progress = useMemo(() => {
    if (!run || run.total === 0) return 0
    return Math.min(100, Math.round((run.completed / run.total) * 100))
  }, [run])

  const selectedTestSet = config?.test_sets.find((item) => item.id === testSet)

  const visibleResults = useMemo(
    () =>
      resultFilter === 'failed'
        ? results.filter((result) => result.failures.length > 0)
        : results,
    [resultFilter, results],
  )

  const failedResultCount = useMemo(
    () => results.filter((result) => result.failures.length > 0).length,
    [results],
  )

  const handleStart = async () => {
    setStarting(true)
    setActionError(null)
    setResultsError(null)
    setResults([])
    setResultFilter('all')
    setExpandedResultId(null)

    try {
      const response = await fetch('/api/testing/runs', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          test_set: testSet,
          model,
          use_judge: useJudge,
          judge_model: useJudge ? judgeModel : null,
          retrieval_strategy: retrievalStrategy,
          top_k: topK,
        }),
      })

      const payload = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(readError(payload, 'Could not start the evaluation run.'))
      }

      setRun(payload as EvaluationRun)
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not start the evaluation run.')
    } finally {
      setStarting(false)
    }
  }

  const handleStop = async () => {
    if (!run) return

    setActionError(null)

    try {
      const response = await fetch(`/api/testing/runs/${run.run_id}/stop`, {
        method: 'POST',
        credentials: 'include',
      })
      const payload = await response.json().catch(() => ({}))

      if (!response.ok) {
        throw new Error(readError(payload, 'Could not stop the evaluation run.'))
      }

      setRun(payload as EvaluationRun)
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not stop the evaluation run.')
    }
  }

  return (
    <Layout badge="INTERNAL · SPRINT 3">
      <div className="evaluation-page">
        <div className="page-header">
          <h1 className="welcome-title">LLM Testing &amp; Evaluation</h1>
          <p className="welcome-subtitle">
            Run the benchmark against a configured model and review retrieval, citation,
            refusal and response-quality metrics.
          </p>
        </div>

        {configError && <div className="error-message">{configError}</div>}
        {actionError && <div className="error-message">{actionError}</div>}

        <section className="eval-card">
          <div className="eval-card__header">
            <div>
              <div className="eval-eyebrow">RUN CONFIGURATION</div>
              <h2>Benchmark settings</h2>
            </div>

            <button
              type="button"
              className="btn-primary eval-run-button"
              onClick={handleStart}
              disabled={!config || starting || isActive}
            >
              {starting ? 'Starting…' : 'Run Benchmark'}
            </button>
          </div>

          <div className="eval-config-grid">
            <div className="field-group">
              <label htmlFor="eval-test-set">Test Set</label>
              <select
                id="eval-test-set"
                value={testSet}
                onChange={(event) => setTestSet(event.target.value)}
                disabled={!config || isActive}
              >
                {config?.test_sets.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label} – {item.case_count} cases
                  </option>
                ))}
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="eval-model">Model</label>
              <select
                id="eval-model"
                value={model}
                onChange={(event) => setModel(event.target.value)}
                disabled={!config || isActive}
              >
                {config?.models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="eval-strategy">Retrieval</label>
              <select
                id="eval-strategy"
                value={retrievalStrategy}
                onChange={(event) => setRetrievalStrategy(event.target.value)}
                disabled={!config || isActive}
              >
                {config?.retrieval_strategies.map((strategy) => (
                  <option key={strategy} value={strategy}>
                    {strategy[0].toUpperCase() + strategy.slice(1)}
                  </option>
                ))}
              </select>
            </div>

            <div className="field-group">
              <label htmlFor="eval-top-k">Top K</label>
              <input
                id="eval-top-k"
                type="number"
                min={1}
                max={20}
                value={topK}
                onChange={(event) => setTopK(Number(event.target.value))}
                disabled={isActive}
              />
            </div>
          </div>

          <label className="eval-checkbox">
            <input
              type="checkbox"
              checked={useJudge}
              onChange={(event) => setUseJudge(event.target.checked)}
              disabled={isActive}
            />
            <span>
              <strong>Use LLM Judge</strong>
              <small>
                Adds correctness and faithfulness scores. These scores are informational
                until human validated.
              </small>
            </span>
          </label>

          {useJudge && (
            <div className="field-group eval-judge-field">
              <label htmlFor="eval-judge-model">Judge Model</label>
              <select
                id="eval-judge-model"
                value={judgeModel}
                onChange={(event) => setJudgeModel(event.target.value)}
                disabled={!config || isActive}
              >
                {config?.models.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div className="eval-config-note">
            {selectedTestSet
              ? `${selectedTestSet.case_count} benchmark cases will run sequentially.`
              : 'Loading benchmark information…'}
          </div>
        </section>

        {run && (
          <section className="eval-card">
            <div className="eval-card__header">
              <div>
                <div className={`eval-status eval-status--${run.status}`}>
                  {statusLabel(run.status)}
                </div>
                <h2>Run #{run.run_id}</h2>
                <p className="eval-muted">
                  {run.test_set_label} · {run.model} · {run.retrieval_strategy} retrieval
                </p>
              </div>

              {(run.status === 'starting' || run.status === 'running') && (
                <button type="button" className="btn-secondary eval-stop-button" onClick={handleStop}>
                  Stop Run
                </button>
              )}
            </div>

            <div className="eval-progress-line">
              <div>
                <strong>
                  {run.completed} / {run.total} cases completed
                </strong>
                <span>{progress}%</span>
              </div>
              <div className="eval-progress-track" aria-label={`${progress}% complete`}>
                <div className="eval-progress-fill" style={{ width: `${progress}%` }} />
              </div>
            </div>

            <div className="eval-stat-grid">
              <div className="eval-stat">
                <span>Passed</span>
                <strong>{run.passed}</strong>
              </div>
              <div className="eval-stat">
                <span>Failed</span>
                <strong>{run.failed}</strong>
              </div>
              <div className="eval-stat">
                <span>Running</span>
                <strong>{isActive && run.current_case ? 1 : 0}</strong>
              </div>
              <div className="eval-stat">
                <span>Remaining</span>
                <strong>{run.remaining}</strong>
              </div>
              <div className="eval-stat">
                <span>Elapsed</span>
                <strong>{formatElapsed(run.elapsed_seconds)}</strong>
              </div>
            </div>

            {run.current_case && isActive && (
              <div className="eval-current-case">
                Current case: <strong>{run.current_case}</strong>
              </div>
            )}

            {run.status === 'stopping' && (
              <div className="eval-info-banner">Stopping the evaluation process…</div>
            )}

            {run.status === 'interrupted' && (
              <div className="eval-warning-banner">
                The run was stopped. Completed case results were preserved for this server session.
              </div>
            )}

            {run.status === 'failed' && (
              <div className="error-message">
                {run.error || 'The evaluation run failed. Please retry.'}
              </div>
            )}
          </section>
        )}

        {run?.summary && (
          <section className="eval-card">
            <div className="eval-card__header">
              <div>
                <div className="eval-eyebrow">SUMMARY METRICS</div>
                <h2>Evaluation results</h2>
              </div>

              <div
                className={`eval-release-gate ${
                  !isCompleteRun
                    ? ''
                    : run.summary.gates_met
                      ? 'eval-release-gate--pass'
                      : 'eval-release-gate--fail'
                }`}
              >
                {!isCompleteRun
                  ? 'Partial run · gates informational'
                  : run.summary.gates_met
                    ? 'Release gates met'
                    : 'Release gates not met'}
              </div>
            </div>

            <div className="eval-summary-strip">
              <span>{run.summary.cases} cases</span>
              <span>{run.summary.passed_cases} passed</span>
              <span>{run.summary.failed_cases} failed</span>
              <span>{run.summary.provider_failures} provider failures</span>
            </div>

            <div className="eval-metric-grid">
              {run.summary.metric_cards.map((metric) => (
                <article className="eval-metric-card" key={metric.key}>
                  <div className="eval-metric-card__top">
                    <span>{metric.label}</span>
                    <span className={`eval-outcome eval-outcome--${metric.outcome}`}>
                      {metric.outcome === 'pass'
                        ? 'PASS'
                        : metric.outcome === 'fail'
                          ? 'FAIL'
                          : 'INFO'}
                    </span>
                  </div>

                  <strong>{metric.display}</strong>
                  <small>{metric.gate}</small>
                </article>
              ))}
            </div>

            <div className="eval-planned">
              <div className="eval-eyebrow">PLANNED METRICS</div>
              <div className="eval-planned-grid">
                <span>Temporal Precision · Not implemented</span>
                <span>Citation Support · Not implemented</span>
                <span>Corpus Attribution · Not implemented</span>
                <span>Cost Per Query · Not implemented</span>
              </div>
            </div>
          </section>
        )}

        {results.length > 0 && (
          <section className="eval-card">
            <div className="eval-card__header eval-results-header">
              <div>
                <div className="eval-eyebrow">QUESTION RESULTS</div>
                <h2>Per-question evaluation</h2>
                <p className="eval-muted">
                  Inspect generated answers, retrieved sources and individual scores
                  from this recorded run.
                </p>
              </div>

              <div className="eval-result-filters" aria-label="Result filters">
                <button
                  type="button"
                  className={resultFilter === 'all' ? 'is-active' : ''}
                  onClick={() => setResultFilter('all')}
                >
                  All ({results.length})
                </button>

                <button
                  type="button"
                  className={resultFilter === 'failed' ? 'is-active' : ''}
                  onClick={() => setResultFilter('failed')}
                >
                  Failed ({failedResultCount})
                </button>
              </div>
            </div>

            {resultsError && <div className="error-message">{resultsError}</div>}

            {visibleResults.length === 0 ? (
              <div className="eval-results-empty">
                No failed questions in the recorded results.
              </div>
            ) : (
              <div className="eval-results-table-wrap">
                <table className="eval-results-table">
                  <thead>
                    <tr>
                      <th>Case</th>
                      <th>Question</th>
                      <th>Expected source</th>
                      <th>Expected outcome</th>
                      <th>Source</th>
                      <th>Citation</th>
                      <th>Latency</th>
                      <th>Result</th>
                      <th aria-label="Expand" />
                    </tr>
                  </thead>

                  <tbody>
                    {visibleResults.map((result) => {
                      const expanded = expandedResultId === result.id
                      const failed = result.failures.length > 0
                      const metrics = result.metrics ?? {}

                      return (
                        <>
                          <tr
                            key={result.id}
                            className={`eval-result-row ${
                              failed ? 'eval-result-row--failed' : ''
                            }`}
                          >
                            <td>
                              <strong>{result.id}</strong>
                              {result.class && (
                                <small className="eval-result-class">
                                  {result.class}
                                </small>
                              )}
                            </td>

                            <td className="eval-result-question">
                              {result.question}
                            </td>

                            <td>
                              {result.expected_sources.length > 0
                                ? result.expected_sources.join(', ')
                                : 'None expected'}
                            </td>

                            <td>
                              <span
                                className="eval-result-outcome-text"
                                title={result.expected_outcome || ''}
                              >
                                {result.expected_outcome || 'Not specified'}
                              </span>
                            </td>

                            <td>
                              {formatBooleanMetric(metrics.expected_source_hit)}
                            </td>

                            <td>
                              {formatBooleanMetric(metrics.citation_valid)}
                            </td>

                            <td>{formatLatencyMs(result.latency_ms)}</td>

                            <td>
                              <span
                                className={`eval-case-badge ${
                                  failed
                                    ? 'eval-case-badge--fail'
                                    : 'eval-case-badge--pass'
                                }`}
                              >
                                {failed ? 'FAIL' : 'PASS'}
                              </span>
                            </td>

                            <td>
                              <button
                                type="button"
                                className="eval-expand-button"
                                aria-expanded={expanded}
                                onClick={() =>
                                  setExpandedResultId(
                                    expanded ? null : result.id,
                                  )
                                }
                              >
                                {expanded ? '−' : '+'}
                              </button>
                            </td>
                          </tr>

                          {expanded && (
                            <tr
                              key={`${result.id}-details`}
                              className="eval-result-details-row"
                            >
                              <td colSpan={9}>
                                <div className="eval-result-details">
                                  {failed && (
                                    <div className="eval-case-failures">
                                      <strong>Failed checks</strong>
                                      <ul>
                                        {result.failures.map((failure) => (
                                          <li key={failure}>{failure}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}

                                  <div className="eval-detail-grid">
                                    <section>
                                      <div className="eval-eyebrow">
                                        EXPECTED OUTCOME
                                      </div>
                                      <p>
                                        {result.expected_outcome ||
                                          'No expected outcome recorded.'}
                                      </p>
                                    </section>

                                    <section>
                                      <div className="eval-eyebrow">
                                        GENERATED ANSWER
                                      </div>
                                      <p className="eval-answer-text">
                                        {result.model_answer ||
                                          'No answer was returned.'}
                                      </p>
                                    </section>
                                  </div>

                                  <div className="eval-detail-section">
                                    <div className="eval-eyebrow">
                                      RETRIEVED SOURCES
                                    </div>

                                    {result.retrieved_chunks.length === 0 ? (
                                      <p className="eval-muted">
                                        No retrieved chunks recorded.
                                      </p>
                                    ) : (
                                      <div className="eval-source-list">
                                        {result.retrieved_chunks.map(
                                          (chunk, index) => (
                                            <article
                                              className="eval-source-item"
                                              key={chunk.chunk_id}
                                            >
                                              <div className="eval-source-item__header">
                                                <strong>
                                                  {index + 1}.{' '}
                                                  {chunk.source_label ||
                                                    chunk.filename}
                                                </strong>
                                                <span>
                                                  Chunk {chunk.chunk_index}
                                                  {typeof chunk.similarity ===
                                                  'number'
                                                    ? ` · similarity ${chunk.similarity.toFixed(2)}`
                                                    : ''}
                                                </span>
                                              </div>

                                              <p>{chunk.content_preview}</p>
                                            </article>
                                          ),
                                        )}
                                      </div>
                                    )}
                                  </div>

                                  <div className="eval-detail-section">
                                    <div className="eval-eyebrow">SCORES</div>

                                    <div className="eval-case-score-grid">
                                      <div>
                                        <span>Expected source hit</span>
                                        <strong>
                                          {formatBooleanMetric(
                                            metrics.expected_source_hit,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Recall @ K</span>
                                        <strong>
                                          {formatRatio(metrics.recall_at_k)}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>MRR</span>
                                        <strong>
                                          {formatDecimal(
                                            metrics.reciprocal_rank,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Citation present</span>
                                        <strong>
                                          {formatBooleanMetric(
                                            metrics.citation_present,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Citation valid</span>
                                        <strong>
                                          {formatBooleanMetric(
                                            metrics.citation_valid,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Citation format</span>
                                        <strong>
                                          {formatBooleanMetric(
                                            metrics.citation_format_standard,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Refusal correct</span>
                                        <strong>
                                          {formatBooleanMetric(
                                            metrics.refusal_correct,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Correctness</span>
                                        <strong>
                                          {formatJudgeScore(
                                            result.judge?.correctness,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Faithfulness</span>
                                        <strong>
                                          {formatJudgeScore(
                                            result.judge?.faithfulness,
                                          )}
                                        </strong>
                                      </div>

                                      <div>
                                        <span>Total latency</span>
                                        <strong>
                                          {formatLatencyMs(result.latency_ms)}
                                        </strong>
                                      </div>
                                    </div>

                                    {result.judge?.reason && (
                                      <div className="eval-judge-reason">
                                        <strong>Judge note:</strong>{' '}
                                        {result.judge.reason}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}

        <div className="eval-scope-note">
          Question details are loaded from the recorded evaluation output.
          Opening a result does not rerun the benchmark.
        </div>
      </div>
    </Layout>
  )
}
