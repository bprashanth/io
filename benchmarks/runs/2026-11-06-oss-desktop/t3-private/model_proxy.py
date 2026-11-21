import http.server,urllib.request,json,time
class P(http.server.BaseHTTPRequestHandler):
 def do_POST(self):
  body=self.rfile.read(int(self.headers.get('Content-Length',0)))
  j=json.loads(body)
  with open('/tmp/io-t3-benchmark/model-requests.jsonl','a') as f:f.write(json.dumps(dict(time=time.time(),path=self.path,model=j.get('model'),stream=j.get('stream')))+'\n')
  try:
   with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8181'+self.path,data=body,headers={'Content-Type':'application/json'}),timeout=240) as r:
    self.send_response(r.status);self.send_header('Content-Type',r.headers.get('Content-Type'));self.end_headers()
    while chunk:=r.read1(8192):self.wfile.write(chunk);self.wfile.flush()
  except urllib.error.HTTPError as e:
   self.send_response(e.code);self.send_header('Content-Type','application/json');self.end_headers();self.wfile.write(e.read())
  except Exception as e: print(type(e).__name__,flush=True)
 def log_message(self,*a):pass
http.server.ThreadingHTTPServer(('172.26.0.1',8182),P).serve_forever()
