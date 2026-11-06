# Prova PMTiles — Etapa 4, parte 1

A prova reduziu os bytes necessários para visualizar CARs e o tempo de abertura no teste local. O arquivo PMTiles em disco ficou maior que os GeoJSONs. Clique e destaque básicos funcionaram, mas dependem da API de depuração do protomaps-leaflet. Minha recomendação é **avaliar MapLibre em outra prova autorizada antes de migrar o mapa interativo**. Não foi usado ou instalado MapLibre nesta etapa.

## Escopo preservado

Somente arquivos novos exclusivos da prova. Nenhum arquivo rastreado anterior foi alterado, incluindo mapa.html, app.js, paleta, menus, dados, .gitignore e documentação de etapas. Não há migração, commit ou push. O servidor atual da porta 8766 continua preservado.

## Ferramentas e dados

- Tippecanoe 2.79.0, commit `68ab8dcc229f95b8b25877697d5e8d66783af503`, licença BSD-2-Clause. Compilado no Ubuntu já existente, em `/tmp/hibama-prova-pmtiles-20261106/tippecanoe`, usando `make -j4 tippecanoe tippecanoe-decode`, sem `make install`, sudo, apt ou conda. Os pacotes zlib1g-dev e libsqlite3-dev foram instalados previamente pelo usuário. Nenhuma outra ferramenta foi instalada.
- Leaflet 1.9.4 já existente no site, licença BSD-2-Clause; protomaps-leaflet **5.1.0**, licença **BSD-3-Clause**, bundle fixo de 128.171 bytes, SHA-256 `26af014f7b1af308ec120b791cff76657bb9c3383633b52033e6edf9e5e4cdb5`. Bundle e licença ficam em work ignorado, carregados pelo servidor da prova. O script de download valida ambos os hashes e não usa latest.
- 62 GeoJSONs municipais atuais de `dist/data/mapa/`, 98.982 códigos únicos. Manaus (`1302603`) já está entre eles: seus 7.162 CARs não foram duplicados. Situações: AT 78.218; PE 9.322; SU 7.922; CA 3.520.
- Um único `work/prova-pmtiles/car-am.pmtiles`, camada `car`, zooms de dados 4–14; visualização permite overzoom até 20. No zoom 19 da captura, o desenho usa tiles de dados do zoom 14, não dados novos mais precisos.
- Geração: `-l car -Z4 -z14 --full-detail=14 --drop-densest-as-needed --no-tiny-polygon-reduction --simplify-only-low-zooms --simplification=2 --include=code --include=status`. Simplificação nos níveis baixos; nível máximo sem a simplificação de linhas, ainda sujeito à quantização dos tiles. A geometria de entrada já era simplificada pelo site; a prova não recupera precisão perdida anteriormente.
- Gerados em `work/prova-pmtiles/`, ignorado pela regra existente `work/`. Nenhum PMTiles, GeoJSON combinado, biblioteca baixada ou log entra no commit.

## Medidas

Medianas de três execuções por cenário no navegador integrado Chromium 156, Windows, viewport 1280 × 720. Servidor local em loopback, sem simulação de celular ou rede lenta; não são tempos de produção do GitHub Pages. Dados de CAR apenas, excluindo Esri, HTML, bibliotecas, paleta, manifesto da prova e cabeçalhos HTTP. Respostas dos dados sem compressão HTTP adicional e com Cache-Control: no-store. O PMTiles contém sua compressão interna. Caches do objeto da camada são reiniciados nas aberturas “do zero”; Esri e bibliotecas podem estar aquecidos.

| Medida | GeoJSON atual / comparador | PMTiles da prova |
|---|---:|---:|
| Disco, 62 arquivos do AM / um arquivo | 41.256.734 B | 81.307.541 B |
| Bytes para abrir todos os CARs do AM, zoom 6 | 41.254.233 B | 1.176.338 B |
| Requisições CAR na abertura AM | 1 (combinado) | 12 |
| Primeiro desenho AM | 1.045,7 ms | 77,9 ms |
| AM pronto após desenho/tiles | 1.153,9 ms | 170,7 ms |
| Bytes adicionais para zoom 12 em Manaus após AM | 0 B | 104.154 B |
| Tempo do zoom em Manaus após AM | 346,6 ms | 34,9 ms |
| Bytes para abrir Manaus diretamente, zoom 12 | 2.279.267 B | 95.961 B |
| Primeiro desenho de Manaus diretamente | 355,8 ms | 21,2 ms |
| Manaus pronto diretamente | 362,8 ms | 43,0 ms |
| Bytes adicionais no pan padronizado | 0 B | 6.378 B |
| Pan padronizado: tempo até conclusão | 1.031,5 ms | 1.020,2 ms |
| Pan padronizado: intervalo de quadros p95 | 6,2 ms | 6,2 ms |

O GeoJSON combinado contém exatamente os mesmos CARs; sua diferença de 2.501 bytes frente aos 62 arquivos decorre dos envelopes FeatureCollection. Esse comparador desenha **todos** os CARs do AM: o site atual não baixa esses 62 arquivos na abertura estadual, quando mostra limites municipais e carrega CAR por município. Portanto, a tabela não significa que a abertura atual do site transfira 41 MB. A comparação de Manaus diretamente usa o arquivo municipal atual sem alteração. No zoom após AM, o GeoJSON já está integralmente na memória e por isso não baixa mais dados.

Disco: PMTiles ficou aproximadamente 97% maior, resultado desta configuração de precisão, zooms, buffers e repetição das geometrias nos tiles; não é garantia de compressão do acervo. A economia de rede do AM foi aproximadamente 97,1% e a de Manaus diretamente 95,8%, **em relação ao comparador sem gzip HTTP**. Como referência calculada, não como medição de download, gzip nível 6 do combinado resultou em 11.622.918 B e de Manaus em 586.954 B. Uma CDN com gzip reduz a diferença de tráfego. Requisições Range acrescentam viagens de rede; latência externa pode alterar os tempos e não foi medida aqui.

Fluidez: o arrasto manual foi exercitado em ambos os formatos, sem travamento perceptível durante o gesto. O pan de 400 pixels foi configurado com animação de 1 segundo; a tabela usa a mediana dos tempos efetivamente observados. Não houve vantagem mensurável no p95 do pan aquecido. A maior pausa apareceu no carregamento GeoJSON, não durante o arrasto. Intervalos de requestAnimationFrame deste navegador automatizado são apenas uma observação local; não devem ser convertidos em FPS de hardware nem usados como promessa para celular. Não foi feita medição de memória ou validação em Android físico.

## Funcionalidade e limites

| Verificação | Resultado |
|---|---|
| Clique em CAR | O ponto interior calculado na geometria de entrada do menor perímetro válido de Manaus retornou `AM-1302603-D3F7431D65D14199BDE0CE9CE881A896`, exatamente o esperado. |
| Destaque | Contorno branco de 3 px, redesenhado nos tiles da camada após selecionar. Funcionou visualmente; a seleção foi repetida com sucesso após arrastar. |
| Cor por situação | AT, PE, SU e CA usam a paleta atual, com cores e tracejados distintos, nos dois comparadores. A captura estadual mostra as quatro situações. |
| Imóvel pequeno | Os cinco menores perímetros válidos de Manaus não constam no tile de dados do zoom 4 do respectivo ponto, mas os cinco estão presentes com código e situação corretos no zoom 14. O menor foi desenhado e selecionado no navegador em overzoom 19. |
| Privacidade | As 98.982 entradas sanitizadas têm somente code e status nas propriedades, além da geometria. O comando restringe os atributos e os metadados MVT só declaram esses dois campos; os tiles amostrados também foram conferidos. Não foram incluídos nomes, CPF ou CNPJ. |
| Range | Todas as requisições PMTiles das rodadas retornaram 206. O teste explícito de 127 bytes recebeu exatamente 127 bytes e Content-Range correto. |

A consulta `queryTileFeaturesDebug` considera o conteúdo dos tiles em cache. Não é uma API suportada de interação completa: o próprio código upstream a limita a depuração/casos básicos. O destaque requer symbolizer adicional e `rerenderTiles()`, em vez de estado nativo de feature. A prova não implementa hover, busca por CAR ausente do viewport, encaixe em geometria original, exportação de perímetro completo a partir de fragmentos, nem seleção cadastral precisa em divisas. Sobreposições podem devolver mais de um código, para escolha explícita. Não foi feita auditoria exaustiva da retenção dos 98.982 códigos em todos os tiles de maior zoom; os testes de pequenos são amostrais. Esses limites impedem tratar a prova como migração pronta.

## Servidor e hospedagem

O servidor atual `tools/servidor_earth_engine.py`, porta 8766, respondeu **200**, sem Content-Range, ao pedido `Range: bytes=0-126` do GeoJSON de Manaus. Ele não foi modificado. Foi criado exclusivamente para a prova `tools/prova_pmtiles_servidor.py`, porta **8774**, usando a biblioteca padrão do Python, com GET/HEAD, Range, 206, 416, Content-Length, Accept-Ranges, ETag e whitelist de arquivos. A verificação real do PMTiles retornou `Content-Range: bytes 0-126/81307541` e 127 bytes. O servidor exclusivo foi encerrado ao concluir o trabalho.

A documentação do Protomaps lista GitHub Pages como opção para arquivos que caibam nos limites de hospedagem. A prova não publicou nada nem validou Range no domínio público do projeto. O acervo nacional pode exceder limites de tamanho e armazenamento; esta configuração de AM não permite afirmar que um arquivo nacional caberá no Pages. Dados gerados continuariam fora do Git e precisariam de uma estratégia de publicação aprovada. Não foi adotado outro provedor.

## Recomendações

1. PMTiles é promissor para reduzir transferência seletiva e parsing inicial; não prometer redução de disco com esta configuração.
2. **Opção recomendada: avaliar MapLibre em uma próxima prova separadamente autorizada**, preservando o site atual. O motivo é a manutenção limitada e a API de seleção do protomaps-leaflet; nenhuma troca foi executada.
3. Antes de qualquer migração: auditar todos os códigos no nível máximo, seleção entre tiles/limites/sobreposições, hover, destaque persistente, busca fora do viewport, acesso à geometria original, rede lenta, celular e Range no host final. Medir uma configuração com menos níveis ou precisão menor para reduzir disco, sem aceitar o desaparecimento de imóveis pequenos.

## Reprodução

Na raiz do repositório, com o ambiente existente:

```powershell
.\.venv\Scripts\python.exe tools/prova_pmtiles_preparar.py
.\.venv\Scripts\python.exe tools/prova_pmtiles_bibliotecas.py
```

No Ubuntu, com o binário isolado já compilado:

```sh
export TIPPECANOE=/tmp/hibama-prova-pmtiles-20261106/tippecanoe/tippecanoe
export PROVA_DIR=/mnt/c/Users/user/Downloads/ibama/Hibama/site-hibama/work/prova-pmtiles
sh /mnt/c/Users/user/Downloads/ibama/Hibama/site-hibama/tools/prova_pmtiles_gerar.sh
```

Depois, no ambiente Windows do projeto:

```powershell
.\.venv\Scripts\python.exe tools/prova_pmtiles_verificar.py
.\.venv\Scripts\python.exe tools/prova_pmtiles_servidor.py --port 8774
```

Abrir `http://127.0.0.1:8774/prova-pmtiles.html`. Para cada formato: Abrir AM do zero → Zoom Manaus após AM → Pan padronizado → Abrir Manaus do zero. Repetir três vezes. Imóvel pequeno → clicar no centro marcado → conferir código/destaque. Salvar medições locais. Resultados brutos ficam em work/prova-pmtiles/medidas.jsonl e requisições em requisicoes.jsonl. Não expor o servidor local à Internet.

Validação executada: **27 testes Python (incluindo cinco da prova), 36 testes JavaScript, sintaxe JavaScript, auditoria real do PMTiles e dos cinco menores perímetros, Range real e checagem de isolamento/LF/arquivos ignorados**. O índice real permanece sem arquivos preparados para commit.

SHA-256 do arquivo medido: `823c0fbd968cd184f85627a04daced754a6e94ec854e189439a5ee2979f7cd69`.

## Fontes oficiais consultadas

- [Tippecanoe 2.79.0 e opções de geração](https://github.com/felt/tippecanoe/tree/2.79.0).
- [GDAL: driver PMTiles, alternativa nativa desde 3.8](https://gdal.org/en/stable/drivers/vector/pmtiles.html). Não foi instalado/usado nesta prova; a documentação Protomaps prefere Tippecanoe para overviews eficientes em bases maiores.
- [Criar PMTiles](https://docs.protomaps.com/pmtiles/create).
- [Leaflet e limitações da interatividade](https://docs.protomaps.com/pmtiles/leaflet).
- [Biblioteca, licença e modo de manutenção](https://github.com/protomaps/protomaps-leaflet).
- [Consulta básica, restrições e redesenho](https://github.com/protomaps/protomaps-leaflet/blob/main/src/frontends/leaflet.ts).
- [Armazenamento, Range e GitHub Pages](https://docs.protomaps.com/pmtiles/cloud-storage).
- [Especificação PMTiles v3](https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md).
