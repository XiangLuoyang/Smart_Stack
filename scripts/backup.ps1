# Smart Stack 一键备份脚本
param([string]$DbPath = "backend\data\smartstack.db", [string]$BackupDir = "backups")

$python = "C:\Users\chaos\AppData\Local\Programs\Python\Python312\python.exe"

Write-Host "=== Smart Stack Backup ===" -ForegroundColor Cyan
& $python -c @"
import sys; sys.path.insert(0, 'backend')
from app.services.backup_service import BackupService
svc = BackupService('$DbPath', '$BackupDir')
m = svc.create_backup()
print(f'Backup: {m[\"file\"]}')
print(f'SHA256: {m[\"sha256\"]}')
print(f'Integrity: {m[\"integrity\"]}')
print(f'Size: {m[\"size_bytes\"]} bytes')
"@
Write-Host "Done." -ForegroundColor Green