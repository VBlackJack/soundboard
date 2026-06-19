#
# Copyright 2026 Julien Bombled
# Licensed under the Apache License, Version 2.0.
#
# Initializes the local Git repository and pushes the SoundBoard project to a
# GitHub remote. Run from the repository root after the remote repo exists.
#
# Usage:
#   pwsh -File tools/publish.ps1 -RemoteUrl https://github.com/<user>/soundboard.git
#
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl,

    [string]$Branch = "main",

    [string]$Message = "Initial commit: ThemeForge-themed Kaamelott soundboard (645 sounds, 16 themes)"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
Write-Host "Repository root: $root"

# Remove any stale .git directory (e.g. a partially-created one).
if (Test-Path ".git") {
    Write-Host "Removing existing .git ..."
    Remove-Item -Recurse -Force ".git"
}

git init --initial-branch=$Branch
git config user.name  "Julien Bombled"
git config user.email "jbombled@proton.me"

git add -A
git commit -m $Message

if (git remote | Select-String -Quiet "^origin$") {
    git remote set-url origin $RemoteUrl
} else {
    git remote add origin $RemoteUrl
}

git push -u origin $Branch
Write-Host "Done. Pushed to $RemoteUrl ($Branch)."
Write-Host "Next: GitHub > Settings > Pages > Source = GitHub Actions (workflow already included)."
