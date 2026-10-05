from aiohttp import web


async def web_server():
    routes = web.RouteTableDef()

    @routes.get("/", allow_head=True)
    async def root_handler(request):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        }
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LinkShareBot</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #0f172a; color: #f8fafc; padding: 1rem; }
        .card { text-align: center; padding: 2.5rem; background: #1e293b; border-radius: 16px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5); max-width: 420px; width: 100%; border: 1px solid #334155; }
        .icon { font-size: 3rem; margin-bottom: 1rem; display: inline-block; animation: pulse 2s infinite; }
        h1 { color: #38bdf8; font-size: 1.75rem; margin-bottom: 0.5rem; font-weight: 700; }
        p { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }
        .status { display: inline-flex; align-items: center; gap: 0.5rem; margin-top: 1.25rem; padding: 0.35rem 0.85rem; background: rgba(16, 185, 129, 0.15); color: #34d399; border-radius: 9999px; font-weight: 600; font-size: 0.85rem; }
        .dot { width: 8px; height: 8px; background: #34d399; border-radius: 50%; display: inline-block; }
        @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">🤖</div>
        <h1>LinkShareBot</h1>
        <p>Telegram Channel Link Management & Auto-Approval Engine</p>
        <div class="status"><span class="dot"></span> Online & Active</div>
    </div>
</body>
</html>"""
        return web.Response(text=html_content, content_type="text/html", headers=headers)

    @routes.get("/health")
    async def health_handler(request):
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
        }
        return web.json_response({"status": "ok", "service": "LinkShareBot"}, headers=headers)

    app = web.Application()
    app.add_routes(routes)
    return app

