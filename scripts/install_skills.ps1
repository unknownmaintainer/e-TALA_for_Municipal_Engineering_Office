# PowerShell Script to install all 50 Dev-Stack skills into .agents/skills
$SourceDir = "c:\Users\Dion\Desktop\eTala\Dev-Stack-Agents-main\Dev-Stack-Agents-main"
$TargetBaseDir = "c:\Users\Dion\Desktop\eTala\.agents\skills"

if (-not (Test-Path $TargetBaseDir)) {
    New-Item -ItemType Directory -Path $TargetBaseDir -Force | Out-Null
}

$files = Get-ChildItem -Path $SourceDir -Filter "*.md"
$count = 0

foreach ($file in $files) {
    if ($file.Name -ne "README.md" -and $file.Name -ne "LICENSE") {
        $agentName = $file.BaseName
        $targetDir = Join-Path $TargetBaseDir $agentName
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        $targetFile = Join-Path $targetDir "SKILL.md"
        Copy-Item -Path $file.FullName -Destination $targetFile -Force
        $count++
        Write-Host "Installed skill: $agentName -> $targetFile"
    }
}

Write-Host "`nSuccessfully installed $count Dev-Stack skills into .agents/skills!"
