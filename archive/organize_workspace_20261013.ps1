$ErrorActionPreference = 'Stop'
$cleanupWorkspace = [IO.Path]::GetFullPath('F:\ThacSi\Data Mining\Survey')
$cleanupProject = Join-Path $cleanupWorkspace 'Deep_Clustering_Demo'

function Assert-CleanupPath([string]$Candidate) {
    $absolute = [IO.Path]::GetFullPath($Candidate)
    if (-not $absolute.StartsWith($cleanupWorkspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path outside intended workspace: $absolute"
    }
    if (Test-Path -LiteralPath $absolute) {
        $resolved = (Resolve-Path -LiteralPath $absolute).ProviderPath
        if (-not $resolved.StartsWith($cleanupWorkspace + '\', [StringComparison]::OrdinalIgnoreCase)) {
            throw "Resolved path outside intended workspace: $resolved"
        }
        if ((Get-Item -LiteralPath $absolute -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Refusing to operate on reparse point: $absolute"
        }
    }
    return $absolute
}

$movePlan = @(
    @('results', 'archive\reference_results'),
    @('results_verified_20261012', 'archive\results_verified_20261012'),
    @('results_timeline_20261013', 'results\timeline_20261013'),
    @('results_dcss_width_ablation_20261013', 'results\dcss_width_ablation_20261013'),
    @('docs\Bao_cao_kiem_tra_va_thuc_nghiem.html', 'archive\reports\Bao_cao_kiem_tra_va_thuc_nghiem.html'),
    @('docs\Bao_cao_kiem_tra_va_thuc_nghiem.docx', 'archive\reports\Bao_cao_kiem_tra_va_thuc_nghiem.docx'),
    @('docs\Bao_cao_kiem_tra_va_thuc_nghiem.md', 'archive\reports\Bao_cao_kiem_tra_va_thuc_nghiem.md'),
    @('notebooks\demo_5_algorithms.ipynb', 'archive\notebooks\demo_5_algorithms.ipynb'),
    @('notebooks\demo_5_algorithms_verified.ipynb', 'archive\notebooks\demo_5_algorithms_verified.ipynb'),
    @('checks\verification.json', 'archive\verification_initial.json'),
    @('checks\execute_review_notebook.py', 'archive\tools\execute_review_notebook.py'),
    @('checks\finalize_literature_tracker.py', 'archive\tools\finalize_literature_tracker.py'),
    @('checks\build_timeline_notebook.py', 'scripts\build_timeline_notebook.py'),
    @('checks\diagnose_dcss_initialization.py', 'scripts\diagnose_dcss_initialization.py'),
    @('checks\run_dcss_calibration.py', 'scripts\run_dcss_calibration.py'),
    @('prepare_data.py', 'scripts\prepare_data.py'),
    @('summarize_survey.py', 'scripts\summarize_survey.py'),
    @('build_review_report.py', 'scripts\build_review_report.py'),
    @('requirements_report.txt', 'requirements\report.txt'),
    @('requirements_notebook.txt', 'requirements\notebook.txt'),
    @('requirements_verified.txt', 'requirements\verified.txt'),
    @('requirements_tested.txt', 'archive\requirements_tested.txt'),
    @('docs\primary_papers', 'docs\references\primary_papers'),
    @('docs\author_sources', 'docs\references\author_sources'),
    @('.survey_sources', 'docs\references\survey_papers'),
    @('docs\literature_catalog_additions.json', 'docs\references\literature_catalog_additions.json')
)
$deletePlan = @(
    'checks\browser_review_profile', 'checks\report_chrome_profile', 'checks\timeline_preview_profile',
    '__pycache__', 'src\__pycache__', 'checks\__pycache__',
    'results_smoke_dcss_20261013', 'results_smoke_timeline_20261013', 'results_live_20261013',
    'checks\report_html_preview.png', 'checks\report_preview.png', 'checks\timeline_html_preview.png',
    'checks\read_primary_papers.py', 'checks\link_latest_report.py'
)

# Check every source and destination before any recursive move or delete.
foreach ($pair in $movePlan) {
    $source = Assert-CleanupPath (Join-Path $cleanupProject $pair[0])
    $destination = Assert-CleanupPath (Join-Path $cleanupProject $pair[1])
    if (-not (Test-Path -LiteralPath $source)) { throw "Missing source: $source" }
    if (Test-Path -LiteralPath $destination) { throw "Destination already exists: $destination" }
}
foreach ($relative in $deletePlan) {
    $null = Assert-CleanupPath (Join-Path $cleanupProject $relative)
}
$originalWord = Assert-CleanupPath (Join-Path $cleanupWorkspace 'Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx')
$wordDestination = Assert-CleanupPath (Join-Path $cleanupProject 'docs\original\Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx')
$duplicateWord = Assert-CleanupPath (Join-Path $cleanupProject 'docs\Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx')
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $originalWord).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $duplicateWord).Hash) {
    throw 'Word files differ; do not delete either.'
}
if (Test-Path -LiteralPath $wordDestination) { throw 'Original Word destination already exists.' }

$manifest = [ordered]@{date='2026-10-13'; moved=@(); deleted=@(); preserved_source_snapshots=@()}
foreach ($relative in @('run_demo.py', 'checks\run_dcss_calibration.py')) {
    $source = Assert-CleanupPath (Join-Path $cleanupProject $relative)
    $snapshotRelative = 'archive\source_snapshots\20261013\' + $relative
    $snapshot = Assert-CleanupPath (Join-Path $cleanupProject $snapshotRelative)
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $snapshot) -Force
    Copy-Item -LiteralPath $source -Destination $snapshot
    $manifest.preserved_source_snapshots += @{source=$relative; snapshot=$snapshotRelative; sha256=(Get-FileHash -Algorithm SHA256 -LiteralPath $snapshot).Hash}
}
foreach ($relative in @('results_timeline_20261013', 'results_dcss_width_ablation_20261013')) {
    $source = Assert-CleanupPath (Join-Path $cleanupProject ($relative + '\config.json'))
    $destination = Assert-CleanupPath (Join-Path $cleanupProject ('archive\source_snapshots\20261013\configs\' + $relative + '.json'))
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
    Copy-Item -LiteralPath $source -Destination $destination
}

foreach ($pair in $movePlan) {
    $source = Assert-CleanupPath (Join-Path $cleanupProject $pair[0])
    $destination = Assert-CleanupPath (Join-Path $cleanupProject $pair[1])
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
    Move-Item -LiteralPath $source -Destination $destination
    $manifest.moved += @{source=$pair[0]; destination=$pair[1]}
}
$null = New-Item -ItemType Directory -Path (Split-Path -Parent $wordDestination) -Force
Move-Item -LiteralPath $originalWord -Destination $wordDestination
$manifest.moved += @{source='../Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx'; destination='docs/original/Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx'}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $wordDestination).Hash -ne (Get-FileHash -Algorithm SHA256 -LiteralPath $duplicateWord).Hash) {
    throw 'Word checksum changed during move.'
}
$deletePlan += 'docs\Bao_cao_Survey_Deep_Clustering_va_Demo_5_Phuong_phap.docx'
foreach ($relative in $deletePlan) {
    $target = Assert-CleanupPath (Join-Path $cleanupProject $relative)
    if (-not (Test-Path -LiteralPath $target)) { continue }
    $entry = Get-Item -LiteralPath $target -Force
    $files = if ($entry.PSIsContainer) { @(Get-ChildItem -LiteralPath $target -Recurse -Force -File) } else { @($entry) }
    $manifest.deleted += @{path=$relative; files=$files.Count; bytes=($files | Measure-Object Length -Sum).Sum; reason='Generated temporary artifacts or checksum-identical Word duplicate'}
    Remove-Item -LiteralPath $target -Recurse -Force
}
$manifestPath = Assert-CleanupPath (Join-Path $cleanupProject 'archive\cleanup_20261013.json')
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
[PSCustomObject]@{Moved=$manifest.moved.Count; DeletedFiles=($manifest.deleted | ForEach-Object { $_.files } | Measure-Object -Sum).Sum; FreedMiB=[Math]::Round((($manifest.deleted | ForEach-Object { $_.bytes } | Measure-Object -Sum).Sum / 1MB),2)} | Format-Table -AutoSize
