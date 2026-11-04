#!/usr/bin/env python3
"""Run the four long-running scenarios against any service published on Varis.

The question this answers is narrow and concrete: when a call takes longer than
the request window, does the platform hand back a handle you can collect from, or
does it fail in a way that invites a retry -- and if an agent does retry, does the
service run and bill twice?

Nothing here is specific to our service. Point it at yours.

    export VARIS_AGENT_KEY=var_ak_...        # agent key, never committed
    export VARIS_SERVICE_ID=var_srvc_...
    export DELAY_SECONDS=35                  # must exceed the ~30s window
    python run_varis.py --out ./varis-run

Writes `varis-run/http.json` and a line per call to stdout. Compare against your
service's own log and your account ledger; the client's view alone is not enough
to tell an execution from a replay.

Exit codes: 0 all observations collected, 2 a scenario failed, 3 configuration.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

INVOKE = "https://api.usevaris.com/v1/invocations"
LOOKUP = "https://api.usevaris.com/v1/invocations/%s"
POLL_INTERVAL = 5.0
POLL_DEADLINE = 120.0


def call(key, body, idempotency_key=None, timeout=180):
    req = urllib.request.Request(
        INVOKE, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + key,
                 "Content-Type": "application/json",
                 "Accept": "application/json"})
    if idempotency_key:
        req.add_header("Idempotency-Key", idempotency_key)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode("utf-8", "replace")
            return {"http_status": r.status, "headers": dict(r.headers),
                    "raw": raw, "elapsed_s": round(time.time() - t0, 3)}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        return {"http_status": e.code, "headers": dict(e.headers or {}),
                "raw": raw, "elapsed_s": round(time.time() - t0, 3)}
    except Exception as e:  # noqa: BLE001
        return {"http_status": None, "headers": {}, "raw": "",
                "error": repr(e), "elapsed_s": round(time.time() - t0, 3)}


def body_of(rec):
    try:
        return json.loads(rec["raw"]) if rec.get("raw") else {}
    except Exception:  # noqa: BLE001
        return {}


def lookup(key, invocation_id):
    req = urllib.request.Request(LOOKUP % invocation_id, method="GET",
                                 headers={"Authorization": "Bearer " + key,
                                          "Accept": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read().decode("utf-8", "replace")),
                    "elapsed_s": round(time.time() - t0, 3)}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            b = json.loads(raw)
        except Exception:  # noqa: BLE001
            b = {"raw": raw[:400]}
        return {"http_status": e.code, "body": b,
                "elapsed_s": round(time.time() - t0, 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="varis-run")
    args = ap.parse_args()

    key = os.environ.get("VARIS_AGENT_KEY")
    svc = os.environ.get("VARIS_SERVICE_ID")
    delay = int(os.environ.get("DELAY_SECONDS", "35"))
    if not key or not svc:
        print("set VARIS_AGENT_KEY and VARIS_SERVICE_ID"); return 3

    os.makedirs(args.out, exist_ok=True)
    log = {"service_id": svc, "delay_seconds": delay,
           "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "s1": [], "s1b": [], "s2": []}

    # S1 -- a slow call, twice
    for i in (1, 2):
        # The key is sent on the FIRST call so that S1b can replay against it.
        # Retrying without an idempotency key is not a same-key retry -- it is a
        # new invocation that runs and bills again. Getting this wrong is how a
        # "replay" test silently charges you twice.
        idem = "varis-s1-%d" % i
        rec = call(key, {"service_id": svc,
                         "input": {"delay_seconds": delay,
                                   "run_tag": "varis-s1-%d" % i}},
                   idempotency_key=idem)
        b = body_of(rec)
        ent = {"index": i, "http_status": rec["http_status"],
               "elapsed_s": rec["elapsed_s"],
               "status": b.get("status"),
               "invocation_id": b.get("invocation_id"),
               "request_id": b.get("request_id"),
               "body_keys": sorted(b.keys()),
               "body": b}
        if ent["invocation_id"]:
            deadline = time.time() + POLL_DEADLINE
            ent["lookups"] = []
            while time.time() < deadline:
                time.sleep(POLL_INTERVAL)
                lk = lookup(key, ent["invocation_id"])
                ent["lookups"].append({"http_status": lk["http_status"],
                                       "elapsed_s": lk["elapsed_s"],
                                       "status": lk["body"].get("status"),
                                       "has_output": bool(lk["body"].get("output"))})
                if lk["body"].get("status") in ("success", "succeeded",
                                                "completed", "failed"):
                    ent["final"] = ent["lookups"][-1]
                    ent["final_body"] = lk["body"]
                    break
        log["s1"].append(ent)
        print("[S1.%d] http=%s in %.1fs status=%s invocation=%s final=%s" % (
            i, ent["http_status"], ent["elapsed_s"], ent["status"],
            ent["invocation_id"], (ent.get("final") or {}).get("status")))

    # S1b -- retry with the same key, twice
    for i in (1, 2):
        # Same key as the S1 call above, same body. This is the retry an agent
        # would send after a timeout -- and the only version of the test that
        # answers "does a retry re-run my service?".
        rec = call(key, {"service_id": svc,
                         "input": {"delay_seconds": delay,
                                   "run_tag": "varis-s1-%d" % i}},
                   idempotency_key="varis-s1-%d" % i)
        b = body_of(rec)
        log["s1b"].append({"index": i, "http_status": rec["http_status"],
                           "elapsed_s": rec["elapsed_s"],
                           "replayed": b.get("replayed"),
                           "status": b.get("status"),
                           "invocation_id": b.get("invocation_id"),
                           "has_output": bool(b.get("output")), "body": b})
        print("[S1b.%d] http=%s in %.1fs replayed=%s status=%s" % (
            i, rec["http_status"], rec["elapsed_s"], b.get("replayed"),
            b.get("status")))

    # S2 -- identity stability
    log["s2"] = [{"note": "compare request_id and invocation_id between the S1 "
                          "call and its S1b retry for the same index"}]

    log["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = os.path.join(args.out, "http.json")
    json.dump(log, open(out, "w", encoding="utf-8"), indent=2)
    print("\nwrote", out)
    print("Now compare against your service's own request log and your account "
          "ledger. A 200 from the client does not by itself prove the service "
          "ran once.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
