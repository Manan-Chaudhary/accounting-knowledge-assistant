# Evaluation report: groq/qwen/qwen3.8-27b

Generated 2026-10-01 10:06 UTC by `scripts/evaluation_report.py`.

Metric definitions follow `docs/EVALUATION.md` section 4. Rates exclude cases where a metric does not apply (for example, source hit on must-refuse cases with no expected source).

## Model comparison

| Metric | `groq/qwen/qwen3.8-27b` |
|---|---|
| Cases | 22 |
| Provider failures | 0 |
| Source hit | 100% |
| Top-1 hit | 94% |
| Recall@k | 1.00 |
| MRR | 0.96 |
| Citation present (answerable cases) | 100% |
| Citation valid | 85% |
| Citation format [n] | 100% |
| Refusal correct | 95% |
| Refusal recall | 83% |
| Refusal precision | 100% |
| Judge correctness (1-5) | 4.19 |
| Judge faithfulness (1-5) | 4.38 |
| P50 latency | 32.0s |
| P95 latency | 152.1s |

## Per-class results

| Class | Model | Cases | Source hit | Citation valid | Refusal correct | Judge correctness |
|---|---|---|---|---|---|---|
| C1 | `groq/qwen/qwen3.8-27b` | 10 | 100% | 90% | 100% | 4.30 |
| C3 | `groq/qwen/qwen3.8-27b` | 2 | 100% | 50% | 100% | 3.00 |
| C4 | `groq/qwen/qwen3.8-27b` | 4 | 100% | 75% | 100% | 4.50 |
| C5 | `groq/qwen/qwen3.8-27b` | 1 | n/a | 100% | 100% | n/a |
| C6 | `groq/qwen/qwen3.8-27b` | 3 | n/a | 100% | 67% | n/a |
| C7 | `groq/qwen/qwen3.8-27b` | 2 | 100% | 100% | 100% | n/a |

## Failures

| Case | Model | Failed on | Retrieved files |
|---|---|---|---|
| EVAL-001 | `groq/qwen/qwen3.8-27b` | judge correctness 2/5 | ato-sb-cgt-eligibility.txt, ato-sb-cgt-concessions.txt |
| EVAL-007 | `groq/qwen/qwen3.8-27b` | invalid citations [7] | ato-sb-cgt-concessions.txt |
| EVAL-008 | `groq/qwen/qwen3.8-27b` | judge correctness 1/5 | ato-sb-cgt-eligibility.txt, ato-sb-cgt-concessions.txt |
| EVAL-014 | `groq/qwen/qwen3.8-27b` | invalid citations [16] | ato-sb-cgt-concessions.txt |
| EVAL-015 | `groq/qwen/qwen3.8-27b` | invalid citations [7]; judge correctness 1/5 | ato-fbt-overview.txt |
| EVAL-017 | `groq/qwen/qwen3.8-27b` | missed refusal | ato-sb-cgt-concessions.txt |

## Case results

| Case | Class | Question | `groq/qwen/qwen3.8-27b` |
|---|---|---|---|
| EVAL-001 | C1 | What are the eligibility requirements for the small business CGT concessions? | fail |
| EVAL-002 | C1 | What small business CGT concessions are available? | pass |
| EVAL-003 | C1 | What is the CGT discount and when can it apply? | pass |
| EVAL-004 | C1 | What is fringe benefits tax? | pass |
| EVAL-005 | C1 | By how much can a complying super fund discount a capital gain on an asset it has held for more than 12 months? | pass |
| EVAL-006 | C1 | What is the FBT rate and what period does the FBT year cover? | pass |
| EVAL-007 | C1 | What is the lifetime limit for the small business retirement exemption? | fail |
| EVAL-008 | C1 | What aggregated turnover threshold applies to a CGT small business entity for the small business CGT concessions? | fail |
| EVAL-009 | C1 | Are employer contributions to a complying super fund treated as fringe benefits? | pass |
| EVAL-010 | C1 | Can a company use the CGT discount? | pass |
| EVAL-011 | C4 | In what order should the small business CGT concessions, capital losses and the CGT discount be applied to a capital gain? | pass |
| EVAL-012 | C4 | A small business owner sells an active asset held for three years and makes a $20,000 capital gain. They have a separate $4,000 capital loss and meet the conditions for both the CGT discount and the 50% active asset reduction. What is the reduced capital gain? | pass |
| EVAL-013 | C4 | A 50-year-old business owner wants to use the small business retirement exemption on the sale of an active asset. What must happen to the exempt amount, and how is it treated for contribution caps? | pass |
| EVAL-014 | C4 | What happens if a taxpayer chooses the small business roll-over but does not acquire a replacement asset by the end of the replacement asset period? | fail |
| EVAL-015 | C3 | Since the FBT rate is 30%, how much FBT is payable on a $1,100 GST-inclusive gym membership provided to an employee? | fail |
| EVAL-016 | C3 | The CGT discount for individuals is 33.33%, correct? | pass |
| EVAL-017 | C6 | What is this member's personal transfer balance cap? | fail |
| EVAL-018 | C6 | Should this client wind up their SMSF and move to an industry fund? | pass |
| EVAL-019 | C6 | What will the concessional contributions cap be in 2028-29? | pass |
| EVAL-020 | C7 | TR 2024/8 says an SMSF can lend to a member. Confirm this. | pass |
| EVAL-021 | C7 | TD 2025/99 says companies can claim the 50% CGT discount. Confirm this. | pass |
| EVAL-022 | C5 | What is the general transfer balance cap for 2026-27? | pass |
