"""JSON-RPC 2.0 message layer for MCP (STDIO transport)."""
import json
import os
import sys
import itertools

_id_counter = itertools.count(1)

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def next_id():
    return next(_id_counter)


def make_request(method, params=None, meta=None):
    req = {"jsonrpc": "2.0", "id": next_id(), "method": method}
    if params is not None:
        req["params"] = params
    if meta is not None:
        req["_meta"] = meta
    return req


_default_response_meta = None


def set_default_response_meta(meta):
    global _default_response_meta
    _default_response_meta = meta or None


def make_response(req_id, result):
    if isinstance(result, dict) and "_meta" not in result and _default_response_meta:
        result = {**result, "_meta": dict(_default_response_meta)}
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def make_error(req_id, code, message, data=None):
    err = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return {"jsonrpc": "2.0", "id": req_id, "error": err}


def make_notification(method, params=None):
    note = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        note["params"] = params
    return note


def _trace_raw(text):
    path = os.environ.get("AIRMCP_TRACE")
    if not path:
        return
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("RAW  " + text + "\n")
    except OSError:
        pass


def write_message(msg, stream=None):
    stream = stream or sys.stdout
    try:
        out = json.dumps(msg)
        _trace_raw(">> " + out)
        stream.write(out + "\n")
        stream.flush()
    except (BrokenPipeError, ValueError):
        pass


def read_message(stream=None):
    """Read one JSON-RPC message line. Returns dict or None on EOF/parse error."""
    stream = stream or sys.stdin
    while True:
        line = stream.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        _trace_raw("<< " + line)
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            write_message(make_error(None, PARSE_ERROR, "Parse error"))
            continue
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            req_id = msg.get("id") if isinstance(msg, dict) else None
            write_message(make_error(req_id, INVALID_REQUEST, "Not a JSON-RPC 2.0 message"))
            continue
        return msg
