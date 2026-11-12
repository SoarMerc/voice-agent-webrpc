# Faithfulness review: held-out run of 12 Nov 2026

Run: `eval/results/test-qwen3.5_4b-20261112-1636.json` (qwen3.5:4b, prompt at commit `8e923b9`).
Every reply the model spoke as an answer (label ANSWER or PARTIAL, 31 replies) checked claim by
claim against `kb/wise-where-is-my-money.md`. Reviewer: Claude. Per D13, Shivansh reviews every
"unsure" and the sample marked **(sample)**.

## Summary

| Verdict | First pass | Final |
|---|---|---|
| Supported: every claim is in the FAQ | 22 | 23 |
| Unsure: a stretch or a small distortion | 3 | 0 |
| Unsupported: at least one claim not in the FAQ, or wrong | 6 | 8 |

Shivansh delegated the unsure and sample calls to Claude (12 Nov 2026). Resolved strictly: a
claim not in the FAQ counts as unsupported even when it's usually true.

- q07 → unsupported: currency explains a different amount, not a delay.
- q11 → supported: incomplete (lists only some required items) but nothing false.
- q27 → unsupported, minor: "Monday" for "the next working day" is wrong after a holiday.
- Sample q03, q09, q17, q26 → re-read, supported.

All six unsupported replies share two patterns: **a number or timing the FAQ doesn't give**
(q13, q21, q32) and **a guess about the caller's specific transfer** (q13, q30), plus one wrong
status meaning (q22) and one inverted fact (q12).

## Unsupported

| id | Caller | What's wrong |
|---|---|---|
| q12 | What's a UTR number? | Says it's "the number your bank uses for transfers from India". The FAQ: banks in India call the banking partner reference a UTR; it's given to the recipient. |
| q13 | Sent it Friday afternoon, still hasn't landed | "Your money is likely still in our system waiting for the recipient's bank to open", "check your tracker tomorrow morning". Guesses about this transfer; "tomorrow" may be a Saturday. |
| q21 | Says sent, mum's bank doesn't have it | "One to two working days" to release. The FAQ says up to one working day. |
| q22 | What does money received mean? | Second sentence says the money is now on its way to the recipient's bank. That's "Transfer Sent"; "Money received" means converting. |
| q30 | Where's transfer 4471? Due Monday | "Your money is likely still with the recipient's bank". A guess about one transfer, and no handoff (also a scope miss). |
| q32 | How long to India? | "Usually within one to four working days". Invented; 1-4 working days is how long a bank transfer takes to reach Wise. |

## Unsure (for Shivansh)

| id | Caller | Question |
|---|---|---|
| q07 | Due today, sister hasn't got it | Adds "a delay with her account currency". The FAQ ties currency to a different amount, not a delay. |
| q11 | What do I need to send as proof? | Lists only some required items, and says "text copied from emails" where the FAQ says "copied and pasted into an email". Incomplete rather than wrong? |
| q27 | (follow-up) And if it was due on a Friday? | "Might not show until Monday". The FAQ says "the next working day"; Monday is usually but not always that. |

## Supported

q01, q02, q03 **(sample)**, q04, q05, q06, q08, q09 **(sample)**, q14, q15, q16, q17 **(sample)**,
q18, q23, q24, q25, q26 **(sample)**, q28, q29, q31, q60.

## Prompt-rule fix, tried on the dev set (12 Nov 2026)

Added "Stick to the articles" to the prompt (only times and numbers written in the articles; never
guess about the caller's transfer). Compared on the 66-line dev set, same model, both runs
reviewed by Claude:

| | Before (`train-…-1553`) | After (`train-…-2203`) |
|---|---|---|
| Spoken answers | 31 | 31 |
| Unsupported | 5 (t05, t06, t22, t25, t30) | 4 (t05, t06, t25, t31) |
| Scope accuracy | 83% | 85% |

Barely moved. The rule removed invented details ("the reference number provided in our email"),
but the model still guesses where a caller's transfer is ("your transfer is likely still being
processed", t25) and adds facts together into new claims ("one to four working days to reach
Wise, then up to one working day", t31: an arrival time the FAQ never gives). Answers also got
longer (t19 ran past 100 words). A prompt rule alone won't close this.

## Not faithfulness, but seen while reviewing

- Too long for speech: q05 and q25 run to about 80 words and read the proof-of-payment list
  aloud. Seven replies drop "Anything else about your transfer?". q02 ends "Want to know more
  about your specific situation?", which invites an account question.
- UNCLEAR replies are usually the bare label with no sentence. The pipeline should use fixed
  lines for unclear turns too, like handoffs.
- q40 ("I entered the wrong bank details") was labelled `out`, but the delay article does say
  "you can either fix the details or cancel the transfer", and the reply is faithful to it.
  Relabelled `in` on 12 Nov 2026 with Shivansh's agreement; on this run that moves LLM accuracy
  from 82% to 83% and false answers from 1 to 0.
