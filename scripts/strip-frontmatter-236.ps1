$ErrorActionPreference = 'Stop'
$localPath = 'C:\Workspaces\Holeshot Software\agency-runtime\docs\roadmap\issue-AR-236-achieve-full-cli-dashboard-parity.md'
$tempBody = Join-Path $env:TEMP 'ar-236-body.md'

$contentLines = Get-Content -LiteralPath $localPath
$dashCount = 0
$bodyLines = @()
foreach ($line in $contentLines) {
    if ($line -eq '---') {
        $dashCount++
        if ($dashCount -le 2) { continue }
    }
    if ($dashCount -ge 2) { $bodyLines += $line }
}
$bodyText = ($bodyLines -join "`n")
Set-Content -LiteralPath $tempBody -Value $bodyText -Encoding utf8
Write-Output ("wrote body: {0} chars to {1}" -f $bodyText.Length, $tempBody)
