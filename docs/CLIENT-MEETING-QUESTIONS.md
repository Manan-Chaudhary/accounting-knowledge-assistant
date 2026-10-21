# First Client Meeting - Questions That Change the Build

> **Status: this meeting never took place.** The questions are unanswered, so the question set and document list in the built system are assumptions. Hand these to the next team. Things that changed since this was written: the system uses email and password sign-in with roles `staff`, `admin` and `team` (no SSO, no Chainlit auth callback), and it is not deployed anywhere.

Ranked. If the meeting is cut short, ask in this order. Each entry states what the answer changes, so you can tell when you have enough and move on.

Do not open by describing the technology. Open by confirming what they do - section 2 of [`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) - because arriving already knowing what they do (a generalist tax and accounting firm with an SMSF administration service line) buys more credibility than any architecture slide.

## Tier 1 - ask these no matter what

**Q1. Can we see the last 50 questions your staff actually asked each other, or that clients and referrers asked you?**
Email threads, chat history, or the customer service manager's memory - anything real. *Changes:* the entire benchmark distribution in [`EVALUATION.md`](EVALUATION.md) section 2, which is currently our estimate. This is the single highest-value thing to leave the meeting with.

**Q2. Which parts of your general tax and business-services work should the assistant cover, beyond SMSF?**
*Changes:* corpus scope. Alfa Focus is a generalist firm, so the SMSF-weighted corpus is too narrow. A general practice book roughly triples Corpus A, so agree priorities in the same meeting.

**Q3. When a new staff member joins, what do you hand them? Are there written procedures, checklists, or templates - or is it learned by sitting next to someone?**
*Changes:* whether Corpus B can be indexed or has to be created. This is the biggest single delivery risk in the project ([`RAG-DESIGN.md`](RAG-DESIGN.md) section 2). Ask it early enough that you can negotiate interview time in the same conversation. If the answer is "it's in people's heads", propose the interviews there and then and frame the written procedures as a deliverable they keep regardless of the software.

**Q4. What software do you administer funds on, and does it have an API?**
Expect BGL Simple Fund 360 or Class Super, with something for documents. *Changes:* whether firm process can be read from structured data or only from interviews; also whether integration is in scope at all.

**Q5. What is your position on client data and AI tools? Has the firm formed one?**
*Changes:* which model `app/rag/generator.py` may call (it currently goes through LiteLLM to free-tier Gemini, Groq and OpenRouter, with no confirmed no-training terms), and what goes in the proposal. CPA Australia's stated position is that client data must not go into public AI tools while in-house tools with adequate controls are acceptable, so the answer determines whether a hosted API is available to us at all. Get it in writing if you can.

## Tier 2 - ask if there is time

**Q6. Who would use this, and how many of them?**
*Changes:* the roles in `app/auth/` (currently `staff`, `admin`, `team`), and whether per-user permissions on Corpus B are needed.

**Q7. Walk us through one fund from onboarding to lodgement.**
*Changes:* everything about Corpus B structure. Also the fastest way for a non-accounting team to understand the business. Ask for it as a story, not a list.

**Q8. What went wrong most recently - a missed deadline, a contravention, a question someone got wrong?**
*Changes:* where the assistant should be sharpest. People describe their real pain when asked about a specific incident and describe their imagined pain when asked what they need.

**Q9. How do you currently find out that something has changed?**
Newsletters, professional body alerts, a partner who reads the ATO newsroom. *Changes:* whether the weekly change digest ([`RAG-DESIGN.md`](RAG-DESIGN.md) section 4) is a killer feature or a duplicate of something they already have. Worth knowing before building it.

**Q10. Would one of your accountants spend two hours reviewing about 40 answers so we can measure accuracy properly?**
*Changes:* whether R1 ground truth and judge validation are available at all ([`EVALUATION.md`](EVALUATION.md) sections 1 and 5). Ask concretely - a named time cost against a named benefit - not as an open-ended request for help.

**Q11. Is there a question you would never want an AI tool to answer?**
*Changes:* the refusal rules in [`PROMPTS.md`](PROMPTS.md). Their answer is more persuasive in the proposal than ours, and it converts a limitation into a requirement they specified.

## Tier 3 - housekeeping

**Q12.** Which legal entity are we contracting with - "Alfa Focus Pty Ltd", or the trustee for the Alfa Focus Unit Trust? The ABN register and the tax agent registration point at different addresses ([`CLIENT-BRIEF.md`](CLIENT-BRIEF.md) section 1).

**Q13.** Who is our single point of contact, and what response time can we expect? A small practice gets busy; agree the cadence now.

**Q14.** Does anything we produce need to survive after the semester - and if so, who maintains it? There appears to be no IT function, which shapes the handover deliverable and whether the Supabase and any future hosting accounts end up in the firm's name (nothing is hosted yet).

## Things to avoid saying

- Do not comment on their website being down. Note it internally; it is useful calibration and a poor opening line.
- Do not promise the assistant will "keep them up to date with all changes". Promise a defined corpus, refreshed on a defined schedule, with a change digest. The difference is the whole project.
- Do not describe it as a chatbot. Describe it as an internal reference tool that always shows its sources. That is what a regulated professional wants and it is also literally what it is.
- Do not offer to handle client data in the first meeting. Establish the confidentiality boundary before anyone offers to cross it.
