# Windows: creates the CPU-only Python environment for the privacy shield next to this script.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m venv "$here\.venv"
$pip = "$here\.venv\Scripts\pip.exe"
& $pip install --upgrade pip | Out-Null
& $pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2"
& $pip install -r "$here\requirements.txt"
$env:HF_HOME = "$here\hf-cache"
& "$here\.venv\Scripts\python.exe" -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-edge-v1.0', map_location='cpu'); print('model cached')"
Write-Host "privacy shield environment ready: $here\.venv"
