# ════════════════════════════════════════════════════════════
#  ספריית הסקילים של טל בשור — סדנת Claude Code Business
#  Windows / PowerShell
#
#  התקנת סקיל בודד:   $env:SKILLS='<skill-name>'; irm <url> | iex
#  התקנת כמה סקילים:   $env:SKILLS='<name1> <name2>'; irm <url> | iex
#  התקנת הכל:         irm <url> | iex
#
#  מוריד את הספרייה כ-ZIP ולא דרך git, כדי שלא יידרש git מותקן.
# ════════════════════════════════════════════════════════════

$ErrorActionPreference = 'Stop'

$ZipUrl = 'https://github.com/talbs1988-dotcom/claude-skills-shareable/archive/refs/heads/main.zip'
$Dest   = Join-Path (Join-Path $HOME '.claude') 'skills'

# ── אילו סקילים להתקין ───────────────────────────────────────
$want = @()
if ($args.Count -gt 0) {
  $want = $args
} elseif ($env:SKILLS) {
  $want = $env:SKILLS -split '[,\s]+' | Where-Object { $_ -ne '' }
}

if ($want.Count -gt 0) {
  Write-Host "📥 מתקין: $($want -join ', ')"
} else {
  Write-Host '📥 מתקין את כל הסקילים של טל...'
}

# ── הורדה ────────────────────────────────────────────────────
$Tmp = Join-Path ([System.IO.Path]::GetTempPath()) ("talbs-skills-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null
$Zip = Join-Path $Tmp 'skills.zip'

try {
  Invoke-WebRequest -Uri $ZipUrl -OutFile $Zip -UseBasicParsing
} catch {
  Write-Host '❌ ההורדה נכשלה. ודאו חיבור לאינטרנט ונסו שוב.' -ForegroundColor Red
  Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
  exit 1
}

try {
  Expand-Archive -Path $Zip -DestinationPath $Tmp -Force
} catch {
  Write-Host '❌ פתיחת הקובץ נכשלה.' -ForegroundColor Red
  Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue
  exit 1
}

# ── העתקה ────────────────────────────────────────────────────
New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$found = Get-ChildItem -Path $Tmp -Filter 'SKILL.md' -Recurse -File |
         Where-Object { $_.FullName -notmatch '[\/]\.git[\/]' } |
         ForEach-Object { $_.Directory }

$installed = @()
foreach ($dir in $found) {
  $name = $dir.Name
  if ($want.Count -eq 0 -or ($want -contains $name)) {
    $target = Join-Path $Dest $name
    if (Test-Path $target) { Remove-Item $target -Recurse -Force }
    Copy-Item -Path $dir.FullName -Destination $target -Recurse -Force
    Write-Host "  ✓ $name"
    $installed += $name
  }
}

Remove-Item $Tmp -Recurse -Force -ErrorAction SilentlyContinue

# ── סיכום ────────────────────────────────────────────────────
if ($installed.Count -eq 0) {
  Write-Host "❌ לא נמצא בספרייה: $($want -join ', ')" -ForegroundColor Red
  exit 1
}

Write-Host ''
if ($installed.Count -eq 1) {
  Write-Host "✅ הסקיל '$($installed[0])' הותקן בהצלחה (רק הוא)."
} else {
  Write-Host "✅ הותקנו $($installed.Count) סקילים."
}

foreach ($w in $want) {
  if ($installed -notcontains $w) {
    Write-Host "⚠️ לא נמצא בספרייה: $w" -ForegroundColor Yellow
  }
}

Write-Host '🔄 הפעילו מחדש את Claude Code (Ctrl+Shift+P → Reload Window) כדי שהסקיל ייטען.'
