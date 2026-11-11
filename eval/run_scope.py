"""Text-only scope eval (no audio).

Runs every line of eval/questions.jsonl through three scope checks (DECISIONS.md D4):
  llm      - the answer model writes the class label on its first line (agent/system_prompt.md)
  clf      - sentence embeddings + logistic regression, trained on eval/train.jsonl only
  cascade  - clf when its confidence >= threshold, otherwise the llm label

Usage:
  python eval/run_scope.py [--model qwen3.5:4b] [--embed BAAI/bge-base-en-v1.5]

Writes eval/results/<model>-<timestamp>.json (every prediction, LLM reply and timing) and prints
a summary.
"""

import argparse
import json
import statistics
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import ollama
from sentence_transformers import SentenceTransformer
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parent.parent
CLASSES = ["in", "in_handoff", "out", "urgent", "unclear"]
ANSWERS = {"in", "in_handoff"}    # classes where the agent speaks FAQ content
HANDOFFS = {"out", "urgent"}      # classes where it only plays a fixed line


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def system_prompt():
    template = (ROOT / "agent" / "system_prompt.md").read_text(encoding="utf-8")
    faq = (ROOT / "kb" / "wise-where-is-my-money.md").read_text(encoding="utf-8")
    return template.replace("{faq}", faq)


def parse_label(reply):
    first = reply.strip().splitlines()[0].strip().strip("`*:. ").lower() if reply.strip() else ""
    return first if first in CLASSES else f"invalid:{first[:20]}"


def run_llm(client, model, prompt, item):
    messages = [{"role": "system", "content": prompt}]
    for turn in item.get("context", []):
        messages.append({"role": "user" if turn["role"] == "user" else "assistant", "content": turn["text"]})
    messages.append({"role": "user", "content": item["text"]})

    start = time.perf_counter()
    first_token = label_at = None
    reply = ""
    # Native Ollama API with think=False. Through the OpenAI-compatible endpoint with
    # reasoning_effort "none" the first content token took ~2.6 s; natively ~0.5 s.
    stream = client.chat(
        model=model,
        messages=messages,
        stream=True,
        think=False if "qwen" in model else None,
        options={"temperature": 0, "num_predict": 200},
    )
    for chunk in stream:
        delta = chunk.message.content or ""
        if not delta:
            continue
        if first_token is None:
            first_token = time.perf_counter() - start
        reply += delta
        if label_at is None and "\n" in reply:
            label_at = time.perf_counter() - start
    total = time.perf_counter() - start
    return {
        "label": parse_label(reply),
        "reply": reply,
        "first_token_s": round(first_token or total, 3),
        "label_s": round(label_at or total, 3),
        "total_s": round(total, 3),
    }


def clf_text(item):
    """What the classifier sees: the previous agent line (if any) plus the caller's words."""
    context = item.get("context", [])
    previous = next((t["text"] for t in reversed(context) if t["role"] == "agent"), "")
    return f"{previous} || {item['text']}" if previous else item["text"]


def metrics(gold, pred):
    n = len(gold)
    pairs = list(zip(gold, pred))
    return {
        "accuracy": round(sum(g == p for g, p in pairs) / n, 3),
        # answered (spoke FAQ content) when it should have handed off: the costly error
        "false_answer": sum(g in HANDOFFS and p in ANSWERS for g, p in pairs),
        # handed off when it could have answered
        "false_handoff": sum(g in ANSWERS and p in HANDOFFS for g, p in pairs),
        # urgent treated as an ordinary out-of-scope (soft handoff instead of immediate)
        "urgent_softened": sum(g == "urgent" and p == "out" for g, p in pairs),
        "invalid_label": sum(p.startswith("invalid") for p in pred),
        "n": n,
    }


def confusion(gold, pred):
    labels = CLASSES + sorted({p for p in pred if p not in CLASSES})
    counts = Counter(zip(gold, pred))
    width = max(len(l) for l in labels) + 2
    lines = ["gold \\ pred".ljust(width) + "".join(l[:10].rjust(11) for l in labels)]
    for g in CLASSES:
        lines.append(g.ljust(width) + "".join(str(counts[(g, p)]).rjust(11) for p in labels))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--embed", default="BAAI/bge-base-en-v1.5")
    parser.add_argument("--host", default="http://localhost:11434")
    args = parser.parse_args()

    questions = load_jsonl(ROOT / "eval" / "questions.jsonl")
    train = load_jsonl(ROOT / "eval" / "train.jsonl")
    gold = [q["class"] for q in questions]

    # Small classifier, trained only on train.jsonl (D12).
    encoder = SentenceTransformer(args.embed)
    x_train = encoder.encode([t["text"] for t in train], normalize_embeddings=True)
    clf = LogisticRegression(max_iter=2000, C=4.0).fit(x_train, [t["class"] for t in train])
    t0 = time.perf_counter()
    x_eval = encoder.encode([clf_text(q) for q in questions], normalize_embeddings=True)
    clf_ms = (time.perf_counter() - t0) / len(questions) * 1000
    proba = clf.predict_proba(x_eval)
    clf_pred = [clf.classes_[i] for i in proba.argmax(axis=1)]
    clf_conf = proba.max(axis=1)

    # LLM first-line label.
    client = ollama.Client(host=args.host)
    prompt = system_prompt()
    run_llm(client, args.model, prompt, {"text": "hello"})  # warm up: load model, cache the prompt
    llm_runs = []
    for q in questions:
        r = run_llm(client, args.model, prompt, q)
        llm_runs.append(r)
        mark = "ok " if r["label"] == q["class"] else "XX "
        print(f"{mark}{q['id']} gold={q['class']:<10} llm={r['label']:<10} clf={clf_pred[len(llm_runs)-1]:<10} {r['label_s']:.2f}s")
    llm_pred = [r["label"] for r in llm_runs]

    results = {"llm": metrics(gold, llm_pred), "clf": metrics(gold, clf_pred)}
    for threshold in (0.5, 0.6, 0.7, 0.8):
        cascade = [c if conf >= threshold else l for c, conf, l in zip(clf_pred, clf_conf, llm_pred)]
        m = metrics(gold, cascade)
        m["clf_share"] = round(float(np.mean(clf_conf >= threshold)), 2)
        results[f"cascade@{threshold}"] = m

    label_times = [r["label_s"] for r in llm_runs]
    timing = {
        "llm_label_median_s": round(statistics.median(label_times), 3),
        "llm_label_p90_s": round(float(np.percentile(label_times, 90)), 3),
        "llm_first_token_median_s": round(statistics.median(r["first_token_s"] for r in llm_runs), 3),
        "clf_ms_per_item": round(clf_ms, 1),
    }

    print("\n== scope metrics ==")
    for name, m in results.items():
        print(f"{name:<14} {m}")
    print("\n== timing ==", timing)
    print("\n== llm confusion ==\n" + confusion(gold, llm_pred))
    print("\n== clf confusion ==\n" + confusion(gold, clf_pred))

    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = out_dir / f"{args.model.replace(':', '_').replace('/', '_')}-{stamp}.json"
    out.write_text(json.dumps({
        "model": args.model, "embed": args.embed, "metrics": results, "timing": timing,
        "items": [
            {**q, "llm": r, "clf": c, "clf_conf": round(float(conf), 3)}
            for q, r, c, conf in zip(questions, llm_runs, clf_pred, clf_conf)
        ],
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
