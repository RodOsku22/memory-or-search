"""Run the experiment. Resumable: finished cells in data/runs.jsonl are skipped.

usage: python run.py --runs 50 [--bonus] [--engines openai,anthropic,google]
                     [--categories meal_kits,...] [--concurrency 8] [--out data/runs.jsonl]
Trials are shuffled so search-on and search-off runs interleave over time.
"""
import argparse, asyncio, json, os, random, sys, time
from datetime import datetime, timezone

import httpx

sys.path.insert(0, os.path.dirname(__file__))
from config import CATEGORIES, ENGINES, CONDITIONS
from engines import CALLERS


def plan(args):
    cats = [c for c in CATEGORIES if (args.categories and c in args.categories)
            or (not args.categories and (args.bonus or not CATEGORIES[c].get("bonus")))]
    engines = args.engines or list(ENGINES)
    trials = []
    for cat in cats:
        for ptype, prompt in CATEGORIES[cat]["prompts"].items():
            if args.prompt_types and ptype not in args.prompt_types:
                continue
            for eng in engines:
                for cond in (args.conditions or CONDITIONS):
                    for i in range(args.runs):
                        trials.append(dict(category=cat, prompt_type=ptype, prompt=prompt,
                                           engine=eng, model=ENGINES[eng]["model"],
                                           condition=cond, run=i))
    return trials


def key(t):
    return (t["category"], t["prompt_type"], t["engine"], t["model"], t["condition"], t["run"])


async def worker(name, queue, client, sems, out, stats):
    while True:
        t = await queue.get()
        if t is not None and stats.get("stop"):
            queue.task_done()
            continue
        if t is None:
            queue.task_done()
            return
        async with sems[t["engine"]]:
            rec = dict(t)
            rec["ts"] = datetime.now(timezone.utc).isoformat()
            for attempt in range(6):
                t0 = time.time()
                try:
                    res = await CALLERS[t["engine"]](client, t["model"], t["prompt"],
                                                     t["condition"] == "search")
                    rec.update(res)
                    rec["latency_s"] = round(time.time() - t0, 2)
                    rec.pop("error", None)
                    break
                except httpx.HTTPStatusError as e:
                    code = e.response.status_code
                    rec["error"] = f"{code}: {e.response.text[:400]}"
                    if "insufficient_quota" in e.response.text or "credit balance" in e.response.text:
                        stats["stop"] = True
                        break
                    if code in (429, 500, 502, 503, 504, 529):
                        await asyncio.sleep(min(60, 2 ** attempt + random.random()))
                        continue
                    break
                except Exception as e:  # network, timeout, parse
                    rec["error"] = f"{type(e).__name__}: {e}"[:400]
                    await asyncio.sleep(min(60, 2 ** attempt + random.random()))
            out.write(json.dumps(rec) + "\n")
            out.flush()
            stats["done"] += 1
            if "error" in rec:
                stats["err"] += 1
            if stats["done"] % 50 == 0:
                print(f"{stats['done']}/{stats['total']} done, {stats['err']} errors", flush=True)
        queue.task_done()


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=50)
    ap.add_argument("--bonus", action="store_true")
    ap.add_argument("--engines", type=lambda s: s.split(","))
    ap.add_argument("--categories", type=lambda s: s.split(","))
    ap.add_argument("--prompt-types", type=lambda s: s.split(","))
    ap.add_argument("--conditions", type=lambda s: s.split(","))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "data", "runs.jsonl"))
    args = ap.parse_args()

    trials = plan(args)
    done = set()
    if os.path.exists(args.out):
        for line in open(args.out):
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "error" not in r:
                done.add(key(r))
    todo = [t for t in trials if key(t) not in done]
    random.seed(7)
    random.shuffle(todo)
    # fill every cell round by round, so a budget stop leaves cells balanced
    todo.sort(key=lambda t: t["run"])
    print(f"{len(trials)} planned, {len(done)} already done, {len(todo)} to run", flush=True)
    if not todo:
        return
    stats = {"done": 0, "err": 0, "total": len(todo)}
    sems = {e: asyncio.Semaphore(args.concurrency) for e in ENGINES}
    queue = asyncio.Queue()
    for t in todo:
        queue.put_nowait(t)
    n_workers = args.concurrency * len(ENGINES)
    for _ in range(n_workers):
        queue.put_nowait(None)
    async with httpx.AsyncClient() as client:
        with open(args.out, "a") as out:
            await asyncio.gather(*[worker(i, queue, client, sems, out, stats) for i in range(n_workers)])
    print(f"finished: {stats['done']} written, {stats['err']} errors", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
