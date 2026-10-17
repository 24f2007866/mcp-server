import hashlib
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

EMAIL = "24f2007866@ds.study.iitm.ac.in".strip().lower()
SUPPORTED = ["2025-06-18", "2025-03-26", "2024-11-05"]

TOOL = {
    "name": "solve_challenge",
    "description": "Returns the exam challenge response derived from request headers.",
    "inputSchema": {"type": "object", "properties": {}},
}

def rpc_result(id_, result):
    return jsonify({"jsonrpc": "2.0", "id": id_, "result": result})

def rpc_error(id_, code, msg):
    return jsonify({"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}})

def handle(msg):
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}

    # Notifications (no id) get no JSON-RPC response
    if id_ is None:
        return Response(status=202)

    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED else SUPPORTED[0]
        return rpc_result(id_, {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "exam-mcp", "version": "1.0.0"},
        })

    if method == "ping":
        return rpc_result(id_, {})

    if method == "tools/list":
        return rpc_result(id_, {"tools": [TOOL]})

    if method == "tools/call":
        if params.get("name") != "solve_challenge":
            return rpc_error(id_, -32602, "Unknown tool")
        challenge = request.headers.get("X-Exam-Challenge", "").strip()
        if not challenge:
            return rpc_result(id_, {
                "content": [{"type": "text", "text": "missing X-Exam-Challenge header"}],
                "isError": True,
            })
        digest = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
        return rpc_result(id_, {"content": [{"type": "text", "text": digest}]})

    return rpc_error(id_, -32601, f"Method not found: {method}")

@app.route("/mcp", methods=["POST"])
@app.route("/", methods=["POST"])
def mcp():
    body = request.get_json(silent=True)
    if body is None:
        return rpc_error(None, -32700, "Parse error"), 400
    if isinstance(body, list):  # batch support
        out = []
        for m in body:
            r = handle(m)
            if r.status_code != 202:
                out.append(r.get_json())
        return jsonify(out) if out else Response(status=202)
    return handle(body)

@app.route("/mcp", methods=["GET"])
def mcp_get():
    return Response(status=405)  # no server-initiated SSE stream

@app.route("/health")
def health():
    return "ok"
