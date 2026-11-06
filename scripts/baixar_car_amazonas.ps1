param(
    [int]$TamanhoLote = 5000
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectRoot = Split-Path -Parent $repoRoot
$pythonExe = Join-Path $repoRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Crie o .venv e instale requirements.txt conforme o LEIA-ME.' }
$outputDir = Join-Path $projectRoot 'dados/amazonas/brutos/sicar'
$pagesDir = Join-Path $outputDir 'lotes'
$metadataDir = Join-Path $outputDir 'metadados'
New-Item -ItemType Directory -Path $pagesDir -Force | Out-Null
New-Item -ItemType Directory -Path $metadataDir -Force | Out-Null
$endpoint = 'https://geoserver.car.gov.br/geoserver/sicar/wfs'
$layer = 'sicar:sicar_imoveis_am'
$layerEncoded = [uri]::EscapeDataString($layer)

function Get-OfficialFile([string]$Url, [string]$Destination) {
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 120 -OutFile $Destination
            return
        } catch {
            if ($attempt -eq 3) { throw }
            Write-Output "Nova tentativa de download ($attempt/3)."
            Start-Sleep -Seconds (2 * $attempt)
        }
    }
}

$hitsUrl = "${endpoint}?service=WFS&version=2.0.0&request=GetFeature&typeNames=${layerEncoded}&resultType=hits"
$hitsPath = Join-Path $metadataDir 'contagem-inicial.xml'
Get-OfficialFile $hitsUrl $hitsPath
[xml]$hits = Get-Content -LiteralPath $hitsPath -Raw
if ($hits.DocumentElement.LocalName -ne 'FeatureCollection') { throw 'Resposta de contagem inesperada.' }
$expected = [int]$hits.DocumentElement.GetAttribute('numberMatched')
if ($expected -le 0) { throw 'A fonte nao informou uma contagem valida.' }

Get-OfficialFile "${endpoint}?service=WFS&version=2.0.0&request=GetCapabilities" (Join-Path $metadataDir 'capacidades.xml')
Get-OfficialFile "${endpoint}?service=WFS&version=2.0.0&request=DescribeFeatureType&typeNames=${layerEncoded}" (Join-Path $metadataDir 'esquema.xsd')

$manifestPath = Join-Path $outputDir 'extracao.json'
$manifest = [ordered]@{
    fonte = 'SICAR - servico WFS publico'
    endpoint = $endpoint
    camada = $layer
    crs = 'EPSG:4326'
    inicio_utc = [DateTime]::UtcNow.ToString('o')
    contagem_inicial = $expected
    tamanho_lote_solicitado = $TamanhoLote
    ordenacao = 'cod_imovel A'
    status = 'em_andamento'
    lotes = @()
    limites = @(
        'A camada publica contem perimetros e atributos cadastrais; nao contem os poligonos internos de APP e Reserva Legal.'
        'A fonte nao fornece uma transacao de snapshot; as contagens inicial e final sao conferidas.'
        'CAR declarado e situacao cadastral nao equivalem a certificacao de regularidade ambiental.'
    )
}
$offset = 0
while ($offset -lt $expected) {
    $filename = 'AM_CAR_{0:D6}.geojson' -f $offset
    $pagePath = Join-Path $pagesDir $filename
    $url = "${endpoint}?service=WFS&version=2.0.0&request=GetFeature&typeNames=${layerEncoded}&outputFormat=application%2Fjson&srsName=EPSG%3A4326&count=${TamanhoLote}&startIndex=${offset}&sortBy=cod_imovel%20A"
    if (-not (Test-Path -LiteralPath $pagePath)) {
        $partial = $pagePath + '.partial'
        Get-OfficialFile $url $partial
        Move-Item -LiteralPath $partial -Destination $pagePath -Force
    }
    $page = Get-Content -LiteralPath $pagePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($page.type -ne 'FeatureCollection') { throw "Lote invalido: $filename" }
    $returned = @($page.features).Count
    if ($returned -le 0 -or $returned -gt $TamanhoLote) { throw "Numero inesperado de registros: $filename" }
    if ([int]$page.numberMatched -ne $expected) { throw 'A contagem da fonte mudou durante a extracao.' }
    if ($returned -ne [int]$page.numberReturned) { throw "Contagem do lote inconsistente: $filename" }
    if (@($page.features | Where-Object { $_.properties.uf -ne 'AM' }).Count -gt 0) { throw 'Lote contem registro fora da UF AM.' }
    $manifest.lotes += [ordered]@{
        arquivo = 'lotes/' + $filename
        url = $url
        start_index = $offset
        registros = $returned
        bytes = (Get-Item -LiteralPath $pagePath).Length
        sha256 = (Get-FileHash -LiteralPath $pagePath -Algorithm SHA256).Hash.ToLowerInvariant()
        primeiro_codigo = $page.features[0].properties.cod_imovel
        ultimo_codigo = $page.features[$returned - 1].properties.cod_imovel
        verificado_utc = [DateTime]::UtcNow.ToString('o')
    }
    $offset += $returned
    $manifest.registros_baixados = $offset
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Write-Output "CAR Amazonas: $offset / $expected registros; lote $filename."
    $page = $null
}

$finalPath = Join-Path $metadataDir 'contagem-final.xml'
Get-OfficialFile $hitsUrl $finalPath
[xml]$finalHits = Get-Content -LiteralPath $finalPath -Raw
$finalCount = [int]$finalHits.DocumentElement.GetAttribute('numberMatched')
$manifest.contagem_final = $finalCount
$manifest.fim_utc = [DateTime]::UtcNow.ToString('o')
if ($finalCount -ne $expected -or $offset -ne $expected) {
    $manifest.status = 'contagem_divergente'
    $manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    throw 'A contagem final divergiu. Os arquivos foram preservados para verificacao.'
}
$manifest.status = 'baixado_aguardando_validacao'
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestPath -Encoding UTF8
& $pythonExe (Join-Path $PSScriptRoot 'consolidar_car_amazonas.py')
if ($LASTEXITCODE -ne 0) { throw 'A validacao final falhou.' }
