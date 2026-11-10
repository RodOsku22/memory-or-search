"""Fill report/template.html with data/results.json and report/narrative.json.

narrative.json keys: lede, date, authors_note, results, implications, setup,
limits, future, footer (HTML strings), takeaways [{value,label}],
lens_default {category, brand}.
"""
import json, os, sys

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")

res = json.load(open(os.path.join(ROOT, "data", "results.json")))
nar = json.load(open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "narrative.json")))
tpl = open(os.path.join(HERE, "template.html")).read()

data = dict(brands=res["brands"], cells=res["cells"], cross_engine=res["cross_engine"],
            categories=res["categories"], engines=res["engines"],
            takeaways=nar.get("takeaways", []), lens_default=nar.get("lens_default"))
runs = sorted(set(res["meta"]["runs_per_cell"].values()))
nruns = "15&ndash;30"

out = tpl
for k, v in {
    "__LEDE__": nar["lede"], "__DATE__": nar["date"], "__NRUNS__": nruns,
    "__AUTHORS_NOTE__": nar["authors_note"], "__RESULTS__": nar["results"],
    "__IMPLICATIONS__": nar["implications"], "__SETUP__": nar["setup"],
    "__LIMITS__": nar["limits"], "__FUTURE__": nar["future"], "__FOOTER__": nar["footer"],
}.items():
    out = out.replace(k, v)
out = out.replace("__DATA__", json.dumps(data, default=str).replace("</", "<\\/"))
dst = os.path.join(HERE, "memory-or-search.html")
open(dst, "w").write(out)
print("wrote", dst, len(out), "bytes")
