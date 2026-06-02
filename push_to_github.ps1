# Push TextSQL project to GitHub repository
# Usage: Run this script from the project root in PowerShell.
# It will prompt for confirmation before committing and pushing.

param(
    [string]$RepoUrl = "https://github.com/prasadk2304/Text-To-SQL.git",
    [string]$Branch = "main",
    [switch]$DryRun
)

function Exec($cmd) {
    Write-Host "$ $cmd"
    $res = & cmd /c $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Command failed: $cmd"
        exit $LASTEXITCODE
    }
    return $res
}

Write-Host "This will add, commit, and push the current project to: $RepoUrl on branch $Branch"
if (-not (Read-Host "Proceed? (y/n)") -eq 'y') {
    Write-Host "Aborted by user."
    exit 0
}

if ($DryRun) {
    Write-Host "Dry run: showing git status"
    Exec "git status --short"
    exit 0
}

# Initialize git if needed
if (-not (Test-Path ".git")) {
    Write-Host "No git repo found. Initializing..."
    Exec "git init"
}

# Add remote if missing or different
$remotes = git remote -v 2>$null
if (-not $remotes -or ($remotes -notmatch $RepoUrl)) {
    Write-Host "Setting remote origin to $RepoUrl"
    # Remove existing origin if present
    if (git remote get-url origin 2>$null) {
        Exec "git remote remove origin"
    }
    Exec "git remote add origin $RepoUrl"
}

# Add all files, commit
Exec "git add ."
$commitMsg = Read-Host "Enter commit message (default: 'Add project files')"
if (-not $commitMsg) { $commitMsg = 'Add project files' }
Exec "git commit -m \"$commitMsg\""

# Ensure branch
Exec "git branch -M $Branch"

# Push (this will prompt for credentials if required)
Exec "git push -u origin $Branch"

Write-Host "Push complete. If you need to authenticate, use a Personal Access Token or GitHub CLI (gh auth login)."
