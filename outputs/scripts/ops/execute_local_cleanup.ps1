param(
    [Parameter(Mandatory=$true)][string]$PlanPath,
    [Parameter(Mandatory=$true)][string]$PlanSha256,
    [switch]$CheckOnly
)
$ErrorActionPreference = 'Stop'
$cleanupRoot = [IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$rootPrefix = $cleanupRoot.TrimEnd('\') + '\'

function Resolve-InProject([string]$Relative) {
    $absolute = [IO.Path]::GetFullPath((Join-Path $cleanupRoot ($Relative.Replace('/','\'))))
    if (-not $absolute.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)) {
        throw "Target is not a strict descendant of the named project: $absolute"
    }
    return $absolute
}
function Assert-NoReparse([string]$Absolute) {
    $cursor = $Absolute
    while ($cursor.Length -ge $cleanupRoot.Length) {
        $node = Get-Item -LiteralPath $cursor -Force
        if (($node.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "Reparse point refused: $cursor"
        }
        if ($cursor.Equals($cleanupRoot,[StringComparison]::OrdinalIgnoreCase)) { break }
        $cursor = Split-Path -Parent $cursor
    }
}
function Assert-File([string]$Relative,$Expected) {
    $absolute = Resolve-InProject $Relative
    Assert-NoReparse $absolute
    $node = Get-Item -LiteralPath $absolute -Force
    if ($node.PSIsContainer -or $node.Length -ne [long]$Expected.bytes -or
        (Get-FileHash -LiteralPath $absolute -Algorithm SHA256).Hash -ine $Expected.sha256) {
        throw "File changed or has the wrong type: $Relative"
    }
}

$planAbsolute = [IO.Path]::GetFullPath($PlanPath)
if (-not $planAbsolute.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Plan must be inside project' }
Assert-NoReparse $planAbsolute
if ((Get-FileHash -LiteralPath $planAbsolute -Algorithm SHA256).Hash -ine $PlanSha256) { throw 'Plan hash mismatch' }
$plan = Get-Content -LiteralPath $planAbsolute -Raw -Encoding UTF8 | ConvertFrom-Json
if ($plan.schema -ne 'project_cleanup_v1' -or $plan.project_root -ine $cleanupRoot) { throw 'Wrong plan/project' }
$preservedPath = [IO.Path]::GetFullPath($plan.preserved_manifest)
if (-not $preservedPath.StartsWith($rootPrefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Preserved manifest outside project' }
Assert-NoReparse $preservedPath
if ((Get-FileHash -LiteralPath $preservedPath -Algorithm SHA256).Hash -ine $plan.preserved_manifest_sha256) { throw 'Preserved manifest hash mismatch' }
$preserved = Get-Content -LiteralPath $preservedPath -Raw -Encoding UTF8 | ConvertFrom-Json
$allowedDirectories = @(
    '.cache/pip','.cache/pip-audit','.cache/curation-check-pip',
    '.cache/task1_import_validation','.cache/task1_import_validation_final',
    '.cache/task1_review_replay','.cache/task1_v2_final_prepare',
    '.cache/task1_v2_offline_prepare','.cache/task1_v2_validated_prepare',
    '.cache/report_synthetic_validation_6cd3d3ee','.cache/task1_v3_prerelease_20261016',
    'outputs/task1_v3_replay_validation','outputs/task1_v3_replay_validation_final',
    'outputs/task1_v3_replay_delivery_validation','outputs/next_stage_transfer',
    'outputs/source_alignment_review_20261015','outputs/assay_audit_transfer_20261014',
    'outputs/assay_review_transfer_20261014'
)
$duplicateBackup = '.sync_audit/backup_20261015_bbea8ee9/backup_20261015_bbea8ee9_local_snapshot.zip'
$selectedFiles = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)
$plannedBytes = [long]0
foreach ($candidate in $plan.candidates) {
    $relative = [string]$candidate.relative_path
    $absolute = Resolve-InProject $relative
    Assert-NoReparse $absolute
    if ($candidate.kind -eq 'directory') {
        if ($allowedDirectories -notcontains $relative) { throw "Unapproved directory: $relative" }
        $children = @(Get-ChildItem -LiteralPath $absolute -Recurse -Force)
        if (@($children | Where-Object { ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0 }).Count) { throw "Nested reparse point: $relative" }
        $actualFiles = @($children | Where-Object { -not $_.PSIsContainer })
        if ($actualFiles.Count -ne @($candidate.files.PSObject.Properties).Count) { throw "Directory content changed: $relative" }
    } elseif ($candidate.kind -eq 'file') {
        $isBytecode = $relative.EndsWith('.pyc') -and $relative.Contains('/__pycache__/') -and
            ($relative.StartsWith('.cache/') -or $relative.StartsWith('outputs/')) -and
            (-not $relative.StartsWith('outputs/results/'))
        if ($relative -ne $duplicateBackup -and -not $isBytecode) { throw "Unapproved file: $relative" }
    } else { throw 'Unknown candidate kind' }
    foreach ($member in $candidate.files.PSObject.Properties) {
        if ($member.Name -ne $relative -and -not $member.Name.StartsWith($relative+'/',[StringComparison]::OrdinalIgnoreCase)) { throw 'Candidate/member mismatch' }
        if (-not $selectedFiles.Add($member.Name)) { throw 'Overlapping deletion targets' }
        Assert-File $member.Name $member.Value
        $plannedBytes += [long]$member.Value.bytes
    }
}
if ($selectedFiles.Count -ne $plan.delete_file_count -or $plannedBytes -ne [long]$plan.delete_bytes) { throw 'Deletion totals mismatch' }
foreach ($member in $preserved.PSObject.Properties) {
    if ($selectedFiles.Contains($member.Name)) { throw 'Retained/deleted sets overlap' }
    Assert-File $member.Name $member.Value
}
if ($CheckOnly) {
    [pscustomobject]@{status='preflight_verified_no_deletions';files=$selectedFiles.Count;bytes=$plannedBytes;
        protected_files=@($preserved.PSObject.Properties).Count} | ConvertTo-Json
    exit 0
}

$reportDirectory = Split-Path -Parent $planAbsolute
$receiptPath = Join-Path $reportDirectory 'cleanup_receipt.json'
$logPath = Join-Path $reportDirectory 'deleted_targets.jsonl'
if (Test-Path -LiteralPath $receiptPath) { throw 'Cleanup receipt already exists; inspect it before retrying' }
$receipt = [ordered]@{schema='project_cleanup_receipt_v1';status='started';project_root=$cleanupRoot;
    plan_sha256=$PlanSha256;started_at=(Get-Date).ToString('o');deleted_targets=0;
    deleted_files=0;deleted_bytes=[long]0;protected_files=@($preserved.PSObject.Properties).Count}
$writer = New-Object IO.StreamWriter($logPath,$false,(New-Object Text.UTF8Encoding($false)))
try {
    foreach ($candidate in $plan.candidates) {
        $absolute = Resolve-InProject $candidate.relative_path
        Assert-NoReparse $absolute
        if ($candidate.kind -eq 'directory') { Remove-Item -LiteralPath $absolute -Recurse -Force }
        else { Remove-Item -LiteralPath $absolute -Force }
        if (Test-Path -LiteralPath $absolute) { throw "Removal did not complete: $absolute" }
        $receipt.deleted_targets++
        $receipt.deleted_files += @($candidate.files.PSObject.Properties).Count
        $receipt.deleted_bytes += [long]$candidate.bytes
        $writer.WriteLine((@{path=$absolute;category=$candidate.category;bytes=$candidate.bytes} | ConvertTo-Json -Compress))
        $writer.Flush()
    }
    foreach ($member in $preserved.PSObject.Properties) { Assert-File $member.Name $member.Value }
    $receipt.status = 'completed_retained_files_hash_verified'
} catch {
    $receipt.status = 'stopped_after_error'
    $receipt.error = $_.Exception.Message
    throw
} finally {
    $writer.Dispose()
    $receipt.finished_at = (Get-Date).ToString('o')
    $receipt | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $receiptPath -Encoding UTF8
}
$receipt | ConvertTo-Json -Depth 4
