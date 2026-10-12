# Instala (ou remove, com -Remover) a tarefa que roda o agente do botao "Atualizar" a cada
# minuto, sem janela, enquanto o Silvio estiver logado (a leitura da pasta do RMR usa a sessao
# dele). Rode da raiz do projeto:
#   powershell -ExecutionPolicy Bypass -File deploy\agente-instalar.ps1
#   powershell -ExecutionPolicy Bypass -File deploy\agente-instalar.ps1 -Remover
param([switch]$Remover)

$nome = 'Farol de Metas - Atualizar'
if ($Remover) {
  Unregister-ScheduledTask -TaskName $nome -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output "Tarefa '$nome' removida."
  exit 0
}

$raiz = Split-Path -Parent $PSScriptRoot
$script = Join-Path $raiz 'etl\agente_atualizacao.py'
$python = (Get-Command python -ErrorAction Stop).Source
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $python }

$acao = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`"" -WorkingDirectory $raiz
$gatilho = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)
$config = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable `
  -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName $nome -Action $acao -Trigger $gatilho -Settings $config `
  -Description 'Le os farois na pasta do RMR quando alguem clica Atualizar no site do Farol de Metas (173:3007).' -Force | Out-Null
Write-Output "Tarefa '$nome' instalada: $pythonw $script (a cada minuto)."
