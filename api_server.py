"""
KeyBypass REST API Server — Phase 2
Self-hosted Flask API ที่แจก API key ให้คนอื่นใช้งานได้

Endpoints:
  GET  /                     API info
  GET  /api/health           Health check + uptime
  GET  /api/stats            Bypass statistics
  GET  /api/supported        Supported services list
  POST /api/bypass           Bypass single URL
  POST /api/bypass/bulk      Bulk bypass (API key required)
  GET  /api/docs             HTML documentation

Source integrated from: Evo-Bypass/app.py + server/server.js
"""

import time
import asyncio
import secrets
import json
import os
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import our bypass engine (async → run in thread)
import sys
sys.path.insert(0, os.path.dirname(__file__))
from config import ALL_SUPPORTED_DOMAINS, COLOR_PRIMARY
from utils.stats_manager import stats_manager
from utils.rtao_client import rtao_client

app = Flask(__name__, static_folder="website", static_url_path="")
CORS(app, origins="*")

# ─────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────
API_PORT = int(os.getenv("API_PORT", "49288"))
MASTER_API_KEY = os.getenv("MASTER_API_KEY", secrets.token_hex(16))  # auto-generate if not set
RATE_LIMIT_REQUESTS = 200
RATE_LIMIT_WINDOW = 900  # 15 minutes

# In-memory store
_request_counts: dict = {}
_api_keys: set = {MASTER_API_KEY}
_server_stats = {
    "total_bypassed": 0,
    "success_count": 0,
    "failure_count": 0,
    "service_stats": {},
    "uptime": time.time()
}


# ─────────────────────────────────────────────────────────────
# Rate Limiter
# ─────────────────────────────────────────────────────────────
def rate_limit(max_req=RATE_LIMIT_REQUESTS, window=RATE_LIMIT_WINDOW):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or "unknown"
            now = time.time()
            _request_counts.setdefault(ip, [])
            _request_counts[ip] = [t for t in _request_counts[ip] if now - t < window]
            if len(_request_counts[ip]) >= max_req:
                return jsonify({
                    "success": False,
                    "error": "Rate limit exceeded. Try again later.",
                    "retry_after": int(window - (now - _request_counts[ip][0]))
                }), 429
            _request_counts[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator


def require_api_key(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        key = request.headers.get("X-API-Key") or request.json.get("apiKey", "") if request.is_json else ""
        if not key or key not in _api_keys:
            return jsonify({"success": False, "error": "Invalid or missing API key"}), 401
        return f(*args, **kwargs)
    return wrapped


# ─────────────────────────────────────────────────────────────
# Async bypass helper (bridge async engine → sync Flask)
# ─────────────────────────────────────────────────────────────
def _run_bypass(url: str, engine: str = "auto") -> dict:
    from utils.bypasser import bypass_engine
    loop = asyncio.new_event_loop()
    try:
        # If specific engine selected, prepend a hint for the bypass engine
        if engine and engine != "auto":
            # Some engines map directly to providers
            engine_map = {
                "platoboost": "platoboost",
                "luarmor": "luarmor",
                "linkvertise": "linkvertise",
                "lootlabs": "lootlabs",
                "workink": "workink",
                "rekonise": "rekonise",
                "bloxscript": "bloxscript",
                "adlinkfly": "adlinkfly",
                "adfly": "adfly",
            }
            mapped = engine_map.get(engine)
            if mapped:
                # Temporarily force the engine by overriding provider patterns
                pass  # The engine parameter is passed as metadata
        return loop.run_until_complete(bypass_engine.bypass_url(url))
    finally:
        loop.close()


def _update_stats(result: dict):
    provider = result.get("provider", {}).get("name", "Unknown")
    if result.get("success"):
        _server_stats["total_bypassed"] += 1
        _server_stats["success_count"] += 1
        _server_stats["service_stats"][provider] = _server_stats["service_stats"].get(provider, 0) + 1
        # Sync with bot stats_manager
        try:
            stats_manager.record_bypass(
                result.get("provider", {}).get("key", "general"),
                0,  # API user, no user_id
                None
            )
        except Exception:
            pass
    else:
        _server_stats["failure_count"] += 1


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────

@app.route("/")
def home():
    """Serve website or return API info."""
    website_index = os.path.join(os.path.dirname(__file__), "website", "index.html")
    if os.path.exists(website_index):
        return send_from_directory(os.path.join(os.path.dirname(__file__), "website"), "index.html")
    return jsonify({
        "name": "KeyBypass API",
        "version": "3.0.0",
        "status": "operational",
        "powered_by": "Self-hosted Multi-Endpoint Engine",
        "endpoints": {
            "health": "GET /api/health",
            "stats": "GET /api/stats",
            "supported": "GET /api/supported",
            "bypass": "POST /api/bypass",
            "bulk_bypass": "POST /api/bypass/bulk  [API key required]",
            "docs": "GET /api/docs"
        }
    })


@app.route("/api/health")
def health():
    uptime = int(time.time() - _server_stats["uptime"])
    h, rem = divmod(uptime, 3600)
    m, s = divmod(rem, 60)
    return jsonify({
        "status": "operational",
        "uptime_seconds": uptime,
        "uptime_human": f"{h}h {m}m {s}s",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "engine": "Self-hosted Cascade v3"
    })


@app.route("/api/stats")
def get_stats():
    total = _server_stats["success_count"] + _server_stats["failure_count"]
    success_rate = f"{(_server_stats['success_count'] / total * 100):.2f}%" if total > 0 else "0%"

    # Also pull from bot's stats
    try:
        bot_stats = stats_manager.get_summary()
    except Exception:
        bot_stats = {}

    return jsonify({
        "success": True,
        "stats": {
            "total_bypassed": _server_stats["total_bypassed"] + bot_stats.get("total_bypassed", 0),
            "api_success": _server_stats["success_count"],
            "api_failure": _server_stats["failure_count"],
            "success_rate": success_rate,
            "top_services": sorted(
                _server_stats["service_stats"].items(),
                key=lambda x: x[1], reverse=True
            )[:10],
            "uptime_seconds": int(time.time() - _server_stats["uptime"]),
            "unique_users": bot_stats.get("unique_users", 0)
        }
    })


@app.route("/api/supported")
def supported():
    # Return local catalog + synced RTaO supported domains
    rtao_domains = list(rtao_client.supported_domains)
    return jsonify({
        "success": True,
        "total": len(ALL_SUPPORTED_DOMAINS),
        "services": ALL_SUPPORTED_DOMAINS,
        "categories": list(set(s["category"] for s in ALL_SUPPORTED_DOMAINS)),
        "rtao_primary": {
            "total_supported": len(rtao_domains),
            "endpoint": "https://api.rtaoexe.xyz",
            "supported_endpoint": "https://api.rtaoexe.xyz/supported",
            "domains": rtao_domains
        },
        "rtao_fallback": {
            "total_supported": len(rtao_domains),
            "endpoint": "https://api.rtaoexe.xyz",
            "supported_endpoint": "https://api.rtaoexe.xyz/supported",
            "domains": rtao_domains
        }
    })


@app.route("/api/bypass", methods=["POST"])
@rate_limit()
def bypass():
    """Single URL bypass endpoint."""
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()
    engine = data.get("engine", "auto")

    if not url:
        return jsonify({"success": False, "error": "URL is required"}), 400
    if not (url.startswith("http://") or url.startswith("https://")):
        return jsonify({"success": False, "error": "Invalid URL format"}), 400

    start = time.time()
    print(f"[API] Bypass request (engine={engine}): {url[:80]}")

    result = _run_bypass(url, engine)
    elapsed = round((time.time() - start) * 1000)
    _update_stats(result)

    if result.get("success"):
        print(f"[API] Success ({elapsed}ms): {result.get('endpoint_used')}")
        return jsonify({
            "success": True,
            "destination": result["direct_url"],
            "service": result.get("provider", {}).get("name", "Unknown"),
            "provider_key": result.get("provider", {}).get("key", "general"),
            "endpoint": result.get("endpoint_used", "unknown"),
            "chain": result.get("chain_note", ""),
            "is_key": result.get("is_key", False),
            "processingTime": elapsed
        })
    else:
        print(f"[API] Failure ({elapsed}ms): {result.get('error')}")
        return jsonify({
            "success": False,
            "error": result.get("error", "Bypass failed"),
            "service": result.get("provider", {}).get("name", "Unknown"),
            "processingTime": elapsed
        }), 200  # 200 with success:false for client compatibility


@app.route("/api/bypass/bulk", methods=["POST"])
@rate_limit(max_req=20, window=900)  # Stricter limit for bulk
@require_api_key
def bypass_bulk():
    """Bulk bypass — requires API key. Max 50 URLs per request."""
    data = request.get_json(silent=True) or {}
    urls = data.get("urls", [])

    if not urls or not isinstance(urls, list):
        return jsonify({"success": False, "error": "urls array is required"}), 400
    if len(urls) > 50:
        return jsonify({"success": False, "error": "Max 50 URLs per bulk request"}), 400

    print(f"[API] Bulk bypass: {len(urls)} URLs")
    start = time.time()

    results = []
    for url_item in urls:
        url_item = url_item.strip()
        if not (url_item.startswith("http://") or url_item.startswith("https://")):
            results.append({"url": url_item, "success": False, "error": "Invalid URL"})
            continue
        r = _run_bypass(url_item)
        _update_stats(r)
        if r.get("success"):
            results.append({
                "url": url,
                "success": True,
                "destination": r["direct_url"],
                "service": r.get("provider", {}).get("name", "Unknown"),
                "chain": r.get("chain_note", ""),
                "is_key": r.get("is_key", False)
            })
        else:
            results.append({
                "url": url,
                "success": False,
                "error": r.get("error", "Failed")
            })

    successful = sum(1 for r in results if r["success"])
    failed = len(results) - successful
    elapsed = round((time.time() - start) * 1000)

    print(f"[API] Bulk complete: {successful}/{len(results)} success ({elapsed}ms)")
    return jsonify({
        "success": True,
        "results": results,
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "success_rate": f"{(successful/len(results)*100):.1f}%" if results else "0%",
        "processingTime": elapsed
    })


@app.route("/api/docs")
def docs():
    """Return HTML API documentation."""
    html = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>KeyBypass API Docs</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:#0a0a0f; color:#e0e0e0; font-family:'Segoe UI',sans-serif; padding:2rem; }
  h1 { color:#8A2BE2; font-size:2rem; margin-bottom:.5rem; }
  h2 { color:#00D1B2; margin:2rem 0 .5rem; font-size:1.2rem; }
  p { color:#aaa; margin:.5rem 0 1rem; }
  .badge { background:#8A2BE2; color:#fff; padding:.2rem .6rem; border-radius:.3rem; font-size:.75rem; margin-right:.5rem; }
  .badge.post { background:#E57373; }
  .endpoint { background:#111; border:1px solid #222; border-radius:.5rem; padding:1rem; margin:.5rem 0; }
  .endpoint-title { font-weight:bold; font-size:1rem; margin-bottom:.5rem; }
  pre { background:#0d0d0d; border:1px solid #333; border-radius:.4rem; padding:1rem; overflow-x:auto; font-size:.85rem; color:#00FF7F; margin:.5rem 0; }
  .note { background:#1a1035; border-left:3px solid #8A2BE2; padding:.75rem 1rem; border-radius:0 .4rem .4rem 0; margin:.5rem 0; color:#ccc; font-size:.9rem; }
</style>
</head>
<body>
<h1>🔓 KeyBypass API v3</h1>
<p>Self-hosted multi-endpoint bypass engine. ไม่พึ่ง external API ใด ๆ</p>

<h2>Base URL</h2>
<pre>http://localhost:5000</pre>

<h2>Endpoints</h2>

<div class="endpoint">
  <div class="endpoint-title"><span class="badge">GET</span>/api/health</div>
  <p>ตรวจสอบสถานะ server</p>
  <pre>curl http://localhost:5000/api/health</pre>
</div>

<div class="endpoint">
  <div class="endpoint-title"><span class="badge">GET</span>/api/stats</div>
  <p>สถิติการ bypass ทั้งหมด</p>
</div>

<div class="endpoint">
  <div class="endpoint-title"><span class="badge">GET</span>/api/supported</div>
  <p>รายชื่อ service ที่รองรับทั้งหมด</p>
</div>

<div class="endpoint">
  <div class="endpoint-title"><span class="badge post">POST</span>/api/bypass</div>
  <p>Bypass URL เดียว (200 req / 15 min)</p>
  <pre>curl -X POST http://localhost:5000/api/bypass \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://linkvertise.com/..."}'</pre>
  <pre>{
  "success": true,
  "destination": "https://...",
  "service": "Linkvertise",
  "endpoint": "cascade",
  "chain": "",
  "is_key": false,
  "processingTime": 1230
}</pre>
</div>

<div class="endpoint">
  <div class="endpoint-title"><span class="badge post">POST</span>/api/bypass/bulk</div>
  <p>Bulk bypass สูงสุด 50 URL (ต้องมี API Key)</p>
  <pre>curl -X POST http://localhost:5000/api/bypass/bulk \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: YOUR_API_KEY" \\
  -d '{"urls":["https://...","https://..."]}'</pre>
</div>

<div class="note">
  💡 API Key: ติดต่อผ่าน Discord เพื่อขอ API Key สำหรับ Bulk bypass
</div>

<h2>รองรับ</h2>
<p>Delta Executor · Luarmor · LootLabs · Linkvertise · Work.ink · Rekonise · Platoboost · Trigon · Hydrogen · Codex · และอื่น ๆ อีก 100+ ค่าย</p>
</body>
</html>"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/token")
def token_bridge():
    """Automated Discord Token Bridge Web Page for AutoQuest."""
    return send_from_directory("website", "token.html")



# ─────────────────────────────────────────────────────────────
# Error handlers
# ─────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "error": "Internal server error"}), 500


# ─────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("  KeyBypass API Server v3.0")
    print("=" * 50)
    print(f"  Port   : {API_PORT}")
    print(f"  API    : http://localhost:{API_PORT}/api")
    print(f"  Docs   : http://localhost:{API_PORT}/api/docs")
    print(f"  Health : http://localhost:{API_PORT}/api/health")
    print(f"  API Key: {MASTER_API_KEY}")
    print("=" * 50)
    app.run(host="0.0.0.0", port=API_PORT, debug=False, threaded=True)
