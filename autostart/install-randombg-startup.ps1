param(
    [string]$AppDirectory = "C:\\RandomBG"
)

$ErrorActionPreference = 'Stop'

$startupFolder = [Environment]::GetFolderPath('Startup')
if (-not (Test-Path -Path $startupFolder)) {
    throw "Konnte den Autostart-Ordner nicht ermitteln."
}

$shortcutPath = Join-Path -Path $startupFolder -ChildPath 'RandomBG.lnk'
$startupBat = Join-Path -Path $AppDirectory -ChildPath 'autostart\start-randombg-windows.bat'

if (-not (Test-Path -Path $startupBat)) {
    throw "Startup-Skript nicht gefunden unter '$startupBat'. Stelle sicher, dass RandomBG nach '$AppDirectory' kopiert wurde."
}

$wshShell = New-Object -ComObject WScript.Shell
$shortcut = $wshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $startupBat
$shortcut.WorkingDirectory = $AppDirectory
$shortcut.Description = 'RandomBG automatisch beim Anmelden starten'
$shortcut.Save()

Write-Output "Shortcut erstellt/aktualisiert: $shortcutPath"
