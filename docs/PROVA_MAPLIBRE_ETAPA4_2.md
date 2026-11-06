# Prova MapLibre — Etapa 4, parte 2

**Prova concluída em 06/11/2026 para AM e MT, com limitações de seleção documentadas.** Foram feitas três rodadas por cenário e formato, capturas reais, teste Esri, clique e arrasto. Decisão confirmada pelo usuário: manter Leaflet + protomaps-leaflet + PMTiles; corrigir os pequenos MT antes de migrar dados operacionais. MapLibre funciona, mas não trouxe menor tempo de conclusão nesta máquina. O usuário autorizou somente o commit dos dez arquivos da prova; APP/RL permanece parado e sem commit. Sem alteração no site atual ou push.

## Método e isolamento

Chromium 157 no navegador integrado, Windows, viewport de conteúdo 1280 × 720, loopback, servidor exclusivo 8775 sem gzip HTTP e com Cache-Control no-store. Mesma página nova, três sessões por parâmetro renderer, mesmos arquivos AM/MT. Os caches internos do renderer são recriados nas aberturas do zero; zoom/pan reutilizam a sessão. Não se trata de cache frio do sistema operacional, rede móvel ou celular. A ordem foi MapLibre → GeoJSON → protomaps; não houve randomização.

Cada sessão salvou snapshots cumulativos. Foi usado somente o último snapshot de cada formato, tomando as primeiras três linhas de cada cenário; aberturas extras para inspeção visual foram excluídas. `medianas.json` guarda as linhas escolhidas e as medianas; `sessao-maplibre.json`, `sessao-geojson.json` e `sessao-pmtiles.json` guardam os snapshots completos nos outputs desta entrega. Todas as respostas CAR das linhas escolhidas foram 206 para PMTiles e 200 para GeoJSON. Bytes são a soma de Content-Length das respostas vistas pelo fetch, não instrumentação de tráfego físico. O servidor registrou no stderr duas conexões abortadas pelo Windows (10053); os logs antigos não tinham timestamp para atribuí-las a uma rodada. Não houve erro nas linhas escolhidas ou no console final, mas não se comprova entrega integral de todo corpo apenas pelo cabeçalho. Após as medições, o servidor passou a tratar também ConnectionAbortedError e datar os registros, sem alterar dados ou o executor de medição.

A primeira tentativa MapLibre foi descartada: isSourceLoaded podia observar a câmera anterior logo após jumpTo. A espera agora exige um evento render antes de verificar a fonte; depois disso o zoom foi confirmado visualmente e as rodadas foram refeitas. Logs anteriores foram preservados. Primeiro desenho é um marcador de software (feições consultáveis no MapLibre, desenho de linhas no protomaps, construção da camada GeoJSON), não tempo físico de pixels. No GeoJSON ele não é recalculado para zoom/pan. Pronto espera CAR, não o satélite. O pan inclui uma animação de 1 s; intervalos de quadros não comprovam FPS.

Somente os dez arquivos novos da prova foram usados/alterados. A parte 1, o aplicativo e o servidor 8766 foram preservados. Dados e bibliotecas continuam em work/, fora do commit. AM PMTiles: 81.307.541 B, SHA-256 `823c0fbd968cd184f85627a04daced754a6e94ec854e189439a5ee2979f7cd69`; não regenerado.

## GeoJSON × protomaps-leaflet × MapLibre

Medianas de três rodadas novas. Bytes são corpos CAR, sem bibliotecas, Esri, manifesto ou cabeçalhos. Cada célula mostra **bytes / requisições / primeiro desenho ms / pronto ms / intervalo p95 ms**. Travessão indica marcador indisponível.

| Cenário | GeoJSON + Leaflet | protomaps-leaflet + PMTiles | MapLibre + PMTiles |
|---|---:|---:|---:|
| AM do zero | 41.254.233 / 1 / 854,0 / 953,3 / 764,4 | 1.176.338 / 12 / 41,7 / 109,7 / 24,2 | 518.089 / 6 / 82,0 / 175,0 / 6,2 |
| zoom Manaus após AM | 0 / 0 / — / 346,6 / 6,4 | 104.154 / 13 / 18,1 / 36,9 / 6,2 | 138.000 / 4 / 10,6 / 72,0 / 6,2 |
| pan 400 px / 1 s | 0 / 0 / — / 1025,7 / 6,2 | 6.378 / 6 / 212,7 / 1020,0 / 6,2 | 5.829 / 2 / 12,4 / 1035,1 / 6,2 |
| Manaus do zero | 2.279.267 / 1 / 176,0 / 179,3 / 121,4 | 120.538 / 14 / 17,6 / 35,0 / 6,2 | 163.231 / 6 / 24,5 / 72,4 / 6,2 |
| MT do zero | 145.904.977 / 1 / 2532,0 / 2794,6 / 394,4 | 1.068.254 / 10 / 26,3 / 72,9 / 6,2 | 1.144.064 / 6 / 121,9 / 302,2 / 6,2 |

GeoJSON AM combinado tem 41.254.233 B; MT, 145.904.977 B. O site atual usa municípios na visão estadual; não interpretar o GeoJSON combinado como custo atual do aplicativo. PMTiles em disco: AM 81.307.541 B; MT 172.318.612 B. O arquivo inteiro ser maior não impede transferência parcial muito menor.

MapLibre requisitou menos bytes na abertura AM (518.089 B), mas protomaps ficou pronto antes em AM (109,7 contra 175,0 ms), MT (72,9 contra 302,2 ms) e Manaus direto (35,0 contra 72,4 ms). Em MT, GeoJSON exigiu 145,9 MB e 2.794,6 ms; ambos os leitores PMTiles transferiram cerca de 1,1 MB. Esses valores sustentam uso de tiles, sem demonstrar necessidade de trocar Leaflet por MapLibre. Diferenças de níveis solicitados e critérios de desenho limitam a comparação entre motores.

## Bibliotecas e licença

MapLibre GL JS 6.16.0 e PMTiles JS 4.5.0: BSD-3-Clause. protomaps-leaflet 5.1.0: BSD-3-Clause. Tippecanoe 2.79.0: BSD-2-Clause. Versões e hashes estão fixados nos preparadores; licenças preservadas em work/. A integração segue o [exemplo oficial MapLibre](https://maplibre.org/maplibre-gl-js/docs/examples/pmtiles-source-and-protocol/); [PMTiles usa HTTP Range](https://docs.protomaps.com/pmtiles/).

| Asset MapLibre | Bytes em disco | Gzip nível 6 calculado |
|---|---:|---:|
| Módulo principal | 1.108.049 | 295.254 |
| Worker | 519.372 | 147.628 |
| Shared vazio publicado | 0 | 20 |
| CSS | 71.596 | 10.261 |
| PMTiles JS | 20.229 | 7.950 |
| Total | **1.719.246** | **461.113** |

Gzip calculado não é transferência observada; o servidor serve sem gzip. protomaps-leaflet tem bundle de 128.171 B, além do Leaflet já usado pelo site. A página comparadora ainda carrega CSS MapLibre e protocolo PMTiles no cabeçalho, inclusive nos modos Leaflet; esses bytes ficam fora da tabela CAR. Uma migração deve carregar somente as dependências necessárias.

## Avaliação visual e seleção

Esri carregou nos três formatos em AM e MT, inclusive em zoom alto com overzoom do nível nativo 16. As linhas permaneceram sobre a mesma imagem ao ampliar e arrastar; isso é coerência visual, não validação posicional de limites cadastrais. O overzoom fica borrado. As quatro cores/tracejados foram preservados nas camadas e observados nas visões estaduais; a legenda atual mostra só cores, sem reproduzir os tracejados.

O contorno branco do pequeno AM selecionado permaneceu após arrasto nos três formatos. Os cinco casos AM permitiram selecionar o código esperado; no quinto houve sobreposição e seleção explícita do candidato em ambos os leitores de tiles.

| Pequenos no ponto do manifesto, zoom equivalente 19 | GeoJSON/Leaflet | protomaps-leaflet | MapLibre |
|---|---|---|---|
| AM 1–5 | 5/5 códigos selecionados | 5/5 após escolha de candidato | 5/5 após escolha de candidato |
| MT 1 | Outro código selecionado | Esperado ausente dos candidatos | Esperado ausente dos candidatos |
| MT 2 | Esperado selecionado | Esperado ausente dos candidatos | Esperado ausente dos candidatos |
| MT 3 | Esperado selecionado | Esperado selecionado | Esperado selecionado após escolha |
| MT 4 | Outro código selecionado | Esperado selecionado após escolha | Esperado selecionado após escolha |
| MT 5 | Outro código selecionado | Esperado selecionado após escolha | Esperado selecionado após escolha |

GeoJSON não oferece painel de candidatos nesta prova; os cliques MT 1/4/5 não comprovam ausência do imóvel. Nos tiles, os dois menores MT não foram recuperados no centro, apesar de o verificador binário encontrar seus códigos no zoom 14. A causa ainda não foi isolada entre representação simplificada/quantizada e consulta; não atribuir isso exclusivamente ao MapLibre. Não aumentar tolerância silenciosamente nem declarar 5/5. `pequenos.json` e capturas por caso registram os resultados; para MapLibre MT prevalecem as linhas com final=true. Os registros MT com código repetido e situações conflitantes continuam sem arbitragem; promoteId por código pode destacar várias ocorrências. Não houve aceite de cadastro nacional único.

## Capturas e evidências

Capturas JPEG reais em `outputs/capturas/` desta entrega (fora do Git): `maplibre-am-visao-20261106.jpg`, `protomaps-am-visao-20261106.jpg`, `geojson-am-visao-20261106.jpg`; `maplibre-mt-20261106.jpg`, `protomaps-mt-20261106.jpg`, `geojson-mt-20261106.jpg`; pequenos 1–5 de cada UF/formato e três capturas de arrasto. As capturas full-page incluem a tabela da sessão, inclusive linhas extras de inspeção que não integram as medianas. `maplibre-mt-20261106-inicial.jpg` é da tentativa descartada. As capturas MT final mostram seleção explícita dos candidatos 3–5 e falhas 1–2. Nenhuma captura foi sintetizada.

## Recomendação

**Manter Leaflet e escolher protomaps-leaflet + PMTiles para o próximo piloto nacional**, condicionado à decisão do usuário e à correção/explicação dos pequenos MT. Nesta prova foi mais rápido para concluir os três cenários de abertura, exige menor biblioteca adicional e preserva a estrutura existente. MapLibre é funcional com Esri, código CAR, candidatos e destaque persistente; fica como alternativa se necessidades futuras justificarem WebGL/estilos, após teste em dispositivos reais. Nenhuma migração foi executada.

Antes de adotar os tiles: testar representação e seleção dos pequenos com geometria de referência, resolver duplicações e situações MT, validar Range/CORS no host dos dados e testar memória/latência em rede e aparelhos alvo. Dados nacionais devem ficar em armazenamento externo; a estimativa abaixo não é benchmark Brasil. Não há motivo medido para carregar GeoJSON estadual completo na visão nacional.

Passaram 79 testes Python e 39 testes JavaScript, sintaxe do executor, auditorias binárias AM/MT e hashes das sete bibliotecas/licenças. Os 17 arquivos novos da prova e APP/RL passaram LF e git diff --no-index --check; git diff --check e a conferência do índice também passaram. A execução APP/RL real foi reprovada pelo verificador e está documentada separadamente; isso não altera o resultado dos testes. Nenhum dado gerado, biblioteca ou captura entra no commit. Os dez arquivos da prova continuam preservados; lista e diff stat devem preceder qualquer commit, com confirmação conforme handoff. Sem push.

## MT: extração, integridade e limites da cópia nacional

Fonte: [coleção Source Cooperative CAR](https://source.coop/tristangruppwri/cadastral/brazil-car-area-imovel), referência dos dados 16/07/2026, STAC updated 02/08/2026, extração em 06/11/2026. A cópia declara licença `other`; foi usada somente para esta prova local e não foi adotada pelo site. Não houve publicação dos dados.

O footer Parquet confirma 8.453.552 linhas em 212 row groups, GeoParquet 1.1, WKB e EPSG:4326. Os grupos foram avaliados por estatísticas de `cod_estado`; quando não excluídos pelas estatísticas, a coluna UF foi lida. MT está em 13 grupos. Só `cod_imovel`, `ind_status`, `cod_estado` e `geometry` foram lidos para extrair as geometrias; só código, situação e geometria foram exportados. Blocos Range foram conferidos por status 206, tamanho e Content-Range e preservados em cache. O SHA-256 integral do Parquet nacional **não foi recalculado**; não apresentar essa verificação parcial como auditoria integral do arquivo nacional.

A extração contém **217.432 feições e 216.804 códigos distintos**. Há 628 ocorrências adicionais de código repetido: 46 comparações mantêm a mesma situação e 582 têm situação diferente; 397 têm WKB idêntico e 398 têm geometria topologicamente igual. As categorias se sobrepõem. Nenhuma das 217.432 geometrias retornou inválida no Shapely nesta extração. Isso não valida titularidade, limites cadastrais ou atualização da cópia.

A primeira tentativa, que bloqueava qualquer repetição, parou e foi preservada como `.partial`. Depois da auditoria, todas as linhas foram mantidas, inclusive repetições/conflitos, sem eleger situação ou geometria vencedora. `--auditoria-duplicados` vincula essa decisão ao SHA-256 do arquivo de entrada e confere contagens; o comportamento padrão continua bloqueando códigos repetidos. A prova não conta as linhas como imóveis únicos. Em MapLibre, `promoteId: code` pode destacar todos os registros do mesmo código, inclusive situações conflitantes; essa ambiguidade precisa ser mostrada na avaliação visual e resolvida antes de uma migração operacional.

| Artefato MT | Tamanho | SHA-256 |
|---|---:|---|
| GeoJSON da extração, somente código/situação/geometria | 298.023.753 B | `c6716c2e1caa2393be14ef57bedcaa51f060664213ec44c716238bb867a29895` |
| GeoJSON de exibição, simplificação de 0,00012 grau | 145.904.977 B | `27d05b089fd844fe84da773266224cc4cfb6fddaf74788e66a7e1c33de21c1bf` |
| PMTiles, mesmas opções e versão Tippecanoe da parte 1 | 172.318.612 B | `00a3525cec8485753902b21ee2d073ab014ce00ddb8d985f100c639e04af4024` |

O PMTiles ficou 18,1% maior que o GeoJSON de exibição no MT. Os cinco menores polígonos válidos do manifesto estão presentes com código/situação corretos no zoom 14 e ausentes no zoom 4. A auditoria é amostral: não percorreu todos os códigos em todos os tiles. Range real retornou 127 bytes e `Content-Range: bytes 0-126/172318612`. Evidências: `fontes/mt-extracao.json`, `manifesto-mt.json`, `verificacao-mt.json`, `range-mt.json` e `geracao-mt.log`, em `work/prova-maplibre/`.

Para reproduzir a aquisição em diretório sem extração anterior:

```powershell
.\.venv\Scripts\python.exe tools\prova_maplibre_estado.py --uf MT --extrair-sourcecoop
.\.venv\Scripts\python.exe tools\prova_maplibre_estado.py --uf MT --entrada work/prova-maplibre/entrada/mt-todas-linhas.geojson --origem 'Source Cooperative/SICAR; referencia 2026-07-16; STAC 2026-08-02; extracao 2026-11-06' --auditoria-duplicados work/prova-maplibre/fontes/mt-extracao.json
```

O extrator usa PyArrow 22.0.0 descompactado em `work/prova-maplibre/arrow-isolado`, sem instalar no sistema ou alterar requirements/.venv. A wheel foi obtida no PyPI e conferida pelo SHA-256 publicado; a origem fica em `origem.json`. Requests e Shapely são os do `.venv` existente. A extração inicial foi executada pelos scripts de trabalho preservados; a lógica foi incorporada ao preparador da prova para reprodução. Um teste exploratório com DuckDB 1.4.1 portátil não conseguiu carregar a extensão HTTP e não foi usado na extração; seus arquivos ficaram preservados em work, sem instalação no sistema.

Gerar o PMTiles com `tools/prova_maplibre_estado_gerar.sh` conforme `REPLICAR.md`, sem sobrescrever o existente, e executar:

```powershell
.\.venv\Scripts\python.exe tools\prova_maplibre_estado.py --uf MT --verificar
```

Na nova página da prova, o seletor “Formato” abre MapLibre, GeoJSON/Leaflet ou protomaps-leaflet em sessões separadas (`?renderer=maplibre`, `?renderer=geojson`, `?renderer=pmtiles`). As três opções reutilizam os mesmos arquivos AM/MT; os arquivos rastreados da parte 1 não foram alterados. Para MT, selecionar MT em “Estado extra” e abrir três vezes do zero em cada formato; pequenos usa agora o manifesto do estado aberto. As três opções foram exercitadas no navegador em 06/11/2026; resultados acima.

### Escala nacional de armazenamento — estimativa, não download medido

Por feição de entrada, as configurações medidas dão aproximadamente 821 B no AM e 793 B no MT. Aplicar linearmente a 7,2 milhões resulta em **5,71–5,91 GB decimais** de PMTiles; aplicar a 8.453.552 linhas dá aproximadamente **6,70–6,94 GB**. A repetição de códigos, distribuição espacial, complexidade e precisão das geometrias tornam essa faixa apenas um cenário de planejamento. Não extrapolar latência, RAM ou bytes de viewport a partir do tamanho em disco. O limite de 1 GB do Pages segue insuficiente para esse cenário; o host dos dados continua uma decisão separada.
