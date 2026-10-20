"""Fake OpenAI-compatible model endpoint that injects one kind of fault (E1).

Speaks Chat Completions (/v1/chat/completions) and Responses (/v1/responses), streaming and not.
No real model, no real key: every answer is scripted.

usage: python fault_server.py PORT MODE LOGFILE

Modes (the fault is applied to EVERY request it targets, so retries are counted until the client gives up):
  ok                  no fault: first request -> call the counter tool, request with its result -> "Done."
  429                 429, Retry-After: 1, code rate_limit_exceeded
  429-hard            429, Retry-After: 3600, code insufficient_quota
  429-neutral-body    429, Retry-After: 1, body text without "429" / "rate limit" / "rate_limit" / "too many requests"
  500-neutral         500, "upstream error"
  500-ratelimit-text  500 whose message says "Rate limit reached"
  500-text-429        500, unrelated error whose text contains "429" (request id and "14290 tokens")
  timeout             accept and read the request, never answer (the connection is held until the client closes it)
  drop                200, then the connection closes mid-body (mid-stream when streaming). Streaming replies here are
                      close-delimited (no Content-Length, no chunked framing), so at the HTTP layer EOF is a legal end
                      of body and only the missing finish_reason / [DONE] / response.completed shows the truncation.
  drop-chunked        as drop, but the stream uses Transfer-Encoding: chunked (as real API servers do) and the
                      connection closes without the terminating zero-length chunk, which HTTP clients can detect
  after-tool-500      like ok, but every request carrying the tool result gets 500-neutral
  after-tool-drop     like ok, but every request carrying the tool result gets drop
  after-tool-drop-chunked  like ok, but every request carrying the tool result gets drop-chunked

A request "carries the tool result" when its raw body contains the marker COUNTER_OK that the counter tool
returns; this works whatever role or item type a framework uses for tool output.

One JSON line per request: t (s since server start), path, scenario, action, retry headers
(x-stainless-retry-count, x-stainless-timeout, retry-after* sent by the client, user-agent), has_tool_result,
stream, body_sha (sha256 of the body minus volatile fields, so identical retries share it), n_items.
For `timeout`, a second line records when the client closed the held connection."""
import hashlib, json, select, socket, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, MODE, LOGFILE = int(sys.argv[1]), sys.argv[2], sys.argv[3]
LOG = open(LOGFILE, "a")
T0 = time.time()
MARK = b"COUNTER_OK"
MODEL = "fake-model"

ERRORS = {
    "429": (429, "1", {"message": "Rate limit reached for requests", "type": "requests", "code": "rate_limit_exceeded"}),
    "429-hard": (429, "3600", {"message": "You exceeded your current quota, please check your plan and billing details.",
                               "type": "insufficient_quota", "code": "insufficient_quota"}),
    "429-neutral-body": (429, "1", {"message": "Slow down, please.", "type": "requests", "code": "slow_down"}),
    "500-neutral": (500, None, {"message": "upstream error", "type": "server_error", "code": "server_error"}),
    "500-ratelimit-text": (500, None, {"message": "Rate limit reached for requests", "type": "server_error", "code": "server_error"}),
    "500-text-429": (500, None, {"message": "Internal error on request req_4291ab: prompt is 14290 tokens",
                                 "type": "server_error", "code": "server_error"}),
}
ERRORS["after-tool-500"] = ERRORS["500-neutral"]


def log(rec):
    rec = dict({"t": round(time.time() - T0, 3)}, **rec)
    LOG.write(json.dumps(rec) + "\n")
    LOG.flush()


def body_sha(req):
    r = {k: v for k, v in req.items() if k not in ("user", "metadata", "store")}
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:12]


def tool_name(req):
    """The name the client gave the counter tool (frameworks may rename it)."""
    for t in req.get("tools", []) or []:
        n = t.get("name") or t.get("function", {}).get("name") or ""
        if "counter" in n.lower():
            return n
    return None


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_GET(self):
        self._json(200, {"object": "list", "data": [{"id": MODEL, "object": "model"}]})

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(n) if n else b""
        try:
            req = json.loads(raw or b"{}")
        except ValueError:
            req = {}
        has_result = MARK in raw
        responses = self.path.rstrip("/").endswith("/responses")
        stream = bool(req.get("stream"))
        if MODE in ("ok", "after-tool-500", "after-tool-drop", "after-tool-drop-chunked"):
            if has_result:
                action = {"ok": "text", "after-tool-500": "after-tool-500", "after-tool-drop": "drop",
                          "after-tool-drop-chunked": "drop-chunked"}[MODE]
            else:
                action = "tool_call"
        else:
            action = MODE
        h = self.headers
        log({"path": self.path, "scenario": MODE, "action": action, "has_tool_result": has_result, "stream": stream,
             "retry_count_hdr": h.get("x-stainless-retry-count"), "timeout_hdr": h.get("x-stainless-timeout"),
             "user_agent": h.get("user-agent"), "body_sha": body_sha(req),
             "n_items": len(req.get("messages") or req.get("input") or []) if isinstance(req.get("messages") or req.get("input"), list) else 1,
             "tools_offered": [t.get("name") or t.get("function", {}).get("name") for t in req.get("tools", []) or []]})
        try:
            if action in ERRORS:
                code, ra, err = ERRORS[action]
                return self._json(code, {"error": dict(err, param=None)}, {"Retry-After": ra} if ra else {})
            if action == "timeout":
                return self._hold()
            if action in ("drop", "drop-chunked"):
                return self._drop(stream, responses, chunked=action == "drop-chunked")
            name = tool_name(req)
            if action == "tool_call" and name is None:
                # client offered no native tools: answer in ReAct text so text-protocol agents can still act
                return self._reply(stream, responses, text="Thought: I should call the tool.\nAction: counter\nAction Input: {}")
            if action == "tool_call":
                return self._reply(stream, responses, call=name)
            if "final_answer" in [t.get("name") or t.get("function", {}).get("name") for t in req.get("tools", []) or []]:
                # smolagents ToolCallingAgent only stops on its final_answer tool
                return self._reply(stream, responses, call="final_answer", args='{"answer": "Done."}')
            if not req.get("tools"):
                return self._reply(stream, responses, text="Thought: I now know the final answer\nFinal Answer: Done.")
            return self._reply(stream, responses, text="Done.")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # ---- faults ----
    def _hold(self):
        s = self.connection
        while True:
            r, _, _ = select.select([s], [], [], 5)
            if r:
                try:
                    d = s.recv(1024)
                except OSError:
                    d = b""
                if not d:
                    log({"path": self.path, "scenario": MODE, "event": "client_closed_held_connection"})
                    self.close_connection = True
                    return

    def _drop(self, stream, responses, chunked=False):
        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            if chunked:
                self.send_header("Transfer-Encoding", "chunked")
                self._chunked = True
            self.send_header("Connection", "close")
            self.end_headers()
            if responses:
                self._sse({"type": "response.created", "response": {"id": "resp_d", "object": "response", "model": MODEL,
                                                                     "status": "in_progress", "output": []}}, "response.created")
            else:
                self._sse(self._chunk({"role": "assistant", "content": "Do"}))
        else:
            raw = json.dumps(self._chat_body(text="Done.") if not responses else self._resp_body(text="Done.")).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw[: len(raw) // 2])
            self.wfile.flush()
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.close_connection = True

    # ---- normal replies ----
    def _json(self, code, obj, extra=None):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(raw)

    def _sse(self, obj, event=None):
        data = (f"event: {event}\n" if event else "") + "data: " + (obj if isinstance(obj, str) else json.dumps(obj)) + "\n\n"
        if getattr(self, "_chunked", False):
            b = data.encode()
            self.wfile.write(f"{len(b):x}\r\n".encode() + b + b"\r\n")
        else:
            self.wfile.write(data.encode())
        self.wfile.flush()

    def _chunk(self, delta, fin=None, usage=None):
        c = {"id": "c1", "object": "chat.completion.chunk", "created": int(time.time()), "model": MODEL,
             "choices": [{"index": 0, "delta": delta, "finish_reason": fin}]}
        if usage:
            c["usage"] = usage
        return c

    def _chat_body(self, text=None, call=None, args="{}"):
        msg = {"role": "assistant", "content": text}
        if call:
            msg["tool_calls"] = [{"id": "call_1", "type": "function", "function": {"name": call, "arguments": args}}]
        return {"id": "c1", "object": "chat.completion", "created": int(time.time()), "model": MODEL,
                "choices": [{"index": 0, "finish_reason": "tool_calls" if call else "stop", "message": msg}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

    def _resp_item(self, text=None, call=None, args="{}"):
        if call:
            return {"id": "fc_1", "type": "function_call", "call_id": "call_1", "name": call, "arguments": args, "status": "completed"}
        return {"id": "msg_1", "type": "message", "role": "assistant", "status": "completed",
                "content": [{"type": "output_text", "text": text, "annotations": []}]}

    def _resp_body(self, text=None, call=None, args="{}"):
        return {"id": "resp_1", "object": "response", "created_at": int(time.time()), "model": MODEL, "status": "completed",
                "output": [self._resp_item(text, call, args)], "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15,
                "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 0}}}

    def _reply(self, stream, responses, text=None, call=None, args="{}"):
        if not stream:
            return self._json(200, self._resp_body(text, call, args) if responses else self._chat_body(text, call, args))
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        if responses:
            base = {"id": "resp_1", "object": "response", "created_at": int(time.time()), "model": MODEL, "status": "in_progress", "output": []}
            item = self._resp_item(text, call, args)
            self._sse({"type": "response.created", "response": base}, "response.created")
            self._sse({"type": "response.output_item.added", "output_index": 0, "item": dict(item, status="in_progress")},
                      "response.output_item.added")
            if not call:
                self._sse({"type": "response.output_text.delta", "item_id": "msg_1", "output_index": 0, "content_index": 0,
                           "delta": text}, "response.output_text.delta")
            self._sse({"type": "response.output_item.done", "output_index": 0, "item": item}, "response.output_item.done")
            done = self._resp_body(text, call, args)
            self._sse({"type": "response.completed", "response": done}, "response.completed")
        else:
            if call:
                self._sse(self._chunk({"role": "assistant", "content": None, "tool_calls": [
                    {"index": 0, "id": "call_1", "type": "function", "function": {"name": call, "arguments": args}}]}))
                self._sse(self._chunk({}, "tool_calls"))
            else:
                self._sse(self._chunk({"role": "assistant", "content": text}))
                self._sse(self._chunk({}, "stop"))
            self._sse(self._chunk({}, None, {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}) | {"choices": []})
            self._sse("[DONE]")
        self.close_connection = True


if __name__ == "__main__":
    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
