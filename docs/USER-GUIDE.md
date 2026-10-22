# Alfa Focus Knowledge Assistant: user guide

For accountants and other Alfa Focus staff who ask the assistant questions.
Written 2026-10-22 by Ronith Mugundakumar (BA) from the application on `main` (commit `c059f82`). The Documents and Testing pages are covered in the [admin guide](ADMIN-GUIDE.md).

**Draft for screenshots.** Each `[Screenshot SG-n]` marker shows where a screenshot goes and what it must show. The list at the end tells the person adding them what to capture and what to keep out of the frame.

The assistant is a prototype and has not been tested with Alfa Focus staff. Ask your administrator for the address to open.

## What the assistant does

- Answers questions about Australian tax, superannuation and SMSF rules from a library of 73 approved documents: ATO guidance and rulings, legislation, and Tax Practitioner Board and professional standards.
- Shows numbered citations in each answer so you can see which document a statement came from.
- Keeps your chats so you can return to them.

## What it does not do

- It does not give personal financial, tax or investment advice. It sets out the rules, and you decide.
- It does not know your clients. Do not type client names, tax file numbers, member numbers or ABNs. A reminder is shown under the question box.
- It does not sign anything off. A registered tax agent still reviews anything that leaves the firm.
- It knows only the library. It has no firm procedures, so it cannot say how Alfa Focus handles a matter.

## 1. Sign in and sign out

**To sign in**

1. Open the address your administrator gave you. The sign-in page opens.
2. Type your work email address in **Email Address**.
3. Type your password in **Password**. Select the eye icon to show or hide what you typed.
4. Select **Log In**.

You land on the chat page. An administrator creates your account; there is no sign-up page and no password reset page. Ask your administrator if you have no account or have forgotten the password. You are signed out automatically after about 8 hours.

`[Screenshot SG-01: the sign-in page with the Email Address field, the Password field with its eye icon, and the Log In button, no password typed]`

If sign-in fails, the page shows one of these messages under the password field:

| Message | What to do |
|---|---|
| Email address is required. / Enter a valid email address. / Password is required. | Fix the field and try again. |
| The credentials were not recognised. Check your email and password and try again. | Check both and try again. The page does not say which one was wrong. |
| This account is not active. Contact your Alfa Focus administrator. | Ask your administrator to reactivate the account. |
| Sign-in is temporarily unavailable. Please try again shortly. | Wait a minute and try again. If it continues, tell your administrator. |

**To sign out**

1. At the bottom of the left menu, select **Sign out**.
2. Select **OK** when asked "Are you sure you want to log out?".

## 2. Ask a question

1. In the left menu, select **New Chat**. The page shows "How can I help with SMSF guidance?".
2. Select the box that says "Ask an Accounting question…" and type your question. Write it as a complete question and include the income year when it matters, for example "What is the general transfer balance cap for 2026-27?".
3. Select the arrow button, or press Enter.
4. Watch the answer appear. It streams in a few words at a time.

`[Screenshot SG-02: the chat page with a question typed in the box and the arrow button, and the notice about client identifiers visible underneath]`

Things to know:

- **Waiting.** Expect a wait. In a test of five questions on 14 October, the first words took about a minute to appear and the slowest answer took almost three minutes. The free AI plans behind the assistant are the main cause. Do not send the question again while you wait.
- **Stopping.** While an answer is streaming, the arrow becomes a red stop button. Select it to stop. The answer keeps what has appeared and adds "(Generation stopped by user)".
- **AI Model.** The **AI Model** list above the question box offers Gemini 3.8 Flash (the default), Groq GPT-OSS 120B, OpenRouter Free and Free Fallback. Leave it on the default unless your administrator asks you to change it. The models differ in speed and in how carefully they cite, and none has been fully compared yet. You cannot change the model while an answer is streaming.
- **Client details.** If you enter a client name or number anyway, the assistant should answer the rules question without repeating it and add the notice "[Notice: Client identifiers omitted per privacy guidelines]". Treat that as a safeguard, not permission.

## 3. Read an answer and its sources

An answer appears in a card headed **Alfa Focus Assistant**. Longer answers are split under headings. Each statement the assistant takes from a document ends with a number in square brackets, such as [1] or [2], shown as a small grey chip.

`[Screenshot SG-03: an answer card with two citation chips highlighted, one of them with its tooltip showing a document name]`

**To see which document a number points to**

1. Hover over the chip with your mouse. A tooltip shows the document name, such as `ato-cgt-discount.txt`.
2. Read the document name to judge how reliable it is. Names beginning `ato-` are ATO pages, `leg-` is legislation, `apesb-` and `tpb-` are professional standards.

To read the original, ask your administrator for the source list (`docs/DOCUMENT-CORPUS.md`, section 7), which gives the address of each page.

**What the chips tell you**

| You see | It means | What to do |
|---|---|---|
| A grey chip such as [2] | The number matches a document the assistant was given | Check the document before relying on the statement. |
| A chip that reads [7?] | The assistant cited a number that does not match any document it was given | Do not rely on that statement. Treat it as unsupported. |
| A chip whose tooltip says "Waiting for retrieved sources" | The list of documents arrives after the text | Wait for the answer to finish. |
| Plain numbers with no hover, in a chat you reopened | Saved chats keep the numbers but not the document names | Ask the question again if you need the sources. |

Citations show that the assistant had the document. They do not prove the document supports the statement, so read the source for anything you will act on. Clicking a citation does not open the passage yet.

**Other things in an answer**

- Amounts and rates that change each year are meant to carry the income year, such as "For 2026-27, the general transfer balance cap is $2.1 million". If an answer gives a figure with no year, ask again and name the year.
- If your question rests on an out-of-date figure, the assistant should correct it first, then answer.

## 4. When the assistant declines or cannot answer

The assistant should say so plainly instead of guessing. You may see:

| What the assistant says | What it means | What to do |
|---|---|---|
| "I could not find authority for this…" (the exact words vary by model) | The library has no document that covers the question | Check the primary source or ask a colleague. Do not rephrase the question to force an answer. |
| "I could not find authority or relevant document chunks in the approved context to answer this query. Please escalate this matter to a qualified practitioner or refer directly to primary legislation." | Nothing relevant was found at all | Escalate, or check the primary legislation. |
| "Under Alfa Focus compliance guidelines and statutory requirements, I cannot provide personal financial, tax, or investment advice…" | Your question asked what someone should do, such as "Should I…" or "Should my client…" | Rephrase it as a rules question, for example "What rules apply to…", and decide yourself. |
| It says it cannot confirm a ruling or provision | You named a ruling that is not in the library, such as a number you were given second-hand | Look the ruling up at the source. The assistant will not confirm one it cannot find. |
| It will not give a figure for a member or fund | That figure depends on the member's own records | Use the member's transfer balance account, the fund's records or ATO Online. |

A decline is not an error. The assistant is built to decline when it has no source.

`[Screenshot SG-04: an answer card showing a decline, using the question "What is the Victorian land tax tax-free threshold for 2026?"]`

## 5. Follow-up questions

You can send another question in the same chat, and all of them stay together in your history. **The assistant does not read your earlier messages in that chat.** It answers each question on its own, so a follow-up such as "And what about a complying super fund?" will not make sense to it.

Write every follow-up as a full question:

| Instead of | Write |
|---|---|
| "And what about a complying super fund?" | "Can a complying super fund use the CGT discount, and by how much?" |
| "What about 2025-26?" | "What is the general transfer balance cap for 2025-26?" |

## 6. Copy an answer

There is no copy button yet.

1. Press and hold the mouse button at the start of the answer, drag to the end, and release.
2. Press Ctrl+C (Cmd+C on a Mac).
3. Paste into your email or document with Ctrl+V.

The citation numbers copy as plain text, such as [1]. The document names in the tooltips do not copy. Before you send the text on, add the name of each source next to its number, and check each source.

## 7. Manage your chats

Your chats are listed in the left menu under **Recent Conversations**. The list shows your 20 most recent chats, and only your own. Each chat is named after the start of its first question. The menu says "No past sessions yet" until you have asked something.

`[Screenshot SG-05: the left menu showing New Chat, Recent Conversations with three chats, and a trash icon on one chat]`

**To open an earlier chat**

1. Select its name under **Recent Conversations**. The messages load.
2. Type a new question at the bottom to carry on. Remember that the assistant will not read the earlier messages (section 5).

**To start a new chat**

1. Select **New Chat** at the top of the left menu.

**To delete a chat**

1. Point at the chat in **Recent Conversations** and select the trash icon.
2. Select **OK** when the browser asks "Are you sure you want to delete this conversation?".

The chat and all of its messages are deleted for good, and you cannot undo it. If you delete the chat you have open, the page returns to a new chat. If the page says "Failed to delete conversation.", try again.

**Renaming** a chat is not available yet.

## 8. Good habits

- Never type a client's name, TFN, member number or ABN.
- Name the income year for any rate, cap or threshold.
- Check the source for anything you will rely on. The assistant is a way to find the rule quickly, not a substitute for reading it.
- Treat an answer that cites a number with a question mark, or cites nothing, as unchecked.
- Tell your administrator if an answer is wrong. Note the question, the answer and the time, so the team can add it to the test set.

## 9. If something goes wrong

| Problem | What to do |
|---|---|
| The page says "Connecting…" and nothing happens | Wait a few seconds, then refresh the page. |
| "The assistant encountered a streaming error." or "Failed to generate response. Please try again." | Send the question again. If it keeps failing, change the **AI Model** and try again, then tell your administrator. The models run on free plans with strict limits, and they sometimes refuse a request. |
| An answer never finishes | Select the red stop button, then ask again. |
| You are sent back to the sign-in page | Your session ended. Sign in again. |
| A chat is missing from the list | Only your 20 most recent chats appear. |
| You cannot see **LLM Testing** in the menu | That page is only for the project team. It is not for accountants. |

## 10. What is not available yet

These features were planned but are not in the application. Do not look for them.

- Clicking a citation to open the document passage.
- A copy button that keeps the sources with the text.
- Renaming a chat.
- The assistant remembering earlier messages in a chat.
- Answers from Alfa Focus's own procedures. No firm documents are loaded.
- Feedback buttons on answers.
- A reset-password page.

## Screenshots to capture

For the person adding screenshots. Use a demo account and the questions given. Capture at a normal desktop width.

| ID | Page and state | Annotate | Keep out of the frame |
|---|---|---|---|
| SG-01 | Sign-in page, nothing typed | Number the fields and the Log In button | Any real email address or password |
| SG-02 | Chat page with "What is the general transfer balance cap for 2026-27?" typed, not yet sent | The question box, the arrow button and the client-identifier notice | Any client name |
| SG-03 | A finished answer, with the mouse over a citation chip so its tooltip shows | The chip and the tooltip | Anything but demo content |
| SG-04 | The answer to "What is the Victorian land tax tax-free threshold for 2026?" | The decline wording | - |
| SG-05 | Left menu with three chats and the trash icon | New Chat, Recent Conversations, the trash icon | Real email in the profile area at the bottom |
