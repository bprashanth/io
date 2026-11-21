import subprocess, sys, time, urllib.request
p = subprocess.Popen([sys.executable, "-I", sys.argv[1], "8874"])
try:
    for _ in range(50):
        try:
            page = urllib.request.urlopen("http://127.0.0.1:8874/").read().decode()
            break
        except OSError:
            time.sleep(0.1)
    r = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8874/talk", data=b"x" * 4000,
                                                      headers={"Content-Type": "audio/webm"})).read().decode()
    print("page ok" if "MediaRecorder" in page else "page bad", r)
finally:
    p.terminate()
