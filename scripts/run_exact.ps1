# Exact benchmarks runner.
# Sweeps every benchmark across every config and prints a results table.
#
# Configurations (drop_uncompared = OFF for all):
#   C1 NAE=OFF CS=ON  FM=OFF
#   C2 NAE=OFF CS=ON  FM=ON
#   C3 NAE=OFF CS=OFF FM=OFF
#   C4 NAE=OFF CS=OFF FM=ON
#   C5 NAE=ON  CS=ON  FM=OFF
#   C6 NAE=ON  CS=OFF FM=OFF
# (NAE=ON + FM=ON is rejected by runner.py.)
#
# Each (bench, config) overwrites benchmarks/exact/<bench>.p4 with the emitted P4.
# Final results table is printed and also written to benchmarks/exact/results.csv.

$benches = @(
    "linear",
    "single_if",
    "check_after_extract1",
    "single_if_elif_else",
    "multiple_if"
)

# label, NAE, CS, FM
$configs = @(
    @("C1","OFF","ON" ,"OFF"),
    @("C2","OFF","ON" ,"ON" ),
    @("C3","OFF","OFF","OFF"),
    @("C4","OFF","OFF","ON" ),
    @("C5","ON" ,"ON" ,"OFF"),
    @("C6","ON" ,"OFF","OFF")
)

$max_states = 10
$max_entries = 10
$timeout_sec = 1200  # 20 min per-run wall-clock cap; runs exceeding it are killed

$results = @()

foreach ($b in $benches) {
    foreach ($cfg in $configs) {
        $label = $cfg[0]; $nae = $cfg[1]; $cs = $cfg[2]; $fm = $cfg[3]
        Write-Host "Running $b / $label (NAE=$nae CS=$cs FM=$fm) ..." -ForegroundColor Cyan

        $tmpOut = [System.IO.Path]::GetTempFileName()
        $tmpErr = [System.IO.Path]::GetTempFileName()
        $argList = @(
            "runner.py",
            "--input", "Exact/$b.parser",
            "--output", "Exact/$b.p4",
            "--max_states", $max_states,
            "--max_entries", $max_entries,
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
            $results += [pscustomobject]@{ Bench=$b; Config=$label; States="TO"; Entries="TO"; Time=">$timeout_sec" }
            continue
        }

        # Treat stderr-parsed states/entries/time as the success signal.
        # Start-Process -PassThru sometimes leaves $proc.ExitCode null even on
        # clean exit, so checking ExitCode alone misclassifies good runs as ERR.
        $hasStates  = ($stderr -match "states=(\S+)")
        $statesVal  = if ($hasStates)  { $Matches[1] } else { $null }
        $hasEntries = ($stderr -match "entries=(\S+)")
        $entriesVal = if ($hasEntries) { $Matches[1] } else { $null }
        $hasTime    = ($stderr -match "time=(\S+)")
        $timeVal    = if ($hasTime)    { $Matches[1] } else { $null }

        if ($hasStates -and $hasEntries -and $hasTime) {
            Write-Host "  -> states=$statesVal entries=$entriesVal time=$timeVal" -ForegroundColor Green
            $results += [pscustomobject]@{ Bench=$b; Config=$label; States=$statesVal; Entries=$entriesVal; Time=$timeVal }
        } else {
            Write-Host "  -> FAILED (exit $exitCode)" -ForegroundColor Red
            if ($stderr) { Write-Host $stderr -ForegroundColor DarkGray }
            $results += [pscustomobject]@{ Bench=$b; Config=$label; States="ERR"; Entries="ERR"; Time="ERR" }
        }
    }
}

Write-Host ""
Write-Host "===== Long format =====" -ForegroundColor Yellow
$results | Format-Table -AutoSize

# Wide pivot: row = bench, column = config, cell = states/entries/time
$wide = @()
foreach ($b in $benches) {
    $row = [ordered]@{ Bench = $b }
    foreach ($cfg in $configs) {
        $label = $cfg[0]
        $r = $results | Where-Object { $_.Bench -eq $b -and $_.Config -eq $label } | Select-Object -First 1
        if ($r) {
            $row[$label] = "$($r.States)/$($r.Entries)/$($r.Time)"
        } else {
            $row[$label] = "-"
        }
    }
    $wide += [pscustomobject]$row
}

Write-Host ""
Write-Host "===== Wide format (states/entries/time) =====" -ForegroundColor Yellow
$wide | Format-Table -AutoSize

$csvPath = "Exact/results.csv"
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding utf8
Write-Host "CSV written to $csvPath"

Write-Host "Plotting ..." -ForegroundColor Cyan
python plot_results.py $csvPath
