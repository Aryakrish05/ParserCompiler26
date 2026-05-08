# Runs every Ternary benchmark with field_min ON and OFF, captures
# states/entries/time from runner.py's stderr, and prints a summary table.
# Run from STMGen/.
# Settings shared across all runs: not_always_extract=ON, constant_synthesis=OFF.
# Each run is bounded by $timeoutSec (15 min); anything that exceeds it is
# killed and reported as TIMEOUT in the table.

$timeoutSec = 20 * 60

$benchmarks = @(
    @{ name = "single_if_else";      max_states = 8; max_entries = 8 },
    @{ name = "multiple_if";         max_states = 8; max_entries = 8 },
    @{ name = "check_after_extract"; max_states = 8; max_entries = 8 },
    @{ name = "nested_if_else2";     max_states = 8; max_entries = 8 },
    @{ name = "nested_if_else1";     max_states = 8; max_entries = 8 }
)

$results = @()

foreach ($b in $benchmarks) {
    foreach ($fm in @("ON","OFF")) {
        $suffix     = if ($fm -eq "ON") { "min" } else { "nomin" }
        $parserPath = "Ternary/$($b.name).parser"
        $output     = "Ternary/$($b.name)_$suffix.p4"
        $errFile = [System.IO.Path]::GetTempFileName()
        $outFile = [System.IO.Path]::GetTempFileName()

        Write-Host "[run] $($b.name)  field_min=$fm  ..." -NoNewline

        $argList = @(
            "runner.py",
            "--input", $parserPath,
            "--not_always_extract", "ON",
            "--constant_synthesis", "OFF",
            "--field_min", $fm,
            "--max_states", $b.max_states,
            "--max_entries", $b.max_entries,
            "--output", $output
        )

        $p = Start-Process -FilePath python -ArgumentList $argList `
                           -NoNewWindow -PassThru `
                           -RedirectStandardError $errFile `
                           -RedirectStandardOutput $outFile

        $finished = $p.WaitForExit($timeoutSec * 1000)

        $states  = "-"
        $entries = "-"
        $time    = "-"

        if (-not $finished) {
            try { $p.Kill() } catch {}
            $status = "TIMEOUT"
        } elseif ($p.ExitCode -eq 0) {
            $status = "ok"
        } else {
            $status = "FAIL($($p.ExitCode))"
        }

        if ($finished -and (Test-Path $errFile)) {
            foreach ($line in Get-Content $errFile) {
                if ($line -match "^states=(\d+)")    { $states  = $Matches[1] }
                if ($line -match "^entries=(\d+)")   { $entries = $Matches[1] }
                if ($line -match "^time=([\d\.]+)")  { $time    = $Matches[1] }
            }
        }

        if (Test-Path $errFile) { Remove-Item $errFile -Force }
        if (Test-Path $outFile) { Remove-Item $outFile -Force }

        if ($status -eq "TIMEOUT" -and (Test-Path $output)) {
            Remove-Item $output -Force  # discard partial / stale output
        }

        Write-Host " $status (states=$states entries=$entries time=$time)"

        $results += [PSCustomObject]@{
            Benchmark = $b.name
            FieldMin  = $fm
            States    = $states
            Entries   = $entries
            "Time(s)" = $time
            Status    = $status
            P4        = if ($status -eq "TIMEOUT") { "-" } else { $output }
        }
    }
}

Write-Host ""
Write-Host "=== Summary ==="
$results | Format-Table -AutoSize