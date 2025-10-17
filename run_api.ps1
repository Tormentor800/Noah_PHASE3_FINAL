$ErrorActionPreference = "SilentlyContinue"
New-Item -ItemType Directory -Path .\logs -Force | Out-Null
cmd /c "cd /d `"%CD%`" && py -m uvicorn src.serve.api:app --host 127.0.0.1 --port 9010 >> logs\api.log 2>&1"
