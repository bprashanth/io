# Windows: creates the CPU-only Python environment for the privacy shield.
# Pass the IDE's globalStorage dir as the first argument so extension updates keep the env.
param([string]$Target = "")
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Target) { $Target = $here }
New-Item -ItemType Directory -Force -Path $Target | Out-Null
python -m venv "$Target\.venv"
$pip = "$Target\.venv\Scripts\pip.exe"
& $pip install --upgrade pip | Out-Null
& $pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2"
& $pip install -r "$here\requirements.txt"
$env:HF_HOME = "$Target\hf-cache"
& "$Target\.venv\Scripts\python.exe" -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-edge-v1.0', map_location='cpu'); print('model cached')"
Write-Host "privacy shield environment ready: $Target\.venv"
