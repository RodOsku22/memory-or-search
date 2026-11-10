"""One call per engine, with web search off ("memory") or on ("search").

Each call returns a dict: text, citations [{url,title}], queries [str],
searched (bool), plus raw usage. Provider docs change; adapters are kept small
so the pilot can confirm request shapes before the full run.
"""
import os
import httpx

TIMEOUT = httpx.Timeout(180.0, connect=20.0)
OPENAI_EFFORT = os.environ.get("OPENAI_EFFORT", "none")
OPENAI_CONTEXT = os.environ.get("OPENAI_CONTEXT", "low")


def _key(name):
    v = os.environ.get(name)
    if not v:
        raise RuntimeError(f"missing {name}")
    return v


async def call_openai(client, model, prompt, search):
    # reasoning off approximates ChatGPT "Instant", the surface Petra Labs measured
    body = {"model": model, "input": prompt, "reasoning": {"effort": OPENAI_EFFORT}}
    if search:
        body["tools"] = [{"type": "web_search", "search_context_size": OPENAI_CONTEXT}]
        body["tool_choice"] = "required"
    r = await client.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": f"Bearer {_key('OPENAI_API_KEY')}"},
        json=body,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    j = r.json()
    text, cites, queries = [], [], []
    for item in j.get("output", []):
        t = item.get("type")
        if t == "web_search_call":
            act = item.get("action") or {}
            q = act.get("query")
            if q:
                queries.append(q)
            for qq in act.get("queries") or []:
                queries.append(qq)
        elif t == "message":
            for c in item.get("content", []):
                if c.get("type") == "output_text":
                    text.append(c.get("text", ""))
                    for a in c.get("annotations", []) or []:
                        if a.get("type") == "url_citation":
                            cites.append({"url": a.get("url"), "title": a.get("title")})
    searched = any(i.get("type") == "web_search_call" for i in j.get("output", []))
    return {"text": "\n".join(text), "citations": cites, "queries": queries,
            "searched": searched, "model_returned": j.get("model"), "usage": j.get("usage")}


ANTHROPIC_SEARCH_TOOL = os.environ.get("ANTHROPIC_SEARCH_TOOL", "web_search_20250305")


async def call_anthropic(client, model, prompt, search):
    body = {"model": model, "max_tokens": 2500,
            "messages": [{"role": "user", "content": prompt}]}
    if search:
        body["tools"] = [{"type": ANTHROPIC_SEARCH_TOOL, "name": "web_search", "max_uses": 3}]
    r = await client.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": _key("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"},
        json=body,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    j = r.json()
    text, cites, queries, interim = [], [], [], []
    for b in j.get("content", []):
        t = b.get("type")
        if t == "text":
            text.append(b.get("text", ""))
            for c in b.get("citations") or []:
                if c.get("url"):
                    cites.append({"url": c.get("url"), "title": c.get("title")})
        elif t == "server_tool_use":
            q = (b.get("input") or {}).get("query")
            if q:
                queries.append(q)
        elif t == "web_search_tool_result":
            for res in b.get("content") or []:
                if isinstance(res, dict) and res.get("url"):
                    interim.append({"url": res.get("url"), "title": res.get("title")})
    return {"text": "".join(text), "citations": cites, "interim": interim, "queries": queries,
            "searched": bool(queries), "model_returned": j.get("model"), "usage": j.get("usage")}


async def call_google(client, model, prompt, search):
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    if search:
        body["tools"] = [{"google_search": {}}]
    r = await client.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": _key("GOOGLE_API_KEY")},
        json=body,
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    j = r.json()
    cand = (j.get("candidates") or [{}])[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    gm = cand.get("groundingMetadata") or {}
    queries = gm.get("webSearchQueries") or []
    cites = [{"url": (c.get("web") or {}).get("uri"), "title": (c.get("web") or {}).get("title")}
             for c in gm.get("groundingChunks") or [] if c.get("web")]
    return {"text": text, "citations": cites, "queries": queries,
            "searched": bool(queries or cites), "model_returned": j.get("modelVersion"),
            "usage": j.get("usageMetadata"), "finish": cand.get("finishReason")}


CALLERS = {"openai": call_openai, "anthropic": call_anthropic, "google": call_google}
