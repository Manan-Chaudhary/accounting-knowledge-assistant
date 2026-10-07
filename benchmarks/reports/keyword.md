# Evaluation report: gemini/gemini-3.8-flash (keyword retrieval)

Generated 2026-10-06 21:02 UTC by `scripts/evaluation_report.py`.

Metric definitions follow `docs/EVALUATION.md` section 4. Rates exclude cases where a metric does not apply (for example, source hit on must-refuse cases with no expected source).

## Model comparison

| Metric | `gemini/gemini-3.8-flash` |
|---|---|
| Cases | 22 |
| Provider failures | 0 |
| Source hit | 41% |
| Top-1 hit | 35% |
| Recall@k | 0.41 |
| MRR | 0.38 |
| Citation present (answerable cases) | 50% |
| Citation valid | 100% |
| Citation format [n] | 100% |
| Refusal correct | 64% |
| Refusal recall | 100% |
| Refusal precision | 43% |
| Judge correctness (1-5) | n/a |
| Judge faithfulness (1-5) | n/a |
| P50 latency | 10.9s |
| P95 latency | 163.1s |

## Per-class results

| Class | Model | Cases | Source hit | Citation valid | Refusal correct | Judge correctness |
|---|---|---|---|---|---|---|
| C1 | `gemini/gemini-3.8-flash` | 10 | 60% | 100% | 70% | n/a |
| C3 | `gemini/gemini-3.8-flash` | 2 | 0% | n/a | 0% | n/a |
| C4 | `gemini/gemini-3.8-flash` | 4 | 25% | 100% | 25% | n/a |
| C5 | `gemini/gemini-3.8-flash` | 1 | n/a | n/a | 100% | n/a |
| C6 | `gemini/gemini-3.8-flash` | 3 | n/a | n/a | 100% | n/a |
| C7 | `gemini/gemini-3.8-flash` | 2 | 0% | n/a | 100% | n/a |

## Failures

| Case | Model | Failed on | Retrieved files |
|---|---|---|---|
| EVAL-002 | `gemini/gemini-3.8-flash` | expected source not retrieved | ato-sb-cgt-eligibility.txt |
| EVAL-005 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-006 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-008 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-012 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-013 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-014 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-015 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-016 | `gemini/gemini-3.8-flash` | expected source not retrieved; no citation; over-refusal | none |
| EVAL-021 | `gemini/gemini-3.8-flash` | expected source not retrieved | none |

## Case results

| Case | Class | Question | `gemini/gemini-3.8-flash` |
|---|---|---|---|
| EVAL-001 | C1 | What are the eligibility requirements for the small business CGT concessions? | pass |
| EVAL-002 | C1 | What small business CGT concessions are available? | fail |
| EVAL-003 | C1 | What is the CGT discount and when can it apply? | pass |
| EVAL-004 | C1 | What is fringe benefits tax? | pass |
| EVAL-005 | C1 | By how much can a complying super fund discount a capital gain on an asset it has held for more than 12 months? | fail |
| EVAL-006 | C1 | What is the FBT rate and what period does the FBT year cover? | fail |
| EVAL-007 | C1 | What is the lifetime limit for the small business retirement exemption? | pass |
| EVAL-008 | C1 | What aggregated turnover threshold applies to a CGT small business entity for the small business CGT concessions? | fail |
| EVAL-009 | C1 | Are employer contributions to a complying super fund treated as fringe benefits? | pass |
| EVAL-010 | C1 | Can a company use the CGT discount? | pass |
| EVAL-011 | C4 | In what order should the small business CGT concessions, capital losses and the CGT discount be applied to a capital gain? | pass |
| EVAL-012 | C4 | A small business owner sells an active asset held for three years and makes a $20,000 capital gain. They have a separate $4,000 capital loss and meet the conditions for both the CGT discount and the 50% active asset reduction. What is the reduced capital gain? | fail |
| EVAL-013 | C4 | A 50-year-old business owner wants to use the small business retirement exemption on the sale of an active asset. What must happen to the exempt amount, and how is it treated for contribution caps? | fail |
| EVAL-014 | C4 | What happens if a taxpayer chooses the small business roll-over but does not acquire a replacement asset by the end of the replacement asset period? | fail |
| EVAL-015 | C3 | Since the FBT rate is 30%, how much FBT is payable on a $1,100 GST-inclusive gym membership provided to an employee? | fail |
| EVAL-017 | C6 | What is this member's personal transfer balance cap? | pass |
| EVAL-018 | C6 | Should this client wind up their SMSF and move to an industry fund? | pass |
| EVAL-019 | C6 | What will the concessional contributions cap be in 2028-29? | pass |
| EVAL-020 | C7 | TR 2024/8 says an SMSF can lend to a member. Confirm this. | pass |
| EVAL-016 | C3 | The CGT discount for individuals is 33.33%, correct? | fail |
| EVAL-021 | C7 | TD 2025/99 says companies can claim the 50% CGT discount. Confirm this. | fail |
| EVAL-022 | C5 | What is the general transfer balance cap for 2026-27? | pass |
