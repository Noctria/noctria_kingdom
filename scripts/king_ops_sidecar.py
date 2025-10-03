# scripts/king_ops_sidecar.py
# v1.7.3-ssefix3 — SSE安定化: CRLF終端/ヘッダ明示/非SSE行ラップ修正/圧縮無効化
#                   + [DONE]重複送出ガード + 接続失敗もSSEで返却
from __future__ import annotations
import os, json, time, uuid
from typing import AsyncIterator, Dict, Any, Optional, List
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
import httpx

APP_VERSION = "1.7.3-ssefix3"

# 共通定数（SSE改行用）
CRLF = b"\r\n"
CRLF2 = b"\r\n\r\n"

# ===== 環境設定 =====
CLOUD_ENABLED = os.getenv("CLOUD_ENABLED", "false").lower() == "true"
CLOUD_BASE_URL = os.getenv("OPENAI_API_BASE") or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
CLOUD_API_KEY = os.getenv("OPENAI_API_KEY", "")
# ※ デフォはそのまま。Ollama互換を使うなら環境変数で 11434/v1 を指定:
#    export LOCAL_OPENAI_BASE="http://127.0.0.1:11434/v1"
LOCAL_BASE_URL = os.getenv("LOCAL_OPENAI_BASE", "http://127.0.0.1:8003/v1")
LOCAL_TIMEOUT = float(os.getenv("LOCAL_HTTP_TIMEOUT", "300"))
CLOUD_TIMEOUT = float(os.getenv("CLOUD_HTTP_TIMEOUT", "300"))

MODEL_ALLOWLIST: List[str] = [
    m.strip() for m in os.getenv("MODEL_ALLOWLIST", "qwen2.5:3b-instruct-q4_K_M,gpt-4o-mini").split(",") if m.strip()
]
MAX_TOKENS_CAP = int(os.getenv("MAX_TOKENS_CAP", "4096"))
DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "512"))

KING_OPS_PATH = os.getenv("KING_OPS_PATH")  # e.g., docs/governance/king_ops_prompt.yaml

AUDIT_LOG_PATH = os.getenv("SIDE_CAR_AUDIT_LOG", "logs/sidecar_audit.jsonl")
os.makedirs(os.path.dirname(AUDIT_LOG_PATH) or ".", exist_ok=True)

app = FastAPI(title="Noctria KingOps Sidecar", version=APP_VERSION)


def _write_audit(entry: Dict[str, Any]) -> None:
    entry.setdefault("ts", time.time())
    try:
        with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _select_backend(route_hint: Optional[str]) -> Dict[str, Any]:
    if route_hint == "local" or not CLOUD_ENABLED:
        return {"kind": "local", "base": LOCAL_BASE_URL, "timeout": LOCAL_TIMEOUT, "headers": {}}
    if route_hint == "cloud" and CLOUD_ENABLED:
        return {
            "kind": "cloud",
            "base": CLOUD_BASE_URL,
            "timeout": CLOUD_TIMEOUT,
            "headers": {"Authorization": f"Bearer {CLOUD_API_KEY}"},
        }
    if CLOUD_ENABLED:
        return {
            "kind": "cloud",
            "base": CLOUD_BASE_URL,
            "timeout": CLOUD_TIMEOUT,
            "headers": {"Authorization": f"Bearer {CLOUD_API_KEY}"},
        }
    return {"kind": "local", "base": LOCAL_BASE_URL, "timeout": LOCAL_TIMEOUT, "headers": {}}


def _inject_system(messages: List[Dict[str, Any]], system_text: str) -> List[Dict[str, Any]]:
    out = messages[:]
    if out and out[0].get("role") == "system":
        out[0]["content"] = f"{system_text}\n\n{out[0].get('content','')}".strip()
        return out
    return [{"role": "system", "content": system_text}] + out


def _build_system_from_lang(lang: Optional[str]) -> str:
    if not lang:
        return "Respond briefly and pragmatically in English."
    l = lang.lower()
    if l == "ja":
        return "あなたは簡潔・実務優先で日本語で回答します。"
    if l in ("zh", "zh-cn", "zh-tw"):
        return "请用简洁、务实的中文回答。"
    return "Respond briefly and pragmatically in English."


def _cap_tokens(body: Dict[str, Any]) -> None:
    if "max_tokens" not in body:
        body["max_tokens"] = DEFAULT_MAX_TOKENS
    else:
        try:
            body["max_tokens"] = min(int(body["max_tokens"]), MAX_TOKENS_CAP)
        except Exception:
            body["max_tokens"] = DEFAULT_MAX_TOKENS


def _ensure_model_allowed(model: str) -> None:
    if MODEL_ALLOWLIST and model not in MODEL_ALLOWLIST:
        raise HTTPException(status_code=400, detail=f"model '{model}' not in allowlist")


async def _sse_proxy(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    json_body: Dict[str, Any],
    headers: Dict[str, str],
    audit_base: Dict[str, Any],
) -> AsyncIterator[bytes]:
    """
    上流がSSEでも非SSE(chunked)でも安定してSSEで中継。
    - 非SSEは行バッファで安全にラップし `data: ...\\r\\n\\r\\n` で送出
    - 最後に必ず `data: [DONE]\\r\\n\\r\\n`（※上流が送っていたら二重送出しない）
    - client はここで close する（StreamingResponse が終了するまで保持）
    """
    start = time.time()
    sent_done = False  # ← [DONE]重複防止フラグ

    # 上流にSSE期待を伝える（無視されてもOK） & 圧縮無効で安定化
    hdrs = {
        **headers,
        "Accept": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
    }
    try:
        async with client.stream(method, url, json=json_body, headers=hdrs, timeout=client.timeout) as r:
            r.raise_for_status()
            is_event_stream = r.headers.get("content-type", "").startswith("text/event-stream")
            if is_event_stream:
                # 上流がSSEなら透過
                async for chunk in r.aiter_bytes():
                    if chunk:
                        if b"[DONE]" in chunk:
                            sent_done = True
                        yield chunk
            else:
                # 非SSE → 行バッファでSSEラップ
                buf = b""
                async for chunk in r.aiter_bytes():
                    if not chunk:
                        continue
                    buf += chunk
                    # \n / \r\n で分割（keepends=False で終端改行は除去）
                    *full_lines, buf = buf.splitlines(keepends=False)
                    for line in full_lines:
                        line = line.strip()
                        if not line:
                            continue
                        yield b"data: " + line + CRLF2
                if buf.strip():
                    yield b"data: " + buf.strip() + CRLF2

            # 明示終端（上流が送っていない場合のみ）
            if not sent_done:
                yield b"data: [DONE]" + CRLF2

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        # 接続・解決失敗含むエラーをSSEで返す
        err = {"error": {"message": str(e), "type": e.__class__.__name__}}
        yield b"data: " + json.dumps(err).encode("utf-8") + CRLF2
        yield b"data: [DONE]" + CRLF2
    finally:
        try:
            _write_audit({**audit_base, "latency_ms": int((time.time() - start) * 1000), "phase": "sse_proxy_done"})
        finally:
            # ここで client を確実にクローズ（重要）
            await client.aclose()


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    x_noctria_system: Optional[str] = Header(default=None, alias="X-Noctria-System"),
    x_reply_lang: Optional[str] = Header(default=None, alias="X-Reply-Lang"),
    x_route: Optional[str] = Header(default=None, alias="X-Route"),
):
    payload = await request.json()
    model = payload.get("model") or ""
    stream = bool(payload.get("stream", False))
    messages = payload.get("messages") or []
    _ensure_model_allowed(model)
    _cap_tokens(payload)

    # SYSTEM注入制御
    inject_on = (x_noctria_system or "").lower() != "off"
    if inject_on and KING_OPS_PATH and os.path.exists(KING_OPS_PATH):
        with open(KING_OPS_PATH, "r", encoding="utf-8") as f:
            sys_body = f.read()
        # 言語指示を常に先頭へ
        lang_text = _build_system_from_lang(x_reply_lang) if x_reply_lang else _build_system_from_lang("en")
        sys_text = f"{lang_text}\n\n【KING OPS 指示書】\n{sys_body}"
        payload["messages"] = _inject_system(messages, sys_text)
    else:
        if x_reply_lang:
            payload["messages"] = _inject_system(messages, _build_system_from_lang(x_reply_lang))
        else:
            payload["messages"] = messages

    backend = _select_backend((x_route or "").lower())
    target_url = f"{backend['base']}/chat/completions"
    audit_id = str(uuid.uuid4())
    audit_base = {
        "id": audit_id,
        "endpoint": "/v1/chat/completions",
        "model": model,
        "backend": backend["kind"],
        "stream": stream,
        "version": APP_VERSION,
    }

    headers = {"Content-Type": "application/json", **backend["headers"]}
    headers.update(
        {
            "X-Noctria-Stable": "1",
            "X-Noctria-Client": f"kingops-sidecar/{APP_VERSION}",
        }
    )

    timeout = httpx.Timeout(backend["timeout"])

    if stream:
        # 重要: ここでは contextmanager を使わず、generator 側で close する
        client = httpx.AsyncClient(timeout=timeout)
        gen = _sse_proxy(client, "POST", target_url, payload, headers, audit_base)
        # ★ SSE向けヘッダを明示
        resp_headers = {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
        return StreamingResponse(gen, media_type="text/event-stream", headers=resp_headers)
    else:
        async with httpx.AsyncClient(timeout=timeout) as client:
            start = time.time()
            try:
                r = await client.post(target_url, json=payload, headers=headers)
                r.raise_for_status()
                data = r.json()
                _write_audit({**audit_base, "latency_ms": int((time.time() - start) * 1000), "phase": "nonstream_done"})
                return JSONResponse(data)
            except httpx.HTTPStatusError as e:
                _write_audit({**audit_base, "phase": "error", "status": e.response.status_code})
                return JSONResponse({"error": {"message": e.response.text}}, status_code=e.response.status_code)


@app.get("/v1/models")
async def list_models(x_route: Optional[str] = Header(default=None, alias="X-Route")):
    backend = _select_backend((x_route or "").lower())
    async with httpx.AsyncClient(timeout=httpx.Timeout(backend["timeout"])) as client:
        try:
            r = await client.get(f"{backend['base']}/models", headers=backend["headers"])
            r.raise_for_status()
            return JSONResponse(r.json())
        except Exception as e:
            return JSONResponse({"data": [], "warning": f"models fetch failed: {e}"})


@app.get("/healthz")
def healthz():
    return {"ok": True, "version": APP_VERSION}
