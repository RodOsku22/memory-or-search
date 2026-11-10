"""Brand extraction and statistics. Writes data/results.json and CSV tables.

Definitions (following Petra Labs where they define a term):
- answering run: a run whose answer names at least one brand in the vocabulary
- visibility: share of answering runs in a cell that name the brand
- memory visibility (M): web search off; search visibility (S): web search on
- search lift: S - M, with a bootstrap 95% CI and a permutation p-value,
  Benjamini-Hochberg corrected within each engine x prompt cell
- profile distance: total variation distance (TVD) between normalized brand
  visibility profiles, compared against a label-permutation noise floor (p95)
"""
import json, os, re, sys
from collections import defaultdict
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from config import CATEGORIES, ENGINES

ROOT = os.path.join(os.path.dirname(__file__), "..")
RNG = np.random.default_rng(11)
STRONG = 50.0  # percent; threshold for the four-way bucket


def compile_vocab():
    vocab = {}
    for cat, c in CATEGORIES.items():
        vocab[cat] = {b: [re.compile(r"(?<![A-Za-z0-9])" + re.escape(a) + r"(?![A-Za-z0-9])")
                          for a in aliases] for b, aliases in c["brands"].items()}
    return vocab


VOCAB = compile_vocab()


def brands_in(text, cat):
    return sorted(b for b, pats in VOCAB[cat].items() if any(p.search(text or "") for p in pats))


def supported(brand, cat, rec):
    """Brand alias appears in a cited (or, for Claude, retrieved) page's URL or title."""
    pats = VOCAB[cat][brand]
    pages = (rec.get("citations") or []) + (rec.get("interim") or [])
    for p in pages:
        hay = f"{p.get('title') or ''} {p.get('url') or ''}"
        hay_loose = hay.replace("-", " ").replace("_", " ")
        if any(pt.search(hay) or pt.search(hay_loose) for pt in pats):
            return True
        # domain match, e.g. capitalone.com, hellofresh.com
        for a in CATEGORIES[cat]["brands"][brand]:
            slug = re.sub(r"[^a-z0-9]", "", a.lower())
            if len(slug) >= 4 and slug in re.sub(r"[^a-z0-9]", "", (p.get("url") or "").lower()):
                return True
    return False


def load(paths):
    rows = []
    lines = [l for p in paths for l in open(p)]
    for line in lines:
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "error" in r:
            continue
        r["brands"] = brands_in(r.get("text", ""), r["category"])
        r["answering"] = len(r["brands"]) > 0
        r["unsupported"] = ([b for b in r["brands"] if not supported(b, r["category"], r)]
                            if r["condition"] == "search" else [])
        rows.append(r)
    # keep one record per trial key (latest wins)
    dedup = {}
    for r in rows:
        dedup[(r["category"], r["prompt_type"], r["engine"], r["model"], r["condition"], r["run"])] = r
    return list(dedup.values())


def vis_matrix(runs, brands):
    """runs: list of answering records -> (n_runs x n_brands) 0/1 matrix."""
    return np.array([[1 if b in r["brands"] else 0 for b in brands] for r in runs], dtype=float)


def tvd(a, b):
    pa = a / a.sum() if a.sum() else a
    pb = b / b.sum() if b.sum() else b
    return 0.5 * np.abs(pa - pb).sum()


def perm_tvd_floor(X, Y, iters=1000):
    Z = np.vstack([X, Y]); n = len(X); out = []
    for _ in range(iters):
        idx = RNG.permutation(len(Z))
        out.append(tvd(Z[idx[:n]].mean(0), Z[idx[n:]].mean(0)))
    return float(np.percentile(out, 95))


def diff_stats(x, y, iters=2000):
    """x, y: 0/1 vectors (memory, search). Returns lift, CI, permutation p."""
    obs = y.mean() - x.mean()
    boots = [RNG.choice(y, len(y)).mean() - RNG.choice(x, len(x)).mean() for _ in range(iters)]
    z = np.concatenate([x, y]); n = len(x); ge = 0
    for _ in range(iters):
        idx = RNG.permutation(len(z))
        if abs(z[idx[n:]].mean() - z[idx[:n]].mean()) >= abs(obs) - 1e-12:
            ge += 1
    return obs, np.percentile(boots, 2.5), np.percentile(boots, 97.5), (ge + 1) / (iters + 1)


def bh(pvals):
    p = np.asarray(pvals); m = len(p)
    if m == 0:
        return p
    order = np.argsort(p); q = np.empty(m)
    prev = 1.0
    for rank, i in reversed(list(enumerate(order, start=1))):
        prev = min(prev, p[i] * m / rank); q[i] = prev
    return q


def bucket(m, s):
    if m >= STRONG and s >= STRONG:
        return "Anchored"
    if m < STRONG and s >= STRONG:
        return "Search-dependent"
    if m >= STRONG and s < STRONG:
        return "Displaced"
    return "Peripheral"


def main(*paths):
    import glob
    paths = paths or sorted(glob.glob(os.path.join(ROOT, "data", "runs*.jsonl")))
    rows = load(paths)
    df = pd.DataFrame(rows)
    cells = df.groupby(["category", "prompt_type", "engine", "condition"])
    meta = {
        "n_records": len(df),
        "collected_from": df["ts"].min(), "collected_to": df["ts"].max(),
        "models": df.groupby("engine")["model_returned"].agg(lambda s: sorted(set(map(str, s)))).to_dict(),
        "answer_rate": {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": round(100 * g["answering"].mean(), 1)
                        for k, g in cells},
        "search_rate": {f"{k[0]}|{k[1]}|{k[2]}": round(100 * g["searched"].mean(), 1)
                        for k, g in df[df.condition == "search"].groupby(["category", "prompt_type", "engine"])},
        "runs_per_cell": {f"{k[0]}|{k[1]}|{k[2]}|{k[3]}": int(len(g)) for k, g in cells},
    }

    brand_rows, cell_rows = [], []
    for (cat, ptype, eng), g in df.groupby(["category", "prompt_type", "engine"]):
        brands = list(CATEGORIES[cat]["brands"])
        mem = [r for r in g[g.condition == "memory"].to_dict("records") if r["answering"]]
        sea = [r for r in g[g.condition == "search"].to_dict("records") if r["answering"]]
        if not mem or not sea:
            continue
        X, Y = vis_matrix(mem, brands), vis_matrix(sea, brands)
        stats = [diff_stats(X[:, j], Y[:, j]) for j in range(len(brands))]
        q = bh([s[3] for s in stats])
        for j, b in enumerate(brands):
            m, s = 100 * X[:, j].mean(), 100 * Y[:, j].mean()
            if m == 0 and s == 0:
                continue
            named = [r for r in sea if b in r["brands"]]
            uns = [r for r in named if b in r["unsupported"]]
            lift, lo, hi, p = stats[j]
            brand_rows.append(dict(
                category=cat, prompt_type=ptype, engine=eng, brand=b,
                memory=round(m, 1), search=round(s, 1), lift=round(100 * lift, 1),
                lift_lo=round(100 * lo, 1), lift_hi=round(100 * hi, 1),
                q=round(float(q[j]), 4), significant=bool(q[j] <= 0.05),
                bucket=bucket(m, s),
                unsupported_share=round(100 * len(uns) / len(named), 1) if named else None,
                n_memory=len(mem), n_search=len(sea)))
        d = tvd(X.mean(0), Y.mean(0))
        cell_rows.append(dict(category=cat, prompt_type=ptype, engine=eng,
                              tvd_memory_search=round(d, 3),
                              noise_floor=round(perm_tvd_floor(X, Y), 3),
                              spearman=round(pd.Series(X.mean(0)).corr(pd.Series(Y.mean(0)), method="spearman"), 3),
                              n_memory=len(mem), n_search=len(sea)))

    B = pd.DataFrame(brand_rows)
    C = pd.DataFrame(cell_rows)

    # cross-engine agreement: does memory or search disagree more across engines?
    # raw visibility per (cat, prompt, engine, condition), answering runs only
    V = {}
    for (cat, ptype, eng, cond), g in df[df.answering].groupby(["category", "prompt_type", "engine", "condition"]):
        brands = list(CATEGORIES[cat]["brands"])
        V[(cat, ptype, eng, cond)] = pd.Series(100 * vis_matrix(g.to_dict("records"), brands).mean(0), index=brands)
    both = sorted({e for (c, p, e, k) in V if k == "search"})
    cross = []
    for cat in CATEGORIES:
        for ptype in ["broad", "situational"]:
            for cond, engs, tag in [("memory", both, "memory"), ("search", both, "search"),
                                    ("memory", sorted({e for (c, p, e, k) in V if k == "memory"}), "memory_all")]:
                cols = [V[(cat, ptype, e, cond)] for e in engs if (cat, ptype, e, cond) in V]
                if len(cols) < 2:
                    continue
                piv = pd.concat(cols, axis=1)
                piv = piv[(piv.max(axis=1) > 0)]
                rng = piv.max(axis=1) - piv.min(axis=1)
                cross.append(dict(category=cat, prompt_type=ptype, condition=tag, engines=len(cols),
                                  mean_range=round(rng.mean(), 1),
                                  brands_50pt=int((rng >= 50).sum()), n_brands=int(len(rng))))
    vis_rows = [dict(category=c, prompt_type=p, engine=e, condition=k, brand=b, visibility=round(v, 1))
                for (c, p, e, k), ser in V.items() for b, v in ser.items() if v > 0]
    X_ = pd.DataFrame(cross)

    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    B.to_csv(os.path.join(ROOT, "data", "brand_results.csv"), index=False)
    C.to_csv(os.path.join(ROOT, "data", "cell_results.csv"), index=False)
    X_.to_csv(os.path.join(ROOT, "data", "cross_engine.csv"), index=False)
    pd.DataFrame(vis_rows).to_csv(os.path.join(ROOT, "data", "visibility_long.csv"), index=False)
    out = dict(meta=meta, brands=brand_rows, cells=cell_rows, cross_engine=cross, visibility=vis_rows,
               categories={k: {"label": v["label"], "prompts": v["prompts"]} for k, v in CATEGORIES.items()},
               engines={k: v["label"] for k, v in ENGINES.items()})
    json.dump(out, open(os.path.join(ROOT, "data", "results.json"), "w"), indent=1, default=str)
    print(f"{len(df)} records, {len(B)} brand rows, {len(C)} cells")
    return out


if __name__ == "__main__":
    main(*sys.argv[1:])
