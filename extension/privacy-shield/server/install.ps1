# Windows: creates the Python environment for the privacy shield next to this script.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
python -m venv "$here\.venv"
& "$here\.venv\Scripts\pip.exe" install --upgrade pip | Out-Null
& "$here\.venv\Scripts\pip.exe" install -r "$here\requirements.txt"
$env:HF_HOME = "$here\hf-cache"
& "$here\.venv\Scripts\python.exe" -c "from gliner import GLiNER; GLiNER.from_pretrained('knowledgator/gliner-pii-edge-v1.0'); print('model cached')"
Write-Host "privacy shield environment ready: $here\.venv"
