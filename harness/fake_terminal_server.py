"""体检1 假服务器（v2）：按 #144745 真实场景发「terminal 工具调用」。

与 v1 的区别：工具名是真实的 terminal（agent 侧可见），正常回合发出的是
`echo hi >> <marker>` —— 可验证的副作用，用标记文件数行数。

用法: fake_terminal_server.py <port> <mode: never|once|always> <log> <marker> [cap]
- chat 1: mode=always/once -> 退化（无限空白参数）；never -> 正常调用
- chat >=2: 若请求里已含 tool 结果 -> 纯文本收尾；否则再发一次正常调用
"""
import json, os, socket, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1])
MODE = sys.argv[2]
LOG = sys.argv[3]
MARKER = sys.argv[4]
CAP = int(sys.argv[5]) if len(sys.argv) > 5 else 200_000
WS_CHUNK = 512

CMD = 'echo hi >> "%s"' % MARKER.replace("\\", "/")

lock = threading.Lock()
req_no = 0
chat_no = 0


def logrec(**kw):
    with lock:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(kw, ensure_ascii=False) + "\n")


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def setup(self):
        super().setup()
        try:
            self.connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)
        except Exception:
            pass

    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if "models" in self.path:
            return self._json(200, {"object": "list", "data": [{"id": "fake-model", "object": "model"}]})
        return self._json(404, {"error": "nope"})

    def do_POST(self):
        global req_no, chat_no
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode("utf-8", "replace")
        try:
            payload = json.loads(body or "{}")
        except Exception:
            payload = {}
        if "chat/completions" not in self.path:
            with lock:
                req_no += 1
                my = req_no
            logrec(req=my, path=self.path, kind="probe", chars=0)
            return self._json(200, {"ok": True})

        with lock:
            req_no += 1
            my = req_no
            chat_no += 1
            chat_my = chat_no

        msgs = payload.get("messages") or []
        has_tool_result = any(isinstance(m, dict) and m.get("role") == "tool" for m in msgs)
        tools = [((t.get("function") or {}).get("name")) for t in (payload.get("tools") or [])]
        streaming = bool(payload.get("stream"))
        degenerate = chat_my == 1 and MODE in ("once", "always") or (MODE == "always" and not has_tool_result)

        if not streaming:
            logrec(req=my, kind="nonstream", chat=chat_my, chars=0, has_tool_result=has_tool_result)
            return self._json(200, {"id": "c%d" % my, "object": "chat.completion", "created": 0,
                                    "model": "fake-model",
                                    "choices": [{"index": 0, "finish_reason": "stop",
                                                 "message": {"role": "assistant", "content": "Done"}}]})

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        sent = 0
        closed = False
        t0 = time.time()

        def emit(chunk_obj):
            nonlocal sent, closed
            data = "data: " + json.dumps(chunk_obj) + "\n\n"
            try:
                self.wfile.write(data.encode())
                self.wfile.flush()
                sent += len(data)
                return True
            except (BrokenPipeError, ConnectionResetError, OSError):
                closed = True
                return False

        def finish():
            try:
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except Exception:
                pass

        if has_tool_result:
            # 工具已经跑过一轮：给最终答复
            emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                  "choices": [{"index": 0, "delta": {"content": "Done"}, "finish_reason": None}]})
            emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                  "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
            finish()
            logrec(req=my, kind="final_text", chat=chat_my, chars=sent, closed_by_client=False,
                   elapsed=round(time.time() - t0, 2))
            return

        # 开一个 terminal 工具调用
        emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
              "choices": [{"index": 0, "delta": {"role": "assistant", "content": None,
                                                 "tool_calls": [{"index": 0, "id": "call_%d" % my,
                                                                 "type": "function",
                                                                 "function": {"name": "terminal", "arguments": ""}}]},
                           "finish_reason": None}]})

        if degenerate:
            # 参数从第一个字符起就是空白（复刻 #144745 报告的形态：NoJson / 全空白参数）
            block = " " * WS_CHUNK
            while sent < CAP and not closed:
                if not emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0,
                             "model": "fake-model",
                             "choices": [{"index": 0,
                                          "delta": {"tool_calls": [{"index": 0, "function": {"arguments": block}}]},
                                          "finish_reason": None}]}):
                    break
            if not closed:
                emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                      "choices": [{"index": 0, "delta": {}, "finish_reason": "length"}]})
                emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                      "choices": []})
                finish()
            logrec(req=my, kind="degenerate", chat=chat_my, chars=sent, closed_by_client=closed,
                   tools_exposed=tools, elapsed=round(time.time() - t0, 2))
        else:
            args = json.dumps({"command": CMD})
            emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                  "choices": [{"index": 0, "delta": {"tool_calls": [{"index": 0, "function": {"arguments": args}}]},
                               "finish_reason": None}]})
            emit({"id": "c%d" % my, "object": "chat.completion.chunk", "created": 0, "model": "fake-model",
                  "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}]})
            finish()
            logrec(req=my, kind="tool_call", chat=chat_my, chars=sent, closed_by_client=False,
                   tools_exposed=tools, elapsed=round(time.time() - t0, 2))


srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
srv.daemon_threads = True
print("listening %d mode=%s marker=%s" % (PORT, MODE, MARKER), flush=True)
srv.serve_forever()
