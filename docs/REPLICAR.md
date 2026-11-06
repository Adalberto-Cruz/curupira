# Replicar o Hibama

Referência: 06/11/2026. Este guia descreve o código disponível e seus dados externos. O escopo aprovado é nacional; CAR e camadas ambientais ainda usam o pipeline AM. Um clone não contém todos os produtos ignorados nem gera uma versão nacional com os scripts atuais.

## Ambiente e diretórios

Use Python 3.13 no `.venv` do repositório, nunca o conda base. Reutilize o ambiente existente. Em outra máquina, a criação do ambiente e a instalação das dependências devem ser feitas pelo responsável, conforme `LEIA-ME.md` e `requirements.txt`. Não há instalação automática neste trabalho.

Estrutura esperada pelos scripts atuais:

```text
Hibama/
  dados/amazonas/brutos/       # SICAR, IBGE e camadas ambientais
  dados/amazonas/processados/  # CAR consolidado
  dados/brasil/brutos/focos/
  dados/brasil/processados/focos/
  site-hibama/                 # raiz dos comandos abaixo
    .venv/
    dist/
    scripts/
    tools/
    work/                     # provas e intermediários ignorados
```

Preserve originais e manifestos com URL, período, data de acesso, CRS, contagem, tamanho e SHA-256. Não versionar `.env`, credenciais, `.venv`, `acesso-local/`, brutos ou produtos pesados. Identificar imóveis só pelo código CAR; não publicar nomes de titulares, CPF ou CNPJ. Os comandos de preparação abaixo regeneram produtos do site: execute-os apenas para reprodução autorizada, em cópia de trabalho própria. Eles não foram executados nesta prova.

## Fontes

| Produto | Fonte | Observação para reproduzir |
|---|---|---|
| CAR AM | [SICAR](https://consulta.car.gov.br/), WFS usado pelo coletor `https://geoserver.car.gov.br/geoserver/sicar/wfs` | `scripts/baixar_car_amazonas.ps1` registra esquema, contagens e lotes; chama o consolidador. Não foi identificada licença/termos publicados para AREA_IMOVEL. Falha TLS não deve ser contornada desativando validação. |
| Malhas 2025 | [IBGE](https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/) | AM: `AM_Municipios_2025.zip`; nacional: `Brasil/BR_Municipios_2025.zip`. |
| TI | [Funai](https://www.gov.br/funai/pt-br/atuacao/terras-indigenas/geoprocessamento-e-mapas) | Preparador espera `funai_am.json`; conferir versão e extração. |
| Processos minerários | [ANM/SIGMINE](https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/) | Preparador espera `anm_am.zip`; registro administrativo não prova lavra. |
| PRODES e DETER | [TerraBrasilis/INPE](https://terrabrasilis.dpi.inpe.br/) | PRODES AM pelo coletor de camadas; DETER pelo coletor por ano, que trata IDs históricos. Derivados redistribuídos: CC BY-SA 4.0, conforme auditoria. DETER cobre Amazônia Legal e Cerrado. |
| Embargos atuais | [Cópia IPAAM de Ibama/Pamgia](https://gis.ipaam.am.gov.br/server/rest/services/AREAS_EMBARGADAS_IBAMA_AM_PAMGIA/FeatureServer/0) | É a entrada atual AM; não confundir com base nacional. Migração planejada para [Ibama oficial](https://dadosabertos.ibama.gov.br/dataset/fiscalizacao-termo-de-embargo), incluindo histórico. |
| Focos | [INPE/BDQueimadas](https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/) | Série nacional de referência AQUA_M-T; preservar o recorte do manifesto. A camada AM antiga usa todos os satélites e não é comparável. |

A cópia nacional [Source Cooperative](https://source.coop/tristangruppwri/cadastral/brazil-car-area-imovel) teve seus metadados verificados; a adoção e a auditoria do Parquet permanecem pendentes em `PENDENCIAS.md`. Não usar contagem de linhas como contagem de imóveis únicos. Fontes futuras de UC, INCRA, CNFP, APP, IA e carbono estão no plano; não há pipeline nacional completo dessas fontes neste guia.

## Ordem do pipeline existente

1. Obter/restaurar os dados de origem e seus manifestos. O clone sozinho não basta. Conferir os arquivos de Funai/ANM, malha AM e focos AM antigos exigidos por `tools/preparar_ambiental.py`; nem toda aquisição antiga possui coletor reproduzível no repositório.
2. Coletar CAR AM com `scripts/baixar_car_amazonas.ps1`, que já chama `scripts/consolidar_car_amazonas.py`. Se restaurar lotes e manifesto íntegros, executar somente o consolidador.
3. Executar os preparadores AM, depois verificar os produtos. O coletor genérico de camadas também baixa DETER pelo método antigo; se usado para PRODES/embargos, executar obrigatoriamente o coletor DETER por ano depois e antes do preparador ambiental.

```powershell
# Na raiz do repositório; somente para regeneração autorizada.
.\.venv\Scripts\python.exe scripts\consolidar_car_amazonas.py
.\.venv\Scripts\python.exe tools\preparar_dados.py
.\.venv\Scripts\python.exe scripts\coletar_camadas_ambientais.py
.\.venv\Scripts\python.exe scripts\coletar_deter_por_ano.py
.\.venv\Scripts\python.exe tools\preparar_ambiental.py
.\.venv\Scripts\python.exe tools\verificar_dados.py
.\.venv\Scripts\python.exe tools\verificar_ambiental.py
.\.venv\Scripts\python.exe tools\verificar_paleta.py
```

4. Gerar os focos nacionais e, então, o índice de busca. O lote documentado usa anuais 2003–2025 e mensais de 2026; não ampliar o período automaticamente.

```powershell
.\.venv\Scripts\python.exe scripts\coletar_focos_brasil.py --ate 2026-11-06
.\.venv\Scripts\python.exe tools\preparar_focos_brasil.py
.\.venv\Scripts\python.exe tools\verificar_focos_brasil.py
.\.venv\Scripts\python.exe tools\preparar_busca.py
.\.venv\Scripts\python.exe tools\verificar_busca.py
```

5. Executar os testes Python/JavaScript e `git diff --check`. Conferir contagens, hashes, cobertura, interseções e ausência de dados pessoais. Testes unitários não substituem auditoria espacial. Antes de cada commit, apresentar lista de arquivos e diff stat e aguardar confirmação. Nunca push automático.

Para servir o site, usar `tools/iniciar-hibama.ps1`, conforme `LEIA-ME.md`. Earth Engine é opcional: fornecer o projeto por configuração local/ambiente, sem ID fixo no código. Não copiar credenciais para `dist/`.

## Provas isoladas de PMTiles e MapLibre

Parte 1: `PROVA_PMTILES_ETAPA4_1.md`, com preparação, geração Tippecanoe, auditoria e medidas anteriores. Parte 2: `PROVA_MAPLIBRE_ETAPA4_2.md`, ainda sem medições de navegador concluídas. Não executar preparadores do aplicativo para testar a parte 2: ela reutiliza o PMTiles do AM, sem regravar os dados do site.

```powershell
.\.venv\Scripts\python.exe tools\prova_maplibre_bibliotecas.py
.\.venv\Scripts\python.exe tools\prova_maplibre_servidor.py --port 8775
```

Abrir `http://127.0.0.1:8775/prova-maplibre.html`; a mesma porta serve `prova-pmtiles.html`. A porta 8766 do servidor atual não fornece Range e não foi modificada. Bibliotecas com versão/hash fixos, dados, manifestos e logs ficam em `work/`, fora do commit. A licença PMTiles é conferida por hash, embora seu endereço upstream ainda aponte para `main`; se mudar, revisar a licença, sem aceitar automaticamente o novo hash.

Para MT/PA, primeiro obter uma extração completa da UF em GeoJSON EPSG:4326 e registrar origem, versão, data e auditoria. Os dados não estão disponíveis localmente nesta etapa. `tools/prova_maplibre_estado.py` aceita propriedades `code/status`, `cod_imovel/status_imovel` ou `cod_imovel/ind_status`, restringe a saída a código/situação/geometria e interrompe em códigos duplicados. Não converte `des_condic` em situação. Não é coletor nem resolve duplicações por conta própria.

```powershell
.\.venv\Scripts\python.exe tools\prova_maplibre_estado.py --entrada 'C:\pasta\MT.geojson' --uf MT --origem 'URL, versão e data da extração'
```

No Ubuntu/WSL existente, sem instalação de ferramentas, usar o binário já compilado. Os caminhos abaixo são do computador desta prova; adaptar em outra máquina:

```sh
export TIPPECANOE=/tmp/hibama-prova-pmtiles-20261106/tippecanoe/tippecanoe
export PROVA_DIR=/mnt/c/Users/user/Downloads/ibama/Hibama/site-hibama/work/prova-maplibre
export PROVA_UF=mt
sh /mnt/c/Users/user/Downloads/ibama/Hibama/site-hibama/tools/prova_maplibre_estado_gerar.sh
```

O script recusa sobrescrever um PMTiles existente. Depois, na prova, escolher a UF e usar “Abrir estado extra”; medir três aberturas. Validar os tiles e imóveis pequenos da UF antes de tirar conclusões nacionais. Falta implementar uma auditoria completa dos tiles adicionais e executar essa rodada: não declarar a Etapa 4 parte 2 concluída apenas porque o arquivo foi gerado.

## Hospedagem

O código estático fica em `dist/`; o destino permanente planejado é GitHub Pages, cujo limite publicado de site é 1 GB. O acervo nacional pesado ficará fora do Git/Pages: S3 do Learner Lab para a apresentação; avaliar depois R2 ou Azure com crédito do Student Pack, sem ativar agora. A disponibilidade após encerrar o lab precisa ser testada.

No host dos PMTiles, validar GET/HEAD e `Range: bytes=0-126`: resposta 206, 127 bytes e `Content-Range` coerente. Para domínio diferente, configurar e testar CORS para a origem do site, incluindo Range e exposição dos cabeçalhos necessários ao protocolo. Não aplicar compressão HTTP dinâmica ao arquivo PMTiles: offsets referem-se aos bytes do arquivo. Preservar tipo MIME, ETag, hashes e versão no manifesto. Validar Range no host final e em rede externa antes de apresentar.

Os `.gz` dos focos são binários descomprimidos pela interface: servir sem `Content-Encoding: gzip`. Incluir os produtos ignorados necessários no pacote de hospedagem, sem incluir credenciais ou brutos. Nenhuma publicação, ativação de nuvem ou push foi executado neste trabalho.
