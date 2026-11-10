"""Smoke test: list candidate models per provider, then one memory and one
search call per engine on a single prompt. Prints what came back so request
shapes and model IDs can be confirmed before the full run."""
import asyncio, os, sys, json
import httpx

sys.path.insert(0, os.path.dirname(__file__))
from config import ENGINES, CATEGORIES
from engines import CALLERS
from analyze import brands_in


async def models(client):
    out = {}
    try:
        r = await client.get("https://api.openai.com/v1/models",
                             headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
        out["openai"] = sorted(m["id"] for m in r.json().get("data", []) if m["id"].startswith(("gpt-5", "gpt-4.1", "o")))[-25:]
    except Exception as e:
        out["openai"] = repr(e)
    try:
        r = await client.get("https://api.anthropic.com/v1/models?limit=50",
                             headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"})
        out["anthropic"] = [m["id"] for m in r.json().get("data", [])]
    except Exception as e:
        out["anthropic"] = repr(e)
    try:
        r = await client.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
                             headers={"x-goog-api-key": os.environ["GOOGLE_API_KEY"]})
        out["google"] = [m["name"].split("/")[-1] for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])]
    except Exception as e:
        out["google"] = repr(e)
    return out


async def main():
    async with httpx.AsyncClient(timeout=180) as client:
        print(json.dumps(await models(client), indent=1))
        prompt = CATEGORIES["meal_kits"]["prompts"]["broad"]
        for eng, cfg in ENGINES.items():
            for search in (False, True):
                try:
                    r = await CALLERS[eng](client, cfg["model"], prompt, search)
                    print(f"\n== {eng} {cfg['model']} search={search} returned={r.get('model_returned')}")
                    print("searched:", r["searched"], "| queries:", r["queries"][:3], "| citations:", len(r["citations"]))
                    print("brands:", brands_in(r["text"], "meal_kits"))
                    print(r["text"][:300].replace("\n", " "))
                except httpx.HTTPStatusError as e:
                    print(f"\n== {eng} search={search} HTTP {e.response.status_code}: {e.response.text[:500]}")
                except Exception as e:
                    print(f"\n== {eng} search={search} ERROR {e!r}")


asyncio.run(main())
