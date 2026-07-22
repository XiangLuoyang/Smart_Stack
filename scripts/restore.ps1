# Smart Stack 恢复脚本
param([Parameter(Mandatory)][string]$BackupFile, [string]$DbPath = "backend\data\smartstack.db", [string]$BackupDir = "backups")

$python = "C:\Users\chaos\AppData\Local\Programs\Python\Python312\python.exe"

Write-Host "=== Smart Stack Restore ===" -ForegroundColor Yellow
Write-Host "Restoring from: $BackupFile"
& $python -c @"
import sys; sys.path.insert(0, 'backend')
from app.services.backup_service import BackupService
svc = BackupService('$DbPath', '$BackupDir')
r = svc.restore('$BackupFile')
print(f'Restored from: {r[\"restored_from\"]}')
print(f'Pre-restore backup: {r[\"pre_restore_backup\"]}')
"@
Write-Host "Done." -ForegroundColor Green