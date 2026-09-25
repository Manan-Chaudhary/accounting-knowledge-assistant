# Document Corpus (Corpus A - Authority)

Card: [DOCUMENT INGESTION] Gather sample accounting documentation that supports use cases identified (#120).

This is the first set of public authority documents for the knowledge base. It covers Alfa Focus's SMSF service lines (the seven use cases in [`USE-CASES.md`](USE-CASES.md)) and the wider accounting topics accountants at the firm are likely to ask about: Division 7A, FBT, CGT concessions, residency, GST/BAS, payroll and employer super, trusts, deceased estates, financial reporting and professional obligations.

Retrieved 2026-09-25. All sources are Tier 1-3 as defined in [`DOMAIN-PRIMER.md`](DOMAIN-PRIMER.md) section 3. There are no blogs, articles, advisory-firm pages or news sites.

## 1. What is in it

| | |
|---|---|
| Documents | 73 |
| Files | 75 (the SIS Act and SIS Regulations are split into two volumes each, as published) |
| Chunks produced by the ingestion pipeline | 3,750 |
| Size on disk | 18.6 MB |
| Location | [`corpus/`](../corpus/), one folder per topic |
| Machine-readable list | [`corpus/manifest.json`](../corpus/manifest.json) (source URL, type, tier, use cases, chunk count per file) |

### By publisher

| Publisher | Documents |
|---|---|
| Australian Taxation Office | 58 |
| Federal Register of Legislation | 5 |
| Accounting Professional & Ethical Standards Board | 4 |
| Tax Practitioners Board | 3 |
| Australian Accounting Standards Board | 2 |
| Australian Securities and Investments Commission | 1 |

### By document type

| Type | Count | Examples |
|---|---|---|
| Legislation, regulation, legislative instrument | 5 | SIS Act 1993, SIS Regulations 1994, Tax Agent Services Act 2009, SG (Administration) Act 1992, TPB Code Determination 2024 |
| ATO rulings, determinations, LCR, PCGs | 13 | SMSFR 2008/2, 2009/1, 2009/2, 2010/1, 2012/1, TR 2010/1, LCR 2021/2, PCG 2016/5, TD 2022/11, PCG 2017/13, TR 2018/5, TR 2023/1, TR 2021/1 |
| Professional and accounting standards | 6 | APES 110, 220, 305, 320; AASB 1056, AASB 1060 |
| Regulator guidance | 37 | ATO SMSF pages, TPB guidance statements (incl. TPB(GS) 55/2026 on AI use), ASIC SMSF auditors |
| Rates and thresholds tables | 8 | Contributions caps, transfer balance cap, payments from super, SG rate, FBT, Div 7A benchmark rate, company and individual rates |
| Forms and instructions | 3 | SMSF annual return 2026 instructions (all sections), trustee declaration, auditor contravention report instructions |
| Program schedule | 1 | Registered agent lodgment program 2026-27 |

### By authority tier

| Tier | Count | Meaning |
|---|---|---|
| 1 | 18 | The law, and ATO public rulings/determinations |
| 2 | 53 | Regulator guidance, TPB, APESB |
| 3 | 2 | AASB standards |

## 2. Coverage of the use cases

A document can serve more than one use case, so the counts overlap.

﻿| Use case | Docs | Document IDs |
|---|---|---|
| UC-1 Compliance and investment restrictions | 10 | `ato-acr-instructions`, `ato-how-smsfs-are-taxed`, `ato-lcr-2021-2`, `ato-smsf-investment-requirements`, `ato-smsf-investment-restrictions`, `ato-smsfr-2008-2`, `ato-smsfr-2009-1`, `ato-smsfr-2010-1`, `leg-sis-act-1993`, `leg-sis-regulations-1994` |
| UC-2 Property in super and LRBA | 6 | `ato-pcg-2016-5`, `ato-smsf-lrba`, `ato-smsfr-2009-1`, `ato-smsfr-2009-2`, `ato-smsfr-2012-1`, `leg-sis-act-1993` |
| UC-3 Contribution caps and eligibility | 9 | `ato-concessional-cap`, `ato-contributions-caps-table`, `ato-division-293`, `ato-non-concessional-cap`, `ato-payday-super`, `ato-sb-cgt-concessions`, `ato-tr-2010-1`, `leg-sg-administration-act-1992`, `leg-sis-regulations-1994` |
| UC-4 Pension phase, release, TBC | 8 | `ato-conditions-of-release`, `ato-death-of-smsf-member`, `ato-payments-from-super`, `ato-smsf-income-stream-rules`, `ato-smsf-tbar-when-to-lodge`, `ato-transfer-balance-cap`, `leg-sis-act-1993`, `leg-sis-regulations-1994` |
| UC-5 Cross-border and fund residency | 5 | `ato-residency-tests`, `ato-smsf-australian-super-fund`, `ato-tr-2018-5`, `ato-tr-2023-1`, `leg-sis-act-1993` |
| UC-6 Division 296 | 3 | `ato-division-293`, `ato-division-296-smsf`, `ato-division-296-tax` |
| UC-7 Establishment and annual compliance | 13 | `aasb-1056`, `apesb-apes-110`, `apesb-apes-305`, `asic-smsf-auditors`, `ato-acr-instructions`, `ato-agent-lodgment-program`, `ato-sar-2026-instructions`, `ato-smsf-auditor-requirements`, `ato-smsf-trust-deed`, `ato-smsf-trustee-obligations`, `ato-trustee-declaration`, `leg-sis-act-1993`, `leg-sis-regulations-1994` |
| Division 7A | 4 | `ato-division-7a`, `ato-division-7a-benchmark-rate`, `ato-pcg-2017-13`, `ato-td-2022-11` |
| Fringe benefits tax | 2 | `ato-fbt-overview`, `ato-fbt-rates` |
| CGT and small business concessions | 3 | `ato-cgt-discount`, `ato-sb-cgt-concessions`, `ato-sb-cgt-eligibility` |
| Individual and company residency | 3 | `ato-residency-tests`, `ato-tr-2018-5`, `ato-tr-2023-1` |
| GST and BAS | 2 | `ato-bas`, `ato-registering-for-gst` |
| Employer super, payday super, STP | 5 | `ato-payday-super`, `ato-sg-rate`, `ato-stp`, `ato-work-out-if-you-pay-super`, `leg-sg-administration-act-1992` |
| Trusts | 2 | `ato-td-2022-11`, `ato-trusts-trustees-beneficiaries` |
| Company tax | 1 | `ato-company-tax-rates-2025-26` |
| Individual tax | 2 | `ato-individual-tax-rates`, `ato-tr-2021-1` |
| Small business concessions | 2 | `ato-instant-asset-write-off`, `ato-small-business-concessions` |
| Deceased estates and death benefits | 2 | `ato-death-of-smsf-member`, `ato-deceased-estates` |
| Financial reporting standards | 2 | `aasb-1056`, `aasb-1060` |
| Professional obligations and practice | 11 | `apesb-apes-110`, `apesb-apes-220`, `apesb-apes-305`, `apesb-apes-320`, `ato-agent-lodgment-program`, `ato-record-keeping-business`, `leg-tas-code-determination-2024`, `leg-tax-agent-services-act-2009`, `tpb-code-of-professional-conduct`, `tpb-gs-01-2010`, `tpb-gs-55-2026-ai` |

### Check against the benchmark set

For each answerable question in [`benchmarks/questions.md`](../benchmarks/questions.md), the fact the golden answer depends on was searched for in the extracted text of every corpus file. All 21 checks found at least one supporting file. Examples:

| Question | Fact needed | Found in |
|---|---|---|
| Q1, Q4, Q8 | General TBC $2.1m (2026-27), $2.0m (2025-26), $1.9m (earlier) | `ato-non-concessional-cap`, `ato-transfer-balance-cap`, `ato-contributions-caps-table` |
| Q5, Q9 | Division 296 LSBT $3m and VLSBT $10m, 15% and 10% rates | `ato-division-296-smsf`, `ato-division-296-tax` |
| Q6 | Payday super, 7 business days | `ato-payday-super`, SG (Administration) Act |
| Q7 | 2024-25 concessional cap $30,000 | `ato-contributions-caps-table` (year-by-year table) |
| Q11, Q24 | LRBA single acquirable asset, business real property, arm's length terms | SMSFR 2012/1, SMSFR 2009/1, PCG 2016/5, SIS Act |
| Q12 | In-house asset 5% limit | `ato-smsf-investment-restrictions`, SIS Act |
| Q19 | Division 293 $250,000 threshold | `ato-division-293` |
| Q21-Q23 | Fund residency: CM&C "temporarily outside Australia for up to 2 years", active member test | `ato-smsf-australian-super-fund`, TR 2018/5 |
| Q25 | Small business CGT cap, retirement exemption under-55 rule | `ato-sb-cgt-concessions` |

Q13, Q14 and Q15 (firm procedure) need Corpus B, which does not exist yet. Q16-Q18 and Q20 are refusal questions and need no source.

## 3. How the files are prepared

The ingestion pipeline in `app/services/document_service.py` reads PDF, DOCX and TXT only.

- **PDFs** (legislation, APES, AASB, TPB guidance statements) are saved unchanged from the publisher.
- **ATO and TPB web pages** are reduced to their main content and saved as `.txt`. Navigation, scripts and footers are removed; headings, lists and tables are kept.
- **ATO Legal Database rulings** are taken from the print view, which carries the full ruling text without site navigation. The cited URL is the normal document URL.
- Several ATO topics are spread across a hub page and child pages (for example LRBA, FBT, BAS, the SAR instructions). These are combined into one `.txt` per topic. Each section starts with `=== Section:` and its own `Source URL:`, so a retrieved chunk can still be traced to the exact page.

Every `.txt` starts with a provenance header:

```
Title: ...
Publisher: ...
Document type: ...
Authority tier: ...
Corpus: A (authority)
Source URL: ...
Retrieved: 2026-09-25
Topic: ...
---
```

The header matters because the current `documents` table has no `corpus`, `source_url`, `tier` or `effective_from` columns (see section 6). Until it does, the header in the first chunk and `manifest.json` are the only places this metadata lives.

## 4. Scripts

| Script | What it does |
|---|---|
| [`scripts/build_corpus.py`](../scripts/build_corpus.py) | Downloads everything in `corpus/sources.json` and writes `corpus/manifest.json`. Fails a source if the page redirects elsewhere or yields too little text. For legislation it reads the Federal Register downloads page, so it always gets the latest compilation. `--only <id>` rebuilds one entry. |
| [`scripts/validate_corpus.py`](../scripts/validate_corpus.py) | Runs every file through the pipeline's own `extract_text` and `chunk_text`, with no Supabase or embedding calls, and records the chunk count per file in the manifest. Last run: 75 files, 3,750 chunks, 0 failures. |
| [`scripts/upload_corpus.py`](../scripts/upload_corpus.py) | Logs in to the app when credentials are set, POSTs each file to `/upload` (which stores it in Supabase Storage, inserts the `documents` row and calls the n8n webhook), then polls `/documents/{id}/status` until each is `ready` or `failed`. Writes `corpus/upload_log.json` and skips files already `ready`, so it is safe to re-run. `--dry-run` lists what it would send. |

To add a source, add an entry to `corpus/sources.json`, then run `build_corpus.py --only <id>` and `validate_corpus.py`.

## 5. Loading into Supabase

1. Fill `.env` with the real `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_DB_URL`, `SUPABASE_BUCKET` and `HF_TOKEN` (plus `SESSION_SECRET` on `main`).
2. On `main` only, apply the section 6.1 fix first. Without it, no document can reach `ready`.
3. `docker compose up -d app n8n`
4. Open n8n at `http://localhost:5678`, choose **Import from File**, select [`n8n/Document Ingestion.json`](../n8n/Document%20Ingestion.json), and activate it. The webhook path is `process-document`.
5. Run `python scripts/upload_corpus.py`. On `main`, where uploads need a login, set `CORPUS_UPLOAD_EMAIL` and `CORPUS_UPLOAD_PASSWORD` first (create the user with `python scripts/create_app_user.py` if needed).
6. Check that every entry in `corpus/upload_log.json` is `ready`. In Supabase, `select document_id, count(*) from document_chunks group by 1` should roughly match the chunk counts in the manifest.

Start with `--only ato-division-296-smsf ato-smsf-lrba` to test the full path on two small files before sending all 75.

## 6. Blockers and risks found

### 6.1 The n8n callback is rejected by the auth middleware (blocker once merged)

This branch is based on 9eeeb11, before session auth was added, so the problem does not occur here. It will appear as soon as this work is merged into `main`.

On `main`, `enforce_authenticated_access` in `app/main.py` does not list `/api/n8n/` as public. The n8n HTTP Request node calls `POST /api/n8n/process-document/{id}` with no session cookie, so it gets a 401. This was confirmed with FastAPI's TestClient on `main` at 63da927:

```
POST /api/n8n/process-document/1 without session -> 401 {"detail":"Authentication required."}
GET /api/n8n-test without session -> 401 {"detail":"Authentication required."}
```

So every upload stays `pending`. The fix is small, but it is an auth decision, so it has not been made here. Either allow `/api/n8n/` through the middleware and have n8n send a shared-secret header that the route checks, or have n8n call the processing step some other way. Do not make the route public without a secret, because it would let anyone trigger processing.

### 6.2 Embedding volume

Each chunk is one Hugging Face Inference API call (`app/rag/embedder.py`). 3,750 chunks means 3,750 calls, sent one after another inside a single HTTP request from n8n. The SIS Act alone is 797 chunks. Check the HF account's quota before a full load. If the n8n HTTP node times out on the large PDFs, raise its timeout or load the legislation last.

To keep the volume manageable, the GST Act 1999 and the FBTAA 1986 (about 1,200 pages together) were left out. ATO guidance covers both topics. Add them to `sources.json` (title IDs `C2004A00446` and `C2004A03280`) if full-text law on those topics is needed.

### 6.3 Metadata the schema cannot hold yet

`REQUIREMENTS.md` UP-2 and section 5.1 require `corpus`, `effective_from`, `effective_to`, `source_url` and `superseded_by` per document. The current `documents` table has none of these. `manifest.json` has them ready (all these documents are corpus A, and the retrieval date is recorded), so they can be backfilled once the columns exist.

### 6.4 Things a reviewer should know

- The SMSF annual return instructions are the **2026** version. Each year's instructions are a separate document. When the 2027 version comes out, add it as a new document rather than replacing this one.
- APES 110 is the June 2023 compilation. Any amendments issued after it are not included, so check the APESB site for a newer compilation before relying on it.
- AASB 1056 is the December 2023 compilation. No newer compilation turned up in a search, but this was not confirmed on the AASB site.
- The ATO page for Division 293 is filed under UC-3 and UC-6 on purpose. It is there so the assistant can tell Division 293 and Division 296 apart (benchmark Q19).
- TR 2021/1 (employee transport expenses) is included as an example of individual deductions. It is not SMSF material.

## 7. Full source list

| ID | Title | Type | Tier | File(s) | Chunks | Source |
|---|---|---|---|---|---|---|
| `aasb-1056` | AASB 1056 Superannuation Entities (compiled December 2023) | accounting standard | 3 | `accounting-standards/aasb-1056.pdf` | 131 | [link](https://www.aasb.gov.au/admin/file/content105/c9/AASB1056_12-23.pdf) |
| `aasb-1060` | AASB 1060 General Purpose Financial Statements - Simplified Disclosures (compiled August 2025) | accounting standard | 3 | `accounting-standards/aasb-1060.pdf` | 201 | [link](https://standards.aasb.gov.au/sites/default/files/2026-03/AASB1060_03-20_COMPaug25_01-26.pdf) |
| `ato-cgt-discount` | CGT discount | guidance | 2 | `general-tax/cgt/ato-cgt-discount.txt` | 3 | [link](https://www.ato.gov.au/individuals-and-families/investments-and-assets/capital-gains-tax/cgt-discount) |
| `ato-sb-cgt-concessions` | Small business CGT concessions | guidance | 2 | `general-tax/cgt/ato-sb-cgt-concessions.txt` | 24 | [link](https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/incentives-and-concessions/small-business-cgt-concessions) |
| `ato-sb-cgt-eligibility` | CGT concessions eligibility overview | guidance | 2 | `general-tax/cgt/ato-sb-cgt-eligibility.txt` | 5 | [link](https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/incentives-and-concessions/small-business-cgt-concessions/small-business-cgt-concessions-eligibility-conditions/cgt-concessions-eligibility-overview) |
| `ato-division-7a` | Private company benefits - Division 7A dividends | guidance | 2 | `general-tax/division-7a/ato-division-7a.txt` | 10 | [link](https://www.ato.gov.au/businesses-and-organisations/corporate-tax-measures-and-assurance/private-company-benefits-division-7a-dividends) |
| `ato-division-7a-benchmark-rate` | Division 7A - benchmark interest rate | rates and thresholds | 2 | `general-tax/division-7a/ato-division-7a-benchmark-rate.txt` | 3 | [link](https://www.ato.gov.au/tax-rates-and-codes/division-7a-benchmark-interest-rate) |
| `ato-pcg-2017-13` | PCG 2017/13 - Division 7A: PS LA 2010/4 sub-trust arrangements maturing in or after the 2016-17 income year | practical compliance guideline | 1 | `general-tax/division-7a/ato-pcg-2017-13.txt` | 12 | [link](https://www.ato.gov.au/law/view/document?DocID=COG%2FPCG201713%2FNAT%2FATO%2F00001) |
| `ato-td-2022-11` | TD 2022/11 - Division 7A: when will an unpaid present entitlement or amount held on sub-trust become the provision of financial accommodation? | determination | 1 | `general-tax/division-7a/ato-td-2022-11.txt` | 38 | [link](https://www.ato.gov.au/law/view/document?DocID=TXD%2FTD202211%2FNAT%2FATO%2F00001) |
| `ato-company-tax-rates-2025-26` | Company tax rates 2025-26 | rates and thresholds | 2 | `general-tax/entities/ato-company-tax-rates-2025-26.txt` | 3 | [link](https://www.ato.gov.au/tax-rates-and-codes/company-tax-rates/tax-rates-2025-26) |
| `ato-individual-tax-rates` | Tax rates - Australian residents | rates and thresholds | 2 | `general-tax/entities/ato-individual-tax-rates.txt` | 9 | [link](https://www.ato.gov.au/tax-rates-and-codes/tax-rates-australian-residents) |
| `ato-instant-asset-write-off` | Instant asset write-off for eligible businesses | guidance | 2 | `general-tax/entities/ato-instant-asset-write-off.txt` | 7 | [link](https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/depreciation-and-capital-expenses-and-allowances/simpler-depreciation-for-small-business/instant-asset-write-off) |
| `ato-record-keeping-business` | Record keeping for business | guidance | 2 | `general-tax/entities/ato-record-keeping-business.txt` | 6 | [link](https://www.ato.gov.au/businesses-and-organisations/preparing-lodging-and-paying/record-keeping-for-business) |
| `ato-small-business-concessions` | Concessions for eligible businesses | guidance | 2 | `general-tax/entities/ato-small-business-concessions.txt` | 2 | [link](https://www.ato.gov.au/businesses-and-organisations/income-deductions-and-concessions/incentives-and-concessions/concessions) |
| `ato-tr-2021-1` | TR 2021/1 - Income tax: when are deductions allowed for employees' transport expenses? | ruling | 1 | `general-tax/entities/ato-tr-2021-1.txt` | 38 | [link](https://www.ato.gov.au/law/view/document?DocID=TXR%2FTR20211%2FNAT%2FATO%2F00001) |
| `ato-trusts-trustees-beneficiaries` | Trusts, trustees and beneficiaries | guidance | 2 | `general-tax/entities/ato-trusts-trustees-beneficiaries.txt` | 8 | [link](https://www.ato.gov.au/businesses-and-organisations/trusts/trusts-trustees-and-beneficiaries) |
| `ato-deceased-estates` | Deceased estates | guidance | 2 | `general-tax/estates/ato-deceased-estates.txt` | 7 | [link](https://www.ato.gov.au/individuals-and-families/deceased-estates) |
| `ato-fbt-overview` | Fringe benefits tax | guidance | 2 | `general-tax/fbt/ato-fbt-overview.txt` | 13 | [link](https://www.ato.gov.au/businesses-and-organisations/hiring-and-paying-your-workers/fringe-benefits-tax) |
| `ato-fbt-rates` | Fringe benefits tax - rates and thresholds | rates and thresholds | 2 | `general-tax/fbt/ato-fbt-rates.txt` | 6 | [link](https://www.ato.gov.au/tax-rates-and-codes/fringe-benefits-tax-rates-and-thresholds) |
| `ato-bas` | Business activity statements (BAS) | guidance | 2 | `general-tax/gst-bas/ato-bas.txt` | 15 | [link](https://www.ato.gov.au/businesses-and-organisations/preparing-lodging-and-paying/business-activity-statements-bas) |
| `ato-registering-for-gst` | Registering for GST | guidance | 2 | `general-tax/gst-bas/ato-registering-for-gst.txt` | 5 | [link](https://www.ato.gov.au/businesses-and-organisations/gst-excise-and-indirect-taxes/gst/registering-for-gst) |
| `ato-payday-super` | Payday Super for employers | guidance | 2 | `general-tax/payroll-super/ato-payday-super.txt` | 16 | [link](https://www.ato.gov.au/businesses-and-organisations/super-for-employers/about-payday-super) |
| `ato-sg-rate` | Key super rates and thresholds - Super guarantee | rates and thresholds | 2 | `general-tax/payroll-super/ato-sg-rate.txt` | 2 | [link](https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/super-guarantee) |
| `ato-stp` | Single Touch Payroll | guidance | 2 | `general-tax/payroll-super/ato-stp.txt` | 11 | [link](https://www.ato.gov.au/businesses-and-organisations/hiring-and-paying-your-workers/single-touch-payroll) |
| `ato-work-out-if-you-pay-super` | Work out if you have to pay super | guidance | 2 | `general-tax/payroll-super/ato-work-out-if-you-pay-super.txt` | 5 | [link](https://www.ato.gov.au/businesses-and-organisations/super-for-employers/work-out-if-you-have-to-pay-super) |
| `ato-residency-tests` | Residency tests | guidance | 2 | `general-tax/residency/ato-residency-tests.txt` | 19 | [link](https://www.ato.gov.au/individuals-and-families/coming-to-australia-or-going-overseas/residency-tests) |
| `ato-tr-2018-5` | TR 2018/5 - Income tax: central management and control test of residency | ruling | 1 | `general-tax/residency/ato-tr-2018-5.txt` | 18 | [link](https://www.ato.gov.au/law/view/document?DocID=TXR%2FTR20185%2FNAT%2FATO%2F00001) |
| `ato-tr-2023-1` | TR 2023/1 - Income tax: residency tests for individuals | ruling | 1 | `general-tax/residency/ato-tr-2023-1.txt` | 50 | [link](https://www.ato.gov.au/law/view/document?DocID=TXR%2FTR20231%2FNAT%2FATO%2F00001) |
| `leg-sg-administration-act-1992` | Superannuation Guarantee (Administration) Act 1992 (latest compilation) | legislation | 1 | `legislation/leg-sg-administration-act-1992.pdf` | 128 | [link](https://www.legislation.gov.au/C2004A04402/2026-07-01/2026-07-01/text/original/pdf) |
| `leg-sis-act-1993` | Superannuation Industry (Supervision) Act 1993 (latest compilation) | legislation | 1 | `legislation/leg-sis-act-1993_vol1.pdf`<br>`legislation/leg-sis-act-1993_vol2.pdf` | 797 | [link](https://www.legislation.gov.au/C2004A04633/2026-08-10/2026-08-10/text/original/pdf/1) |
| `leg-sis-regulations-1994` | Superannuation Industry (Supervision) Regulations 1994 (latest compilation) | regulation | 1 | `legislation/leg-sis-regulations-1994_vol1.pdf`<br>`legislation/leg-sis-regulations-1994_vol2.pdf` | 615 | [link](https://www.legislation.gov.au/F1996B00580/2026-07-01/2026-07-01/text/original/pdf/1) |
| `leg-tas-code-determination-2024` | Tax Agent Services (Code of Professional Conduct) Determination 2024 | legislative instrument | 1 | `legislation/leg-tas-code-determination-2024.pdf` | 20 | [link](https://www.legislation.gov.au/F2024L00849/2025-02-25/2025-02-25/text/original/pdf) |
| `leg-tax-agent-services-act-2009` | Tax Agent Services Act 2009 (latest compilation) | legislation | 1 | `legislation/leg-tax-agent-services-act-2009.pdf` | 105 | [link](https://www.legislation.gov.au/C2009A00013/2025-02-21/2025-02-21/text/original/pdf) |
| `apesb-apes-110` | APES 110 Code of Ethics for Professional Accountants (including Independence Standards) | professional standard | 2 | `professional-standards/apesb-apes-110.pdf` | 369 | [link](https://apesb.org.au/wp-content/uploads/2023/12/Compiled_APES_110_Jun_23.pdf) |
| `apesb-apes-220` | APES 220 Taxation Services | professional standard | 2 | `professional-standards/apesb-apes-220.pdf` | 19 | [link](https://apesb.org.au/wp-content/uploads/2025/01/APES_220_Jan_2025.pdf) |
| `apesb-apes-305` | APES 305 Terms of Engagement | professional standard | 2 | `professional-standards/apesb-apes-305.pdf` | 12 | [link](https://apesb.org.au/wp-content/uploads/2024/09/APES_305_Sept_2024.pdf) |
| `apesb-apes-320` | APES 320 Quality Management for Firms that provide Non-Assurance Services | professional standard | 2 | `professional-standards/apesb-apes-320.pdf` | 45 | [link](https://apesb.org.au/wp-content/uploads/2022/02/APES_320_reissued_Feb_2022.pdf) |
| `ato-agent-lodgment-program` | Registered agent lodgment program | program schedule | 2 | `professional-standards/ato-agent-lodgment-program.txt` | 5 | [link](https://www.ato.gov.au/tax-and-super-professionals/for-tax-professionals/prepare-and-lodge/registered-agent-lodgment-program) |
| `tpb-code-of-professional-conduct` | Code of Professional Conduct | guidance | 2 | `professional-standards/tpb-code-of-professional-conduct.txt` | 4 | [link](https://www.tpb.gov.au/code-professional-conduct) |
| `tpb-gs-01-2010` | TPB(GS) 01/2010 Code of Professional Conduct | guidance | 2 | `professional-standards/tpb-gs-01-2010.pdf` | 128 | [link](https://www.tpb.gov.au/sites/default/files/2026-04/TPB(GS)%2001_2010_Code%20of%20Professional%20Conduct_2.pdf) |
| `tpb-gs-55-2026-ai` | TPB(GS) 55/2026 The use of Artificial Intelligence and the Code of Professional Conduct | guidance | 2 | `professional-standards/tpb-gs-55-2026-ai.pdf` | 13 | [link](https://www.tpb.gov.au/sites/default/files/2026-07/TPB(GS)%2055_2026_%20The%20use%20of%20Artificial%20Intelligence%20and%20the%20Code%20of%20Professional%20Conduct_0.pdf) |
| `ato-how-smsfs-are-taxed` | How SMSFs are taxed | guidance | 2 | `smsf-compliance/ato-how-smsfs-are-taxed.txt` | 6 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-administration-and-reporting/how-smsfs-are-taxed) |
| `ato-lcr-2021-2` | LCR 2021/2 - Non-arm's length income: expenditure incurred under a non-arm's length arrangement | law companion ruling | 1 | `smsf-compliance/ato-lcr-2021-2.txt` | 36 | [link](https://www.ato.gov.au/law/view/document?DocID=COG%2FLCR20212%2FNAT%2FATO%2F00001) |
| `ato-smsf-investment-requirements` | SMSF investment requirements | guidance | 2 | `smsf-compliance/ato-smsf-investment-requirements.txt` | 16 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-investing/smsf-investment-requirements) |
| `ato-smsf-investment-restrictions` | What are the SMSF investment restrictions? | guidance | 2 | `smsf-compliance/ato-smsf-investment-restrictions.txt` | 7 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-investing/restrictions-on-smsf-investments/what-are-the-smsf-investment-restrictions) |
| `ato-smsfr-2008-2` | SMSFR 2008/2 - Sole purpose test and benefits other than retirement, employment termination or death benefits | ruling | 1 | `smsf-compliance/ato-smsfr-2008-2.txt` | 43 | [link](https://www.ato.gov.au/law/view/document?DocID=SFR%2FSMSFR20082%2FNAT%2FATO%2F00001) |
| `ato-smsfr-2010-1` | SMSFR 2010/1 - Acquisition of an asset by an SMSF from a related party (s66 SIS Act) | ruling | 1 | `smsf-compliance/ato-smsfr-2010-1.txt` | 53 | [link](https://www.ato.gov.au/law/view/document?DocID=SFR%2FSMSFR20101%2FNAT%2FATO%2F00001) |
| `ato-concessional-cap` | Concessional contributions cap | guidance | 2 | `smsf-contributions/ato-concessional-cap.txt` | 8 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/concessional-contributions-cap) |
| `ato-contributions-caps-table` | Key super rates and thresholds - Contributions caps | rates and thresholds | 2 | `smsf-contributions/ato-contributions-caps-table.txt` | 9 | [link](https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/contributions-caps) |
| `ato-division-293` | Division 293 tax on concessional contributions by high-income earners | guidance | 2 | `smsf-contributions/ato-division-293.txt` | 11 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/division-293-tax-on-concessional-contributions-by-high-income-earners) |
| `ato-non-concessional-cap` | Non-concessional contributions cap | guidance | 2 | `smsf-contributions/ato-non-concessional-cap.txt` | 11 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/non-concessional-contributions-cap) |
| `ato-tr-2010-1` | TR 2010/1 - Income tax: superannuation contributions | ruling | 1 | `smsf-contributions/ato-tr-2010-1.txt` | 81 | [link](https://www.ato.gov.au/law/view/document?DocID=TXR%2FTR20101%2FNAT%2FATO%2F00001) |
| `ato-division-296-smsf` | About Division 296 tax for SMSFs | guidance | 2 | `smsf-div296/ato-division-296-smsf.txt` | 4 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-administration-and-reporting/about-division-296-tax-for-smsfs) |
| `ato-division-296-tax` | Division 296 tax | guidance | 2 | `smsf-div296/ato-division-296-tax.txt` | 28 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/super/growing-and-keeping-track-of-your-super/caps-limits-and-tax-on-super-contributions/division-296-tax) |
| `asic-smsf-auditors` | Self-managed superannuation fund (SMSF) auditors | guidance | 2 | `smsf-establishment-compliance/asic-smsf-auditors.txt` | 2 | [link](https://www.asic.gov.au/for-finance-professionals/self-managed-superannuation-fund-smsf-auditors) |
| `ato-acr-instructions` | Auditor/actuary contravention report instructions | form and instructions | 2 | `smsf-establishment-compliance/ato-acr-instructions.txt` | 30 | [link](https://www.ato.gov.au/forms-and-instructions/auditor-actuary-contravention-report-instructions) |
| `ato-sar-2026-instructions` | Instructions to complete your SMSF annual return 2026 | form and instructions | 2 | `smsf-establishment-compliance/ato-sar-2026-instructions.txt` | 179 | [link](https://www.ato.gov.au/forms-and-instructions/self-managed-superannuation-fund-annual-return-2026-instructions/instructions-to-complete-your-smsf-annual-return-2026) |
| `ato-smsf-auditor-requirements` | SMSF auditor professional requirements | guidance | 2 | `smsf-establishment-compliance/ato-smsf-auditor-requirements.txt` | 2 | [link](https://www.ato.gov.au/tax-and-super-professionals/for-superannuation-professionals/smsf-auditors/smsf-auditor-professional-requirements) |
| `ato-smsf-trust-deed` | Create the SMSF trust deed | guidance | 2 | `smsf-establishment-compliance/ato-smsf-trust-deed.txt` | 2 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/setting-up-an-smsf/create-the-smsf-trust-deed) |
| `ato-smsf-trustee-obligations` | Your obligations as an SMSF trustee | guidance | 2 | `smsf-establishment-compliance/ato-smsf-trustee-obligations.txt` | 5 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/before-you-start-an-smsf/your-obligations-as-an-smsf-trustee) |
| `ato-trustee-declaration` | Trustee declaration | form and instructions | 2 | `smsf-establishment-compliance/ato-trustee-declaration.txt` | 2 | [link](https://www.ato.gov.au/forms-and-instructions/trustee-declaration) |
| `ato-conditions-of-release` | Conditions of release | guidance | 2 | `smsf-pensions-tbc/ato-conditions-of-release.txt` | 5 | [link](https://www.ato.gov.au/tax-and-super-professionals/for-superannuation-professionals/apra-regulated-funds/paying-benefits/releasing-benefits/conditions-of-release) |
| `ato-death-of-smsf-member` | Death of an SMSF member | guidance | 2 | `smsf-pensions-tbc/ato-death-of-smsf-member.txt` | 21 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/paying-smsf-benefits/death-of-an-smsf-member) |
| `ato-payments-from-super` | Key super rates and thresholds - Payments from super | rates and thresholds | 2 | `smsf-pensions-tbc/ato-payments-from-super.txt` | 7 | [link](https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/payments-from-super) |
| `ato-smsf-income-stream-rules` | Income stream (pension) rules and payments | guidance | 2 | `smsf-pensions-tbc/ato-smsf-income-stream-rules.txt` | 11 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/paying-smsf-benefits/income-stream-pension-rules-and-payments) |
| `ato-smsf-tbar-when-to-lodge` | When to lodge a transfer balance account report for SMSFs | guidance | 2 | `smsf-pensions-tbc/ato-smsf-tbar-when-to-lodge.txt` | 7 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-administration-and-reporting/when-to-lodge-a-transfer-balance-account-report-for-smsfs) |
| `ato-transfer-balance-cap` | Key super rates and thresholds - Transfer balance cap | rates and thresholds | 2 | `smsf-pensions-tbc/ato-transfer-balance-cap.txt` | 19 | [link](https://www.ato.gov.au/tax-rates-and-codes/key-superannuation-rates-and-thresholds/transfer-balance-cap) |
| `ato-pcg-2016-5` | PCG 2016/5 - Arm's length terms for limited recourse borrowing arrangements established by SMSFs | practical compliance guideline | 1 | `smsf-property-lrba/ato-pcg-2016-5.txt` | 16 | [link](https://www.ato.gov.au/law/view/document?DocID=COG%2FPCG20165%2FNAT%2FATO%2F00001) |
| `ato-smsf-lrba` | Limited recourse borrowing arrangements | guidance | 2 | `smsf-property-lrba/ato-smsf-lrba.txt` | 26 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/smsf-investing/restrictions-on-smsf-investments/smsf-borrowing-restrictions/limited-recourse-borrowing-arrangements) |
| `ato-smsfr-2009-1` | SMSFR 2009/1 - Business real property for the purposes of the SIS Act | ruling | 1 | `smsf-property-lrba/ato-smsfr-2009-1.txt` | 94 | [link](https://www.ato.gov.au/law/view/document?DocID=SFR%2FSMSFR20091%2FNAT%2FATO%2F00001) |
| `ato-smsfr-2009-2` | SMSFR 2009/2 - Meaning of 'borrow money' or 'maintain an existing borrowing of money' | ruling | 1 | `smsf-property-lrba/ato-smsfr-2009-2.txt` | 33 | [link](https://www.ato.gov.au/law/view/document?DocID=SFR%2FSMSFR20092%2FNAT%2FATO%2F00001) |
| `ato-smsfr-2012-1` | SMSFR 2012/1 - Limited recourse borrowing arrangements: application of key concepts | ruling | 1 | `smsf-property-lrba/ato-smsfr-2012-1.txt` | 47 | [link](https://www.ato.gov.au/law/view/document?DocID=SFR%2FSMSFR20121%2FNAT%2FATO%2F00001) |
| `ato-smsf-australian-super-fund` | Check your SMSF is an Australian super fund | guidance | 2 | `smsf-residency/ato-smsf-australian-super-fund.txt` | 2 | [link](https://www.ato.gov.au/individuals-and-families/super-for-individuals-and-families/self-managed-super-funds-smsf/setting-up-an-smsf/check-your-smsf-is-an-australian-super-fund) |

## Handoff Notes

Done: Collected 73 official documents (75 files, 3,750 chunks) from the ATO, the Federal Register of Legislation, APESB, TPB, AASB and ASIC. They cover all seven SMSF use cases plus wider accounting topics, and every file was checked against the pipeline's own extract and chunk code. I also added build, validate and bulk-upload scripts for Supabase via the n8n webhook.

Deliverable: `docs/DOCUMENT-CORPUS.md`, `corpus/` (documents, `sources.json`, `manifest.json`) and `scripts/build_corpus.py`, `validate_corpus.py`, `upload_corpus.py` on branch `docs/sample-accounting-documentation`.

Note for next role: The documents have not been uploaded to Supabase yet. On `main`, the n8n callback gets a 401 from the auth middleware (section 6.1), so that needs a decision and fix first, along with a `.env` holding real Supabase and HF credentials. After that, run `scripts/upload_corpus.py` and confirm every row is `ready`. Please also review the section 6.2 embedding volume before the full load. The Master Document (Team 83) needs updating with this card's handoff.
