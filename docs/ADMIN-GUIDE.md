# Alfa Focus Knowledge Assistant: admin guide

For the people who look after the document library and check the assistant's quality: Alfa Focus administrators and Team 83 reviewers.
Written 2026-10-22 by Ronith Mugundakumar (BA) from the application on `main` (commit `c059f82`). Everyday use of the chat is in the [user guide](USER-GUIDE.md).

This guide covers what you do in the web pages and the one command that creates accounts. Installing and starting the system (Docker Compose, environment variables, the n8n workflow) is in the [README](../README.md) and in section 9 of the Handover Document.

**Draft for screenshots.** Each `[Screenshot AG-n]` marker shows where a screenshot goes. The list at the end says what to capture and what to keep out of the frame.

The assistant is a prototype. Some features a document library normally has are not built. Each section says so where it matters, and section 10 lists them together.

## 1. Who can do what

Every account has one of three roles.

| Action | `staff` | `admin` | `team` |
|---|---|---|---|
| Sign in and use the chat | Yes | Yes | Yes |
| See the Documents page, upload, retry | Yes | Yes | Yes |
| Delete a document | Yes | Yes | **No** |
| See and run **LLM Testing** | No | No | Yes |

The `team` role is for the project team and reviewers. A `team` user who tries to delete a document sees "You do not have permission to delete documents.". Any signed-in user can upload, and the record keeps the uploader as the word "user", not a name.

## 2. Create and disable accounts

There is no page for accounts and no default account. An administrator creates each one from the command line on the machine that runs the application.

**To create an account**

1. Open a terminal in the project folder and activate the Python environment.
2. Run the command with the person's email, a password you generate, and a role:

   ```bash
   python -m scripts.create_app_user --email name@alfafocus.com.au --password '<password>' --role staff
   ```

3. Check the line it prints: `created: id=… email=… role=… active=True`.
4. Give the person their password by a private channel and ask them to keep it safe.

Roles are `staff`, `admin` and `team`. The command needs the database settings in `.env`. The password appears in your shell history, so clear the history afterwards on a shared machine.

**To change a password or role**

1. Run the same command with the same email. It prints `updated:` instead of `created:`.

**To disable an account**

1. Run the same command with the email, the password, the current role, and `--inactive`.
2. The person then sees "This account is not active. Contact your Alfa Focus administrator." and cannot sign in. A person already signed in loses access the next time the application checks their session.

The command sets the password and the role every time it runs. Use the person's current role and the password you want them to have, or the account's role resets to `staff`.

## 3. The Documents page

Open **Documents** in the left menu. The page has an upload area at the top and a table of every uploaded document below it.

`[Screenshot AG-01: the Documents page with the upload area and the table, annotated with Browse Files, the search box, the STATUS column and the delete and retry icons]`

| Table column | Shows |
|---|---|
| FILE NAME | The file name, with the label underneath. The label is the file name. |
| TYPE | PDF, DOCX or TXT |
| UPLOAD DATE | The day it was uploaded |
| STATUS | `pending`, `processing`, `ready` or `failed` |
| ACTIONS | A trash icon (delete) and a circular arrow (retry) |

The newest uploads are at the top. The table does not refresh by itself. After an upload, reload the page to see the status move on.

## 4. Upload a document

The assistant can only answer from documents with the status `ready`.

**To upload**

1. Prepare a PDF, DOCX or TXT file with a clear name (see section 5). A scanned PDF with no text layer cannot be read and will fail.
2. On the Documents page, select **Browse Files**, choose the file and select Open. Or drag the file onto the upload area. Drop one file at a time; if you drop several, only the first is used.
3. Wait for the button to change back from "Uploading…". The document appears in the table with the status `pending`.
4. Wait, then reload the page. The status changes to `processing` and then to `ready`.

`[Screenshot AG-02: the table showing a document with the status pending, and another with ready]`

What happens behind the page: the file is stored, a record is created, and the n8n workflow asks the application to read the text, split it into passages, turn each passage into a numerical fingerprint (an embedding) and save them. The document is searchable only after the last step.

How long it takes depends on the size. A short ATO page has only a few passages and is quick. A long piece of legislation has hundreds of passages and can take many minutes, because each passage is processed one at a time. The embedding service has a free quota. If the quota runs out, uploads fail until it resets.

If the upload itself fails, a message box starts with "Upload error:" and gives the reason. Nothing is added to the table.

The app does not set a file size limit. The storage plan behind it may have its own.

## 5. Classify a document

**The application has no classification step.** An upload takes only the file. It does not ask whether the document is legislation, ATO guidance or an Alfa Focus procedure, and it does not record the date from which the document applies. Both fields were designed (requirement UP-2) and were not built. The assistant therefore cannot filter by document type or by income year, and treats every document in the same way.

Until the fields exist, put the information in the file name and keep a register:

1. **Name the file with its publisher, topic and year.** The file name is the label users see when they hover over a citation. For example `ato-division-296-tax.txt`, `leg-sis-act-1993.pdf`, `ato-contributions-caps-2026-27.txt`. The 73 documents already loaded follow this pattern.
2. **Give year-specific documents a different name for each year.** Upload the 2027 instructions as a new document. Do not replace the 2026 one, because questions about past income years still need it.
3. **Keep a register outside the application.** For each document record the file name, the publisher, whether it is law, regulator guidance or firm procedure, the date it applies from, the source address, the date you retrieved it and who uploaded it. The register for the loaded corpus is `corpus/manifest.json`, and `docs/DOCUMENT-CORPUS.md` section 7 lists each source address.
4. **Do not upload firm procedures yet.** The assistant is built to keep law and firm practice apart, but nothing marks which is which, so a firm document would be treated as authority.
5. **Do not upload anything with client names, TFNs or member numbers.**

To replace a corrected version of the same document, upload the new file, wait until it is `ready`, then delete the old one (section 7). Both are searched while both exist, so do not leave them side by side.

## 6. Understand the statuses and fix a failure

| Status | Meaning | What to do |
|---|---|---|
| `pending` | Uploaded and waiting to be processed | Wait a minute and reload. If it stays `pending`, n8n is not running, the ingestion workflow is not active, or the shared secret does not match. See the table below. |
| `processing` | Being read, split and embedded | Wait. Large files take many minutes. If it is still `processing` long after the file should have finished, or the server restarted meanwhile, it is stuck: retry it. |
| `ready` | Searchable | Nothing. A ready document cannot be retried. |
| `failed` | Processing stopped with an error. The document is not searchable | Find the reason (below), fix the cause, then select retry. |

**To retry a document**

1. Select the circular arrow in the ACTIONS column.
2. Reload the page. The status returns to `pending` and then moves on.

The retry arrow is available for every document that is not `ready`, including one that is still `processing`. Do not retry a document that is working normally.

**To find out why a document failed**

The page does not show the reason. It is stored with the document.

1. Open the Supabase project and the **Table Editor**.
2. Open the `documents` table and find the row (the `id` column matches the order of upload).
3. Read the `failure_reason` column.

| Reason you may see | Cause and fix |
|---|---|
| No readable text could be extracted from the document | The file is a scan or an image. Use a text version, or run it through OCR first. |
| Unsupported file type: .xyz | Only PDF, DOCX and TXT are read. Convert the file. A file dropped onto the page is not checked until it fails here. |
| Downloaded file is empty | The stored file is missing or empty. Delete the document and upload it again. |
| Document produced no usable chunks | The text was too short or unusual to split. Check the file. |
| An error from the embedding service, such as a quota or credit message | The Hugging Face free quota is used up. Wait for it to reset or add credit, then retry. |
| Unexpected embedding dimension | The embedding model was changed. Ask the developers. |

If a document stays `pending`:

| Check | How |
|---|---|
| n8n is running | Open the n8n address for your installation (`http://localhost:5678` when run with Docker Compose). |
| The workflow is active | In n8n, open **Document Ingestion** and check it is switched on. |
| The secret matches | The `X-N8N-Secret` credential in n8n must equal `N8N_SHARED_SECRET` in the application's `.env`. |
| What n8n did | In n8n, open **Executions** and read the latest failure. |

## 7. Find and delete documents

**Find a document**

1. Type part of a file name in the **Search documents** box above the table.
2. The table narrows as you type. The search ignores capital letters and matches the file name and the label.

That is the only filter. You cannot yet filter by status, type or upload date, and the table has no sorting or paging. Clear the box to see everything.

`[Screenshot AG-03: the search box with "division" typed and the table narrowed to matching documents]`

**Delete a document**

Only `admin` and `staff` accounts can delete.

1. Find the document and select the trash icon in the ACTIONS column.
2. Read the box that opens. It says "Delete document?" and names the file.
3. Select **Confirm delete**. Select **Cancel** to keep the document.
4. A message says "Document deleted" and the row leaves the table.

Deleting removes the stored file, the document record and all of its searchable passages. The assistant stops using it at once. It cannot be undone, so keep the original file elsewhere. Chats that already quoted the document keep their text.

`[Screenshot AG-04: the Delete document dialog naming a demo file, with the Cancel and Confirm delete buttons]`

If the box shows a red message, the delete did not happen. "You do not have permission to delete documents." means your role is `team`.

## 8. Run the evaluation page and read the results

The **LLM Testing** page (menu item, or the card on the Home page) runs the 50 benchmark questions against a model and scores the answers. Only `team` accounts see it. Use it to check quality after a change to the documents, the prompt, the retrieval or the model.

**To run the benchmark**

1. Sign in with a `team` account and select **LLM Testing**.
2. Under **Benchmark settings**, check the settings. The defaults suit most runs.

   | Setting | Choices | Default |
   |---|---|---|
   | Test Set | Core MVP Benchmark, 50 cases | The same |
   | Model | Gemini 3.8 Flash, Groq GPT-OSS 120B, OpenRouter Free, Free Fallback | Gemini 3.8 Flash |
   | Retrieval | Dense, Hybrid, Keyword | Hybrid. Use Dense or Keyword only to find where retrieval fails. |
   | Top K | 1 to 20 | 6 (the number of passages given to the model) |
   | Use LLM Judge | Tick to add correctness and faithfulness scores, then pick a judge model | Off |

3. Select **Run Benchmark**.
4. Watch the progress panel. It shows "N / 50 cases completed", and how many have passed, failed, and remain, the time elapsed, and the current case.
5. To stop early, select **Stop Run**. The status becomes RUN INTERRUPTED and the cases finished so far are kept for this server session.

`[Screenshot AG-05: the Benchmark settings card with the defaults, annotated with Test Set, Model, Retrieval, Top K and Run Benchmark]`

Things to know before you start:

- Only one run can be active at a time. A second attempt shows "Another evaluation run is already active.".
- The 50 questions run one after another. On the free models, expect half an hour or more, longer with the judge on.
- You can leave the page and come back. It picks up the active run.
- A model that is rate-limited can fail a question after several retries. That question is counted as a provider failure, not a wrong answer.

**To read the results**

When the run ends, a **Summary metrics** card appears. The strip at the top gives the number of cases, passed, failed and provider failures. The badge to its right says **Release gates met** or **Release gates not met**. On a partial run it says "Partial run · gates informational".

`[Screenshot AG-06: the Summary metrics card after a finished run, annotated with the badge and the metric cards]`

Each metric card shows a value, PASS, FAIL or INFO, and its target:

| Metric | What it measures | Target |
|---|---|---|
| Recall @ K | Whether the right source document was among the passages retrieved | 95% or more |
| MRR | How high the right source ranked (1 is first) | Report only |
| Citation valid | Whether every citation number points at a passage the model was given | 100% |
| Refusal recall | Of the questions that should be declined, how many were | 95% or more |
| Refusal precision | Of the declines, how many were right (low means it refuses too much) | 85% or more |
| Correctness | A judge's score from 1 to 5 against the reference answer | Information only |
| Faithfulness | A judge's score from 1 to 5 for staying within the passages | Information only |
| P95 latency | The time within which 95 in 100 answers finished | 8 seconds or less |

Judge scores come from another AI model that has not been checked against human marking. Treat them as a guide.

Three cautions:

- **P95 latency will almost certainly show FAIL.** Every measured configuration is far over 8 seconds on the free models. That is a known result, not a fault with your run. On a run that includes rate-limit waits it measures the waiting more than the model.
- **The page does not list the questions.** It shows totals only. A "failed" question is one that failed any check: the right source was not retrieved, an invalid citation, a citation in the wrong format, no citation, a missed or unwarranted decline, or a judge score of 2 or below. A per-question table is not built yet.
- **The page does not save results.** It holds them in the server's memory and a temporary folder, and it forgets them when the server restarts. Copy the numbers you need or take a screenshot before you leave.

**To get saved, per-question results**

Ask a developer to run the command-line version, which writes a results file and a report with a table of every failed question:

```bash
python -m scripts.run_evaluation --model gemini-3-8-flash --output benchmarks/results/<name>.jsonl --report benchmarks/reports/<name>.md
```

Use the model names from `litellm/config.yaml` (`gemini-3-8-flash`, `groq-gpt-oss-120b`, `openrouter-free`, `free-fallback`). Add `--judge <name>` for judge scores and `--resume` to continue an interrupted run. The command needs `LITELLM_MASTER_KEY` and the database settings in `.env`, and the LiteLLM proxy must be running.

The gates on the page come from `docs/EVALUATION.md`. The rules for choosing between models, which add scoring and extra gates, are in `docs/MODEL-AB-SCORING.md`, and `docs/MODEL-AB-RESULTS.md` shows where the comparison stands.

## 9. If something goes wrong

| Problem | Likely cause | What to do |
|---|---|---|
| Upload stays `pending` | n8n is off, the workflow is inactive or the secret differs | Section 6, the checks table. |
| Every retrieval fails with "MissingGreenlet" | `SUPABASE_DB_URL` uses the asyncpg driver | It must start `postgresql+psycopg2://`. See the README. |
| Database connection errors | The Supabase project is paused (free plans pause after 7 days) or the address is wrong | Wake the project from the Supabase dashboard and check `SUPABASE_DB_URL`. |
| Answers fail or time out | Free model limits | Try another model in the **AI Model** list, or wait. Check `docker compose logs litellm`. |
| A new user cannot sign in | Wrong email, or the account is inactive | Run the create command again (section 2) and read the `active=` value it prints. |
| The evaluation run says "The evaluation run stopped before completion." | The command failed, often a missing key or an unreachable proxy | Read the server log and retry. |
| `/chat` is open without sign-in | `CHAINLIT_AUTH_SECRET` is not set | Set it in `.env` and restart. The application refuses to start in production without it. |

## 10. What is not available yet

- Document type, authority and effective-date fields, and filtering by them.
- Marking an older document as superseded or withdrawn, and keeping a version history.
- Filtering the document list by status, type or date, and sorting it.
- The failure reason on the Documents page.
- A preview of how a document was split before it is indexed.
- Reading, editing or disabling accounts from a page.
- Per-question results, saved runs and a comparison of runs on the evaluation page.
- Automatic checks for client identifiers in uploads or questions.

## Screenshots to capture

For the person adding screenshots. Use a demo account and demo files with public content. Capture at a normal desktop width.

| ID | Page and state | Annotate | Keep out of the frame |
|---|---|---|---|
| AG-01 | Documents page with at least four documents, one of each status if possible | Browse Files, search box, STATUS, delete and retry icons | Real email in the profile area |
| AG-02 | Table with one `pending` and one `ready` document | The two status badges | - |
| AG-03 | Search box with "division" typed | The search box and the narrowed table | - |
| AG-04 | The Delete document dialog | Cancel and Confirm delete | A real client file name |
| AG-05 | LLM Testing, Benchmark settings card, defaults | Each setting and Run Benchmark | - |
| AG-06 | A finished run's Summary metrics card | The gates badge and one metric card | - |
