# Smart Stack 健康检查
$python = "C:\Users\chaos\AppData\Local\Programs\Python\Python312\python.exe"

Write-Host "=== Smart Stack Health ===" -ForegroundColor Cyan
& $python -c @"
import sys; sys.path.insert(0, 'backend')
from app.core.preflight import run_preflight
r = run_preflight()
print(f'Status: {r.status}')
for c, d in zip(r.codes, r.details):
    print(f'  [{c}] {d}')
if not r.codes:
    print('  All checks passed.')
"@