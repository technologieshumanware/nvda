# NVDA Translation Branch Merge Script
#
# This script merges translation files (.po) between the current branch and a target branch
# while preserving existing translations from the current branch.
#
# Process:
# 1. Backs up all nvda.po files from the current branch
# 2. Performs git merge with the target branch
# 3. Accepts all .po files from target branch (--theirs)
# 4. Uses msgcat to merge current branch translations with target branch,
#    prioritizing current branch translations (--use-first)
# 5. Stages merged .po files and .xliff files from target branch
#
# Usage: .\backup-and-merge.ps1 <target-branch-name>
# Example: .\backup-and-merge.ps1 branch-release-2026.1beta13
#
# Requirements:
# - Must be run from source/humanware directory
# - Target branch must exist locally
# - msgcat (GNU gettext) must be available in PATH
#

param(
    [Parameter(Mandatory=$true)]
    [string]$MergeBranch
)

# Get current git branch name
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to get current git branch. Make sure you're in a git repository."
    exit 1
}

# Check if merge target branch exists
git show-ref --verify --quiet "refs/heads/$MergeBranch"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Branch '$MergeBranch' does not exist locally"
    exit 1
}

# Find all nvda.po files in source subdirectories
Write-Host "Searching for nvda.po files" -ForegroundColor Cyan

$localePath = (Resolve-Path "../locale").Path
$poFiles = Get-ChildItem -Path $localePath -Recurse -Filter "nvda.po" -File
if ($poFiles.Count -eq 0) {
    Write-Error "No .po files were found in $localePath, branch: $currentBranch"
    exit 1
}

# Temporary directory where all nvda.po files from current branch are copied
$localeDir = New-Item -ItemType Directory -Path $currentBranch -Force

foreach ($poFile in $poFiles) {
    # Get the locale code from the file path and create destination file path
    # ex: ".../source/locale/fr/LC_MESSAGES/nvda.po" -> ".../source/humanware/<branch name>/fr/nvda.po"
    $split = $poFile.FullName -split '\\'
    $index = [array]::IndexOf($split, "LC_MESSAGES") - 1
    $destinationDir = Join-Path $localeDir.FullName $split[$index]
    $destinationFile = Join-Path $destinationDir $poFile.Name

    # Create destination directory
    New-Item -ItemType Directory -Path $destinationDir -Force | Out-Null
    
    # Copy file to backup location
    Write-Host "Copying to $destinationFile"
    Copy-Item $poFile.FullName $destinationFile -Force
}

# Perform git merge from current branch to target branch
Write-Host "`nPerform git merge with branch: $MergeBranch" -ForegroundColor Cyan
git merge $MergeBranch

# Perform checkout of all nvda.po files from target branch
Write-Host "`nPerform git checkout of all nvda.po files from target branch" -ForegroundColor Cyan
git checkout $localePath/**/nvda.po $localePath/**/NVDA.po --theirs

# From each nvda.po files previously copied from current branch, perform a msgcat to concatenate and merge
# changes between current branch and target branch
# https://www.gnu.org/software/gettext/manual/html_node/msgcat-Invocation.html
Write-Host "`nPerform msgcat from previously copied nvda.po files to concatenate and merge changes to target nvda.po files" -ForegroundColor Cyan
foreach ($poFile in $poFiles) {
    $split = $poFile.FullName -split '\\'
    $index = [array]::IndexOf($split, "LC_MESSAGES") - 1
    $locale = $split[$index]

    $sourceDir = Join-Path $localeDir $locale
    $sourcePo = Get-ChildItem -Path $sourceDir -Filter "nvda.po" -File
    if (-not $sourcePo) {
        Write-Warning ("Could not find path to $sourceDir, skip .po merge for $locale")
        continue
    }

    msgcat --use-first $sourcePo.FullName $poFile.FullName -o $poFile.FullName
}

Write-Host "Perform stating all nvda.po files" -ForegroundColor Cyan
git add $localePath/**/nvda.po

Write-Host "`nPerform git checkout and stating of all *.xliff files from target branch" -ForegroundColor Cyan
$base = git rev-parse --show-toplevel
git checkout $base/*.xliff --theirs
git add $base/*.xliff

# Delete temporary directory containing nvda.po files from previous steps
Remove-Item -Path $localeDir -Recurse -Force -ErrorAction SilentlyContinue

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nScript completed successfully!" -ForegroundColor Green
} else {
    Write-Error "`nScript encountered issues."
}
