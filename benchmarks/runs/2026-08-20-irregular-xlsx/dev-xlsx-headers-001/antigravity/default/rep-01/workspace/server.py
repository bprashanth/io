#!/usr/bin/env python3
import http.server
import socketserver
import json
import urllib.parse
import os
import sys
from parser import parse_excel_workbook

PORT = 8000
DATA_FILE = os.path.join(os.path.dirname(__file__), 'school_attendance_nested.xlsx')

class AttendanceRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        params = urllib.parse.parse_qs(parsed_path.query)

        if path == '/api/data':
            self.handle_api_data()
        elif path == '/api/sheets':
            self.handle_api_sheets()
        elif path == '/api/sheet':
            sheet_name = params.get('name', [None])[0]
            self.handle_api_sheet(sheet_name)
        elif path == '/api/health':
            self.send_json_response({'status': 'ok', 'port': PORT})
        else:
            # Default to index.html for root
            if path == '/' or path == '':
                self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path

        if path == '/api/upload':
            self.handle_api_upload()
        elif path == '/api/reload':
            self.handle_api_reload()
        else:
            self.send_error(404, "Endpoint not found")

    def handle_api_data(self):
        try:
            data = parse_excel_workbook(DATA_FILE)
            self.send_json_response(data)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def handle_api_sheets(self):
        try:
            data = parse_excel_workbook(DATA_FILE)
            self.send_json_response({'sheets': data.get('sheets', [])})
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def handle_api_sheet(self, sheet_name):
        try:
            data = parse_excel_workbook(DATA_FILE)
            raw_sheets = data.get('raw_sheets', {})
            if sheet_name in raw_sheets:
                self.send_json_response(raw_sheets[sheet_name])
            else:
                self.send_json_response({'error': f"Sheet '{sheet_name}' not found"}, status=404)
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def handle_api_reload(self):
        try:
            data = parse_excel_workbook(DATA_FILE)
            # Update data.js and attendance_data.json
            with open(os.path.join(os.path.dirname(__file__), 'attendance_data.json'), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            with open(os.path.join(os.path.dirname(__file__), 'data.js'), 'w', encoding='utf-8') as f:
                f.write('window.INITIAL_ATTENDANCE_DATA = ' + json.dumps(data, indent=2) + ';\n')
            self.send_json_response({'status': 'reloaded', 'timestamp': str(os.path.getmtime(DATA_FILE))})
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def handle_api_upload(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_json_response({'error': 'No file uploaded'}, status=400)
                return

            body = self.rfile.read(content_length)
            # Simple multipart/form-data or binary upload handling
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                # Extract boundary
                boundary = content_type.split('boundary=')[1].encode()
                parts = body.split(b'--' + boundary)
                file_bytes = None
                for part in parts:
                    if b'filename=' in part:
                        header_end = part.find(b'\r\n\r\n')
                        if header_end != -1:
                            file_bytes = part[header_end+4:].rstrip(b'\r\n')
                            break
                if file_bytes:
                    with open(DATA_FILE, 'wb') as f:
                        f.write(file_bytes)
            else:
                with open(DATA_FILE, 'wb') as f:
                    f.write(body)

            # Re-parse
            data = parse_excel_workbook(DATA_FILE)
            with open(os.path.join(os.path.dirname(__file__), 'attendance_data.json'), 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            with open(os.path.join(os.path.dirname(__file__), 'data.js'), 'w', encoding='utf-8') as f:
                f.write('window.INITIAL_ATTENDANCE_DATA = ' + json.dumps(data, indent=2) + ';\n')

            self.send_json_response({'status': 'success', 'message': 'File uploaded and parsed successfully', 'sheets': data.get('sheets', [])})
        except Exception as e:
            self.send_json_response({'error': str(e)}, status=500)

    def send_json_response(self, data, status=200):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_bytes)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

def run_server():
    server_address = ('', PORT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(server_address, AttendanceRequestHandler) as httpd:
        print(f"School Attendance Portal server running on http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")

if __name__ == '__main__':
    run_server()
