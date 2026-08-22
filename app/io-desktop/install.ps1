# One-time setup for io desktop (Windows). Needs Python 3.10+ and Node 18+ on PATH.
Set-Location $PSScriptRoot
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
.\.venv\Scripts\python.exe -m pip install --quiet duckdb pandas openpyxl sqlglot
npm install --silent
Write-Host "Done. Start with: npm start"
