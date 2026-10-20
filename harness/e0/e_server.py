"""A fake model endpoint whose first reply is a tool call with its arguments cut off.

Speaks OpenAI Chat Completions and OpenAI Responses (SSE). The first request in a run gets a
`write_file` (or, for Codex CLI, its exec_command tool) call whose JSON arguments stop
part-way through the `content` string. How the reply ends is the scenario:

  complete  the arguments are whole and the reply ends normally (the test can see execution)
  length    the reply ends normally but says the output cap was hit
            (chat: finish_reason "length"; responses: response.incomplete, max_output_tokens)
  drop      the connection closes mid-arguments, with no finish event at all

Every later request gets a one-word text answer, so a client that executed the call can finish.
Per request it logs the tools the client offered, whether the request carries a tool result, and
that result's text, so execution can be read from the wire without trusting the client.

usage: python cut_server.py PORT SCENARIO LOGFILE [TOOL]
TOOL is the name of the client's file-writing tool (default write_file); "codex" uses Codex's exec_command."""
import json, sys, socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT, SCENARIO, LOGFILE = int(sys.argv[1]), sys.argv[2], sys.argv[3]
TOOL = sys.argv[4] if len(sys.argv) > 4 else "write_file"
LOG = open(LOGFILE, "a")

LINES = [f"line {i:02d} of 40\n" for i in range(1, 41)]
FULL_CONTENT = "".join(LINES)                      # what the model "meant" to write: 40 lines
CUT_AT = FULL_CONTENT.index("line 17 of 40") + 7   # cut inside line 17, after "line 17"


def full_args():
    if TOOL == "codex":
        script = "printf '" + FULL_CONTENT.replace("\n", "\\n") + "' > notes.txt"
        return json.dumps({"cmd": script})
    return json.dumps({"path": "notes.txt", "content": FULL_CONTENT})


def cut_args():
    a = full_args()
    if TOOL == "codex":
        marker = "line 17 of 40"
        i = a.index(marker) + 7
        return a[:i]
    # cut inside the content string, at the same place in the text
    i = a.index("line 17 of 40") + 7
    return a[:i]


def pieces(s, n=60):
    return [s[i:i + n] for i in range(0, len(s), n)]


def tool_result_in(req):
    """Return (has_result, text) for the tool output a client sent back, on either wire."""
    for m in req.get("messages", []) or []:
        c = m.get("content")
        t = c if isinstance(c, str) else json.dumps(c)
        if m.get("role") != "tool" and t and "wrote 560 chars" in t:
            return True, t[-200:]
    for m in req.get("messages", []) or []:
        if m.get("role") == "tool":
            c = m.get("content")
            return True, c if isinstance(c, str) else json.dumps(c)
    inp = req.get("input")
    if isinstance(inp, list):
        for it in inp:
            if isinstance(it, dict) and it.get("type") in ("function_call_output", "custom_tool_call_output"):
                o = it.get("output")
                return True, o if isinstance(o, str) else json.dumps(o)
    return False, None


def replayed_args(req):
    """The arguments of the tool call the client replays in its history, if any."""
    for m in req.get("messages", []) or []:
        for tc in (m.get("tool_calls") or []):
            return tc.get("function", {}).get("arguments")
    inp = req.get("input")
    if isinstance(inp, list):
        for it in inp:
            if isinstance(it, dict) and it.get("type") == "function_call":
                return it.get("arguments")
    return None


def tool_names(req):
    out = []
    for t in req.get("tools", []) or []:
        out.append(t.get("name") or t.get("function", {}).get("name") or t.get("type"))
    return out


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    first_done = False
    fails_left = 2

    def log_message(self, *a):
        pass

    def _sse(self, obj, event=None):
        data = (f"event: {event}\n" if event else "") + "data: " + (obj if isinstance(obj, str) else json.dumps(obj)) + "\n\n"
        self.wfile.write(data.encode())
        self.wfile.flush()

    def do_GET(self):
        body = json.dumps({"object": "list", "data": [{"id": "cut-model", "object": "model"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        if not self.path.startswith("/v1/"):
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers(); return
        has_result, result_text = tool_result_in(req)
        first = not H.first_done and not has_result and replayed_args(req) is None
        if SCENARIO.startswith("after-") and not has_result and H.first_done:
            first = True  # a client that starts over without the tool result gets the call again
        if SCENARIO.startswith("after-") and has_result and H.fails_left > 0:
            H.fails_left -= 1
            LOG.write(json.dumps({"path": self.path, "scenario": SCENARIO, "injected": SCENARIO, "has_tool_result": True}) + "\n"); LOG.flush()
            if SCENARIO == "after-500":
                body = b'{"error": {"message": "upstream error", "type": "server_error"}}'
                self.send_response(500); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
            self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Connection", "close"); self.end_headers()
            try:
                self.wfile.write(b'data: {"id":"c","object":"chat.completion.chunk","created":0,"model":"cut-model","choices":[{"index":0,"delta":{"role":"assistant","content":"Do"},"finish_reason":null}]}\n\n'); self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return
        rec = {"path": self.path, "scenario": SCENARIO, "first_request": first,
               "tools_offered": tool_names(req), "has_tool_result": has_result,
               "tool_result": (result_text or "")[:400] if has_result else None,
               "replayed_args_len": len(replayed_args(req)) if replayed_args(req) is not None else None,
               "stream": bool(req.get("stream"))}
        LOG.write(json.dumps(rec) + "\n"); LOG.flush()
        responses = self.path.rstrip("/").endswith("/responses")
        if not req.get("stream"):
            return self._plain(req, first, responses)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            if first:
                H.first_done = True
                args = full_args() if SCENARIO in ("complete", "after-500", "after-drop") else cut_args()
                (self._responses_call if responses else self._chat_call)(args)
            else:
                (self._responses_text if responses else self._chat_text)("Done.")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        if first and SCENARIO == "drop":
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    # ---- non-streaming replies ----
    def _plain(self, req, first, responses):
        name = "exec_command" if TOOL == "codex" else TOOL
        if first:
            H.first_done = True
            args = full_args() if SCENARIO != "length" else cut_args()
            if responses:
                st = "completed" if SCENARIO != "length" else "incomplete"
                item = {"id": "fc_1", "type": "function_call", "call_id": "call_1", "name": name, "arguments": args, "status": st}
                body = {"id": "resp_1", "object": "response", "model": "cut-model", "status": st, "output": [item],
                        "usage": {"input_tokens": 10, "output_tokens": 50, "total_tokens": 60}}
                if st == "incomplete":
                    body["incomplete_details"] = {"reason": "max_output_tokens"}
            else:
                body = {"id": "c1", "object": "chat.completion", "created": 0, "model": "cut-model",
                        "choices": [{"index": 0, "finish_reason": "tool_calls" if SCENARIO != "length" else "length",
                                     "message": {"role": "assistant", "content": None, "tool_calls": [
                                         {"id": "call_1", "type": "function", "function": {"name": name, "arguments": args}}]}}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}}
        else:
            if responses:
                body = {"id": "resp_2", "object": "response", "model": "cut-model", "status": "completed", "output": [
                    {"id": "msg_2", "type": "message", "role": "assistant", "status": "completed",
                     "content": [{"type": "output_text", "text": "Done.", "annotations": []}]}],
                    "usage": {"input_tokens": 10, "output_tokens": 1, "total_tokens": 11}}
            else:
                body = {"id": "c2", "object": "chat.completion", "created": 0, "model": "cut-model",
                        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "Done."}}],
                        "usage": {"prompt_tokens": 10, "completion_tokens": 1, "total_tokens": 11}}
        raw = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            if first and SCENARIO == "drop":
                # the body stops inside the arguments; the connection closes short of Content-Length
                self.wfile.write(raw[:raw.index(b"line 17 of 40") + 7]); self.wfile.flush()
                self.connection.shutdown(socket.SHUT_RDWR)
            else:
                self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    # ---- chat completions ----
    def _chunk(self, delta, fin=None):
        return {"id": "c1", "object": "chat.completion.chunk", "created": 0, "model": "cut-model",
                "choices": [{"index": 0, "delta": delta, "finish_reason": fin}]}

    def _chat_call(self, args):
        name = "exec_command" if TOOL == "codex" else TOOL
        self._sse(self._chunk({"role": "assistant", "content": None, "tool_calls": [
            {"index": 0, "id": "call_1", "type": "function", "function": {"name": name, "arguments": ""}}]}))
        for p in pieces(args):
            self._sse(self._chunk({"tool_calls": [{"index": 0, "function": {"arguments": p}}]}))
        if SCENARIO == "drop":
            return
        self._sse(self._chunk({}, "length" if SCENARIO == "length" else "tool_calls"))
        self._sse("[DONE]")

    def _chat_text(self, text):
        self._sse(self._chunk({"role": "assistant", "content": text}))
        self._sse(self._chunk({}, "stop"))
        self._sse("[DONE]")

    # ---- responses ----
    def _responses_call(self, args):
        name = "exec_command" if TOOL == "codex" else TOOL
        base = {"id": "resp_1", "object": "response", "model": "cut-model", "status": "in_progress", "output": []}
        item = {"id": "fc_1", "type": "function_call", "call_id": "call_1", "name": name, "arguments": "", "status": "in_progress"}
        self._sse({"type": "response.created", "response": base}, "response.created")
        self._sse({"type": "response.output_item.added", "output_index": 0, "item": item}, "response.output_item.added")
        for p in pieces(args):
            self._sse({"type": "response.function_call_arguments.delta", "item_id": "fc_1", "output_index": 0, "delta": p},
                      "response.function_call_arguments.delta")
        if SCENARIO == "drop":
            return
        usage = {"input_tokens": 10, "output_tokens": len(args) // 4, "total_tokens": 10 + len(args) // 4}
        if SCENARIO != "length":
            done = dict(item, arguments=args, status="completed")
            self._sse({"type": "response.function_call_arguments.done", "item_id": "fc_1", "output_index": 0, "arguments": args},
                      "response.function_call_arguments.done")
            self._sse({"type": "response.output_item.done", "output_index": 0, "item": done}, "response.output_item.done")
            self._sse({"type": "response.completed", "response": dict(base, status="completed", output=[done], usage=usage)},
                      "response.completed")
        else:  # length: the documented shape of a reply stopped by max_output_tokens
            done = dict(item, arguments=args, status="incomplete")
            self._sse({"type": "response.output_item.done", "output_index": 0, "item": done}, "response.output_item.done")
            self._sse({"type": "response.incomplete", "response": dict(
                base, status="incomplete", incomplete_details={"reason": "max_output_tokens"}, output=[done], usage=usage)},
                "response.incomplete")

    def _responses_text(self, text):
        base = {"id": "resp_2", "object": "response", "model": "cut-model", "status": "in_progress", "output": []}
        item = {"id": "msg_2", "type": "message", "role": "assistant", "status": "in_progress", "content": []}
        self._sse({"type": "response.created", "response": base}, "response.created")
        self._sse({"type": "response.output_item.added", "output_index": 0, "item": item}, "response.output_item.added")
        self._sse({"type": "response.content_part.added", "item_id": "msg_2", "output_index": 0, "content_index": 0,
                   "part": {"type": "output_text", "text": "", "annotations": []}}, "response.content_part.added")
        self._sse({"type": "response.output_text.delta", "item_id": "msg_2", "output_index": 0, "content_index": 0, "delta": text},
                  "response.output_text.delta")
        done = dict(item, status="completed", content=[{"type": "output_text", "text": text, "annotations": []}])
        self._sse({"type": "response.output_text.done", "item_id": "msg_2", "output_index": 0, "content_index": 0, "text": text},
                  "response.output_text.done")
        self._sse({"type": "response.output_item.done", "output_index": 0, "item": done}, "response.output_item.done")
        self._sse({"type": "response.completed", "response": dict(base, status="completed", output=[done],
                   usage={"input_tokens": 10, "output_tokens": 1, "total_tokens": 11})}, "response.completed")


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
