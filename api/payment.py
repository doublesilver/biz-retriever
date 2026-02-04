"""
Unified Payment API - Simplified for Hobby plan  
GET /api/payment - Payment status placeholder
"""
from http.server import BaseHTTPRequestHandler
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "message": "Payment API placeholder"}')
