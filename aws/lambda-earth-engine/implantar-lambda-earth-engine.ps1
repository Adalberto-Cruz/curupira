# Curupira - cria (ou atualiza) a Lambda do Earth Engine e liga no API Gateway.
# Rode no PowerShell, com a AWS CLI já configurada com as credenciais do Learner Lab.
# O login do Earth Engine é lido do seu PC e vai direto para a Lambda (não aparece na tela).

# Continue: o PowerShell 5 trata aviso da AWS CLI como erro; os erros reais sao checados com $LASTEXITCODE
$ErrorActionPreference = 'Continue'
$pasta   = Split-Path -Parent $MyInvocation.MyCommand.Path
$zip     = Join-Path $pasta 'curupira-ee-lambda.zip'
$fn      = 'curupira-earth-engine'
$api     = 'nksewwbo9c'
$regiao  = 'us-east-1'
$envSite = 'C:\Users\user\Downloads\ibama\Hibama\site-hibama\.env'
$credEE  = Join-Path $env:USERPROFILE '.config\earthengine\credentials'

function Checar($msg) { if ($LASTEXITCODE -ne 0) { throw $msg } }

# 1) confere os arquivos antes de mexer na AWS
if (!(Test-Path $zip))     { throw "Pacote nao encontrado: $zip" }
if (!(Test-Path $credEE))  { throw "Login do Earth Engine nao encontrado em $credEE. Rode 'earthengine authenticate' e tente de novo." }
if (!(Test-Path $envSite)) { throw "Arquivo .env nao encontrado: $envSite" }
$linha = Get-Content $envSite | Where-Object { $_ -match '^\s*GOOGLE_CLOUD_PROJECT\s*=' } | Select-Object -First 1
if (!$linha) { throw 'GOOGLE_CLOUD_PROJECT nao esta no .env' }
$projeto = ($linha -split '=', 2)[1].Trim().Trim('"')
$cred = (Get-Content $credEE -Raw).Trim()
try { $null = $cred | ConvertFrom-Json } catch { throw 'Arquivo de credenciais do Earth Engine nao e um JSON valido.' }

$conta = aws sts get-caller-identity --query Account --output text; Checar 'AWS CLI sem credenciais validas. Atualize as credenciais do Learner Lab.'
$conta = $conta.Trim()
$role = "arn:aws:iam::${conta}:role/LabRole"
Write-Host "Conta AWS: $conta"

# 2) variáveis da Lambda num arquivo temporário (apagado no final)
$tmp = [IO.Path]::GetTempFileName()
$json = @{ Variables = @{ EE_CREDENTIALS = $cred; GOOGLE_CLOUD_PROJECT = $projeto } } | ConvertTo-Json -Depth 4 -Compress
[IO.File]::WriteAllText($tmp, $json)
$envArg = "file://$tmp"

try {
  $null = aws lambda get-function --function-name $fn --region $regiao 2>&1
  if ($LASTEXITCODE -eq 0) {
    Write-Host 'Atualizando a Lambda...'
    aws lambda update-function-code --function-name $fn --zip-file "fileb://$zip" --region $regiao --output text --query LastUpdateStatus; Checar 'Falha ao atualizar o codigo'
    aws lambda wait function-updated-v2 --function-name $fn --region $regiao
    aws lambda update-function-configuration --function-name $fn --environment $envArg --timeout 29 --memory-size 1024 --region $regiao --output text --query LastUpdateStatus; Checar 'Falha ao atualizar a configuracao'
    aws lambda wait function-updated-v2 --function-name $fn --region $regiao
  } else {
    Write-Host 'Criando a Lambda...'
    aws lambda create-function --function-name $fn --runtime python3.12 --handler lambda_function.handler --role $role --zip-file "fileb://$zip" --timeout 29 --memory-size 1024 --environment $envArg --region $regiao --output text --query State; Checar 'Falha ao criar a Lambda (confira se o Learner Lab esta ligado)'
    aws lambda wait function-active-v2 --function-name $fn --region $regiao
  }
} finally {
  Remove-Item $tmp -Force -ErrorAction SilentlyContinue
}

$lambdaArn = (aws lambda get-function --function-name $fn --region $regiao --query Configuration.FunctionArn --output text).Trim()

# 3) rota GET /api/earth-engine no API Gateway apontando para a Lambda
$rota = aws apigatewayv2 get-routes --api-id $api --region $regiao --query "Items[?RouteKey=='GET /api/earth-engine'].RouteId" --output text
if (!$rota -or $rota.Trim() -eq '' -or $rota.Trim() -eq 'None') {
  Write-Host 'Criando rota no API Gateway...'
  $int = aws apigatewayv2 create-integration --api-id $api --integration-type AWS_PROXY --integration-uri $lambdaArn --payload-format-version 2.0 --timeout-in-millis 29000 --region $regiao --query IntegrationId --output text; Checar 'Falha ao criar a integracao'
  aws apigatewayv2 create-route --api-id $api --route-key 'GET /api/earth-engine' --target "integrations/$($int.Trim())" --region $regiao --output text --query RouteId; Checar 'Falha ao criar a rota'
} else { Write-Host 'Rota ja existe.' }

# 4) deixa o API Gateway chamar a Lambda (se já existir, só ignora)
aws lambda add-permission --function-name $fn --statement-id apigw-earth-engine --action lambda:InvokeFunction --principal apigateway.amazonaws.com --source-arn "arn:aws:execute-api:${regiao}:${conta}:${api}/*/*/api/earth-engine" --region $regiao 2>&1 | Out-Null

# 5) publica, se o estágio não publica sozinho
$auto = aws apigatewayv2 get-stages --api-id $api --region $regiao --query "Items[?StageName=='`$default'].AutoDeploy" --output text
if ($auto -and $auto.Trim() -ne 'True') { aws apigatewayv2 create-deployment --api-id $api --stage-name '$default' --region $regiao --output text --query DeploymentId }

# 6) teste rápido (Manaus, cor natural)
Write-Host 'Testando (pode levar ate 30 s)...'
Start-Sleep -Seconds 5
try {
  $r = Invoke-RestMethod "https://$api.execute-api.$regiao.amazonaws.com/api/earth-engine?municipio=1302603&start=2026-06-01&end=2026-10-31&product=rgb&cloud=40"
  Write-Host "OK: $($r.count) cenas Sentinel-2. Earth Engine funcionando na AWS."
} catch {
  Write-Host "Teste falhou: $($_.Exception.Message)"
  Write-Host "Veja o log: aws logs tail /aws/lambda/$fn --since 10m --region $regiao"
}
