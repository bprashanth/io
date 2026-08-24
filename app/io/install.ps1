# One-time setup (Windows). CPU only. Needs Python 3.10+ and Node 18+ on PATH.
Set-Location $PSScriptRoot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.\.venv\Scripts\python.exe -m pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2"
.\.venv\Scripts\python.exe -m pip install gliner==0.2.28 pandas openpyxl
$env:HF_HOME = Join-Path $PSScriptRoot 'hf-cache'
.\.venv\Scripts\python.exe -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-edge-v1.0', map_location='cpu'); print('scanner cached')"
npm install --silent
Write-Host "ready: npm start"
