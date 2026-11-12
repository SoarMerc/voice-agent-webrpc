# Faithfulness review: held-out run of 12 Nov 2026

Run: `eval/results/test-qwen3.5_4b-20261112-1636.json` (qwen3.5:4b, prompt at commit `8e923b9`).
Every reply the model spoke as an answer (label ANSWER or PARTIAL, 31 replies) checked claim by
claim against `kb/wise-where-is-my-money.md`. Reviewer: Claude. Per D13, Shivansh reviews every
"unsure" and the sample marked **(sample)**.

## Summary

| Verdict | Count |
|---|---|
| Supported: every claim is in the FAQ | 22 |
| Unsure: a stretch or a small distortion | 3 |
| Unsupported: at least one claim not in the FAQ, or wrong | 6 |

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

## Not faithfulness, but seen while reviewing

- Too long for speech: q05 and q25 run to about 80 words and read the proof-of-payment list
  aloud. Seven replies drop "Anything else about your transfer?". q02 ends "Want to know more
  about your specific situation?", which invites an account question.
- UNCLEAR replies are usually the bare label with no sentence. The pipeline should use fixed
  lines for unclear turns too, like handoffs.
- q40 ("I entered the wrong bank details") is labelled `out` in the test set, but the delay
  article does say "you can either fix the details or cancel the transfer", and the reply is
  faithful to it. The label may be wrong; Shivansh to decide.
