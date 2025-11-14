<#
.SYNOPSIS
    Synchronize a local forked package with the latest version on PyPI using uv and Git.
.DESCRIPTION
    This script downloads the latest source distribution (sdist) of a package from PyPI,
    extracts it into the 'upstream' branch, merges into master, builds with uv, and tags.
.PARAMETER PackageName
    The PyPI name of the package (e.g., 'requests').
.PARAMETER MainBranch
    The name of your main branch (default: 'master').
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$PackageName,
    [string]$MainBranch = "master"
)

$ErrorActionPreference = "Stop"

Write-Host "🔍 Checking for latest version of $PackageName on PyPI..." -ForegroundColor Cyan

# Get the latest version info from PyPI JSON API
$pypiInfo = Invoke-RestMethod -Uri "https://pypi.org/pypi/$PackageName/json"
$latestVersion = $pypiInfo.info.version
$sdistUrl = $pypiInfo.releases.$latestVersion | Where-Object { $_.packagetype -eq "sdist" } | Select-Object -ExpandProperty url

Write-Host "📦 Latest version is $latestVersion"
Write-Host "⬇️ Downloading source from $sdistUrl"

$tempDir = New-Item -ItemType Directory -Force -Path "$env:TEMP\$PackageName-$latestVersion"
$sdistFile = "$tempDir\package.tar.gz"

Invoke-WebRequest -Uri $sdistUrl -OutFile $sdistFile

Write-Host "📂 Extracting package..."
tar -xzf $sdistFile -C $tempDir

$extracted = Get-ChildItem -Directory $tempDir | Where-Object { $_.Name -match "^$PackageName-" }
$sourceDir = $extracted.FullName

# Ensure clean git working directory
if ((git status --porcelain).Length -ne 0) {
    Write-Error "❌ Working directory not clean. Commit or stash changes first."
    exit 1
}

# Switch to upstream branch and reset it to match the new package code
if (-not (git rev-parse --verify upstream 2>$null)) {
    git branch upstream
}

git checkout upstream
git rm -rf .
Copy-Item -Path "$sourceDir\*" -Destination . -Recurse -Force
git add .
git commit -m "Import upstream version $latestVersion" --allow-empty
git tag "v$latestVersion-upstream"

# Merge upstream into main branch
Write-Host "🔄 Merging upstream into $MainBranch..."
git checkout $MainBranch
git merge upstream --no-ff -m "Merge upstream $latestVersion"

# Build and sync with uv
Write-Host "⚙️ Running uv sync and build..."
uv sync
uv build

# Tag the new forked version
$forkTag = "v$latestVersion-fork1"
git tag $forkTag
Write-Host "🏷️ Tagged new version as $forkTag"

Write-Host "✅ Update complete. Review and push when ready." -ForegroundColor Green
