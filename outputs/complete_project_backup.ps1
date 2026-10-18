param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Check-Native([string]$Step) {
    if ($LASTEXITCODE -ne 0) { throw "$Step failed. Stop here; keep the error output." }
}

$plan = Get-Content -LiteralPath $PlanPath -Raw -Encoding UTF8 | ConvertFrom-Json
$projectRoot = [string]$plan.local_project
$backupDir = Split-Path -Parent (Resolve-Path -LiteralPath $PlanPath).Path
$pythonExe = [string]$plan.python_executable
$tool = Join-Path $projectRoot 'outputs\project_backup_v1.py'
$keyPath = Join-Path $env:USERPROFILE '.ssh\id_ed25519_lab'
$targetHost = 'xinrong@100.92.205.88'
$remoteRoot = '/driveA/xinrong/agentic-screening'
$backupId = [string]$plan.backup_id
if ($backupId -notmatch '^backup_[0-9]{8}_[0-9a-f]{8}$') { throw 'Invalid backup ID' }
if ($plan.schema -ne 'project_backup_transfer_plan_v1') { throw 'Invalid plan schema' }
foreach ($path in @($pythonExe,$tool,$keyPath)) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required file missing: $path" }
}
if ((Get-FileHash -LiteralPath $tool -Algorithm SHA256).Hash.ToLowerInvariant() -ne $plan.tool_sha256) {
    throw 'Backup helper changed since preparation. Ask Codex to prepare a new plan.'
}
$localZip = Join-Path $backupDir 'local_snapshot.zip'
$localHash = [string]$plan.local_archive_sha256
Write-Host '[1/5] Verify the prepared local snapshot.'
& $pythonExe -B $tool verify --archive $localZip --expected-sha256 $localHash --receipt (Join-Path $backupDir 'local_rechecked_receipt.json')
Check-Native 'Local backup verification'

# Uploads go to the already-existing audit directory, outside frozen code/data.
$uploadCopy = Join-Path $backupDir ($backupId + '_local_snapshot.zip')
$helperCopy = Join-Path $backupDir ($backupId + '_project_backup_v1.py')
if (-not (Test-Path -LiteralPath $uploadCopy)) { Copy-Item -LiteralPath $localZip -Destination $uploadCopy }
if ((Get-FileHash -LiteralPath $uploadCopy -Algorithm SHA256).Hash.ToLowerInvariant() -ne $localHash) { throw 'Upload copy hash mismatch' }
Copy-Item -LiteralPath $tool -Destination $helperCopy -Force
$sshOptions = @('-i',$keyPath,'-o','IdentitiesOnly=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=20')
$remoteAudit = "$remoteRoot/.sync_audit"
Write-Host '[2/5] Upload the local snapshot and helper. Enter the SSH key passphrase if asked.'
& scp @sshOptions $uploadCopy $helperCopy "${targetHost}:$remoteAudit/"
Check-Native 'Upload'

$remoteTool = "$remoteAudit/${backupId}_project_backup_v1.py"
$remoteIncoming = "$remoteAudit/${backupId}_local_snapshot.zip"
$toolHash = [string]$plan.tool_sha256
$frozenHash = [string]$plan.expected_frozen_manifest_sha256
if ($toolHash -notmatch '^[0-9a-f]{64}$' -or $localHash -notmatch '^[0-9a-f]{64}$' -or $frozenHash -notmatch '^[0-9a-f]{64}$') { throw 'Invalid SHA256 in plan' }
$remoteCommand = "umask 077 && printf '%s  %s\n' '$toolHash' '$remoteTool' | sha256sum -c - && python3 -B '$remoteTool' remote-step --root '$remoteRoot' --backup-id '$backupId' --local-sha256 '$localHash' --incoming '$remoteIncoming' --expected-frozen-manifest '$frozenHash'"
Write-Host '[3/5] Verify the upload and create the remote snapshot.'
& ssh @sshOptions $targetHost $remoteCommand
Check-Native 'Remote backup creation'

$remoteDir = "$remoteRoot/data/curation_private/backups/$backupId"
Write-Host '[4/5] Download the remote snapshot and verification receipts.'
& scp @sshOptions "${targetHost}:$remoteDir/remote_snapshot.zip" "${targetHost}:$remoteDir/remote_created_receipt.json" "${targetHost}:$remoteDir/local_received_receipt.json" $backupDir
Check-Native 'Remote backup download'

$remoteReceipt = Get-Content -LiteralPath (Join-Path $backupDir 'remote_created_receipt.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$uploadReceipt = Get-Content -LiteralPath (Join-Path $backupDir 'local_received_receipt.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($uploadReceipt.status -ne 'VERIFIED_BACKUP_CONTENT' -or $uploadReceipt.archive_sha256 -ne $localHash) { throw 'Remote upload receipt mismatch' }
if ($remoteReceipt.status -ne 'VERIFIED_BACKUP_CONTENT' -or $remoteReceipt.source_root -ne $remoteRoot) { throw 'Remote snapshot receipt mismatch' }
if ($remoteReceipt.preservation_checks.frozen_manifest_sha256 -ne $frozenHash -or $remoteReceipt.preservation_checks.completed_campaigns -ne 30) { throw 'Frozen version preservation receipt mismatch' }
Write-Host '[5/5] Verify the downloaded archive and every file inside it.'
& $pythonExe -B $tool verify --archive (Join-Path $backupDir 'remote_snapshot.zip') --expected-sha256 $remoteReceipt.archive_sha256 --receipt (Join-Path $backupDir 'remote_download_verified.json')
Check-Native 'Downloaded remote backup verification'

$summary = [ordered]@{
    status = 'BOTH_DIRECTIONS_VERIFIED'
    backup_id = $backupId
    completed_at = [DateTimeOffset]::Now.ToString('o')
    local_backup_directory = $backupDir
    remote_backup_directory = $remoteDir
    local_archive_sha256 = $localHash
    remote_archive_sha256 = $remoteReceipt.archive_sha256
    local_snapshot_file_count = $uploadReceipt.file_count
    remote_snapshot_file_count = $remoteReceipt.file_count
    frozen_manifest_sha256 = $frozenHash
    preserved_completed_campaigns = $remoteReceipt.preservation_checks.completed_campaigns
    note = 'Verified project snapshots on both machines. Original scientific files were not replaced. Environments/caches/known credential names excluded.'
}
$summary | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backupDir 'BACKUP_COMPLETE.json') -Encoding UTF8
$summary | ConvertTo-Json -Depth 5
