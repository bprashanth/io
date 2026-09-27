param([Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
function Capture($Name, [scriptblock]$Command) {
  try { & $Command | ConvertTo-Json -Depth 6 | Set-Content -Encoding utf8 (Join-Path $Out "$Name.json") }
  catch { @{error=$_.Exception.Message} | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $Out "$Name.json") }
}
Capture 'os' { Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture,ProductType }
Capture 'account' {
 $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
 $principal=[Security.Principal.WindowsPrincipal]::new($identity)
 @{name=$identity.Name; sid=$identity.User.Value; administrator=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); userProfile=$env:USERPROFILE; sessionId=[Diagnostics.Process]::GetCurrentProcess().SessionId}
}
Capture 'uac' { Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System' | Select-Object EnableLUA,ConsentPromptBehaviorAdmin,ConsentPromptBehaviorUser }
Capture 'volumes' { Get-Volume | Select-Object DriveLetter,FileSystem,DriveType,HealthStatus }
Capture 'defender' { Get-MpComputerStatus | Select-Object AMServiceEnabled,AntivirusEnabled,RealTimeProtectionEnabled,AMProductVersion }
Capture 'firewall' { Get-NetFirewallProfile | Select-Object Name,Enabled,DefaultInboundAction,DefaultOutboundAction }
Capture 'codex-firewall' { Get-NetFirewallRule -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'codex' } | Select-Object DisplayName,Enabled,Direction,Action,Profile }
Capture 'codex-users' { Get-LocalUser | Where-Object { $_.Name -match 'codex' } | Select-Object Name,Enabled,SID }
# Never collect user password caches, .sandbox-secrets, auth.json or full environment.
