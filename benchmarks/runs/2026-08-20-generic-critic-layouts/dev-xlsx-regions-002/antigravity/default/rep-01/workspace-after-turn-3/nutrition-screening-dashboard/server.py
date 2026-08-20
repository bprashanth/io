#!/usr/bin/env python3
"""
High-performance standalone Python server for Nutrition Screening Coverage Dashboard.
Automatically parses 'nutrition_review_side_by_side.xlsx', serves the web UI, and provides /api/data.
"""
import http.server
import socketserver
import json
import os
import sys

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self):
        if self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            data_file = os.path.join(DIRECTORY, 'data.json')
            if os.path.exists(data_file):
                with open(data_file, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.wfile.write(b'{"error": "data.json not found"}')
            return
        
        return super().do_GET()

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        print(f"================================================================")
        print(f"  Nutrition Screening Coverage Dashboard Server Running")
        print(f"  URL: http://localhost:{port}")
        print(f"  Source Sheet: 'Quarterly Review'")
        print(f"  Source Table: 'Table 1. Nutrition screening by block and year'")
        print(f"  Cell Range:   A1:C7")
        print(f"================================================================")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
