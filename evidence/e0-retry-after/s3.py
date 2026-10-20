import json,sys,time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
PORT=int(sys.argv[1]); LOG=open(sys.argv[2],"w"); T0=time.time()
class H(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.1"
    def log_message(self,*a): pass
    def do_POST(self):
        n=int(self.headers.get("Content-Length",0)); self.rfile.read(n)
        LOG.write(json.dumps({"t":round(time.time()-T0,2),"retry_count_hdr":self.headers.get("x-stainless-retry-count")})+"\n"); LOG.flush()
        b=b'{"error":{"message":"Rate limit reached","type":"requests","code":"rate_limit_exceeded"}}'
        self.send_response(429); self.send_header("Retry-After","3"); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
ThreadingHTTPServer(("127.0.0.1",PORT),H).serve_forever()
