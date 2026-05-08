# vxlan_tunnel benchmark: both synthesis designs, CS+FM optimisations on.
#   D1 = always-extract design   (NAE=OFF)
#   D2 = NAE design              (NAE=ON)
# drop_uncompared is OFF for both. Run from STMGen/.

$bench       = "vxlan_tunnel"
$max_states  = 10
$max_entries = 10
$timeout_sec = 1800   # 30 min per run

$configs = @(
    @("D1","OFF","OFF","ON","ON"),
    @("D2","OFF","ON" ,"ON","ON")
)

$results = @()

foreach ($cfg in $configs) {
    $label = $cfg[0]; $du = $cfg[1]; $nae = $cfg[2]; $cs = $cfg[3]; $fm = $cfg[4]
    $out = "benchmarks/${bench}_${label}.p4"
    Write-Host "Running $bench / $label (DU=$du NAE=$nae CS=$cs FM=$fm) ..." -ForegroundColor Cyan

    $tmpOut = [System.IO.Path]::GetTempFileName()
    $tmpErr = [System.IO.Path]::GetTempFileName()
    $argList = @(
        "runner.py",
        "--input", "benchmarks/$bench.parser",
        "--output", $out,
        "--max_states", $max_states,
        "--max_entries", $max_entries,
        "--drop_uncompared", $du,
        "--not_always_extract", $nae,
        "--constant_synthesis", $cs,
        "--field_min", $fm
    )
    $proc = Start-Process -FilePath "python" -ArgumentList $argList -NoNewWindow -PassThru `
        -RedirectStandardOutput $tmpOut -RedirectStandardError $tmpErr

    $timedOut = $false
    if (-not $proc.WaitForExit($timeout_sec * 1000)) {
        try { $proc.Kill() } catch {}
        $proc.WaitForExit()
        $timedOut = $true
    }
    $exitCode = $proc.ExitCode
    $stderr = Get-Content $tmpErr -Raw
    Remove-Item $tmpOut,$tmpErr -Force

    if ($timedOut) {
        Write-Host "  -> TIMEOUT (>${timeout_sec}s)" -ForegroundColor Red
        if ($stderr) { Write-Host $stderr -ForegroundColor DarkGray }
        $results += [pscustomobject]@{ Bench=$bench; Design=$label; States="TO"; Entries="TO"; Time=">$timeout_sec" }
        continue
    }

    $hasStates  = ($stderr -match "states=(\S+)")
    $statesVal  = if ($hasStates)  { $Matches[1] } else { $null }
    $hasEntries = ($stderr -match "entries=(\S+)")
    $entriesVal = if ($hasEntries) { $Matches[1] } else { $null }
    $hasTime    = ($stderr -match "time=(\S+)")
    $timeVal    = if ($hasTime)    { $Matches[1] } else { $null }

    if ($hasStates -and $hasEntries -and $hasTime) {
        Write-Host "  -> states=$statesVal entries=$entriesVal time=$timeVal" -ForegroundColor Green
        $results += [pscustomobject]@{ Bench=$bench; Design=$label; States=$statesVal; Entries=$entriesVal; Time=$timeVal }
    } else {
        Write-Host "  -> FAILED (exit $exitCode)" -ForegroundColor Red
        if ($stderr) { Write-Host $stderr -ForegroundColor DarkGray }
        $results += [pscustomobject]@{ Bench=$bench; Design=$label; States="ERR"; Entries="ERR"; Time="ERR" }
    }
}

Write-Host ""
Write-Host "===== $bench results =====" -ForegroundColor Yellow
$results | Format-Table -AutoSize

$csvPath = "benchmarks/${bench}_results.csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding utf8
Write-Host "CSV written to $csvPath"
