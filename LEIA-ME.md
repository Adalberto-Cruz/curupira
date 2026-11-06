# Hibama: executar localmente

Plataforma independente para consultar dados publicos do CAR e contexto ambiental no Amazonas. O site fica em `dist/`; o servidor Earth Engine e opcional e atende apenas em localhost.

No PowerShell, dentro de `site-hibama`, use Python 3.13:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Nao recrie o ambiente se o `.venv` ja estiver funcionando. Nao instale dependencias no conda base. As dependencias diretas e o NumPy estao fixados; dependencias transitivas ainda sao resolvidas pelo pip.

Preencha `GOOGLE_CLOUD_PROJECT` no `.env` da raiz, ou defina essa variavel no ambiente. O ambiente tem prioridade sobre `.env`; `--project`, quando informado diretamente ao servidor, tem prioridade sobre ambos. Um valor vazio no ambiente desabilita Earth Engine. O arquivo aceita comentarios e valores entre aspas; seu conteudo nao e executado nem interpolado.

```powershell
# Login oficial Google, apenas quando necessario.
.\tools\configurar-earth-engine.ps1
# Nas proximas execucoes, reutilize as credenciais.
.\tools\iniciar-hibama.ps1
```

Se o Windows bloquear um script por falta de assinatura, execute o lancador local revisado em um processo separado, sem alterar a politica permanente:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\configurar-earth-engine.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\iniciar-hibama.ps1
```

Abra `http://127.0.0.1:8766/mapa.html`. Os dois lancadores usam a porta 8766 por padrao e aceitam `-Port 8768` para escolher outra. Ambos usam explicitamente `.venv/Scripts/python.exe`, mesmo quando outro Python estiver no PATH. Com `-CheckConfig`, apenas validam a configuracao, sem perguntas, login ou servidor. Sem projeto, o configurador pede o ID, valida o formato e oferece gravar no `.env`, preservando outras configuracoes. Se voce nao gravar, o ID vale apenas nessa execucao. O lancador normal serve o site sem projeto e a API responde 503 com orientacao. Se o acesso Google falhar, o site local continua disponivel. Nao encerre outro servidor para liberar uma porta: escolha outra com `-Port` em qualquer lancador.

O `.env` fica fora de `dist/` e e ignorado pelo Git. Credenciais Google ficam sob controle do SDK; nao coloque chaves no HTML. Referencias: [autenticacao Earth Engine](https://developers.google.com/earth-engine/guides/auth) e [python-dotenv](https://bbc2.github.io/python-dotenv/).

## Dados e scripts

Os scripts ativos estao em `scripts/` deste repositorio. Os originais no diretorio pai foram preservados. Nesta etapa, os scripts continuam lendo e gravando dados em `../dados/amazonas/` e pesquisa em `../pesquisa/`; mantenha essa estrutura. `tools/preparar_dados.py` e `tools/preparar_ambiental.py` tambem usam os dados do pai. Execute preparadores somente quando quiser regenerar arquivos.

Os recortes `dist/data/ambiental/municipios/` e `intersecoes/` ficam fora do Git. Para restaurar o backup local validado:

```powershell
Expand-Archive -LiteralPath '..\..\backup\hibama-ambiental-20261105-225211-943650.zip' -DestinationPath 'dist\data'
```

O ZIP contem a pasta `ambiental/`. Em outro computador, obtenha os produtos prontos ou as bases de origem antes de executar os preparadores. O clone sozinho ainda nao inclui todos os dados ambientais.

Extracao dos PDFs, sem caminho de usuario fixo:

```powershell
.\.venv\Scripts\python.exe scripts\extrair_pdfs_pesquisa.py --entrada 'C:\pasta\dos\pdfs' --saida '..\pesquisa\2026-11-05\pdf'
```

Arquivos ausentes, vazios, protegidos ou corrompidos sao registrados em `erros.json`, e o comando retorna codigo 1 se houver falhas. Boto3 e ferramentas AWS ficam fora desta etapa.

## Verificar antes de commitar

```powershell
.\.venv\Scripts\python.exe tools\verificar_dados.py
.\.venv\Scripts\python.exe tools\verificar_ambiental.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check dist/assets/app.js
node --check dist/assets/ambiental.js
node --check dist/assets/map-visual.js
node --test tests/test_etapa2a.cjs
.\.venv\Scripts\python.exe tools\verificar_paleta.py
.\.venv\Scripts\python.exe -m compileall -q tools scripts tests
git diff --check
# Depois de selecionar os arquivos com git add:
.\.venv\Scripts\python.exe tools\verificar_commit.py
```

O verificador do indice bloqueia arquivos acima de 50 MB e caminhos locais proibidos; nao substitui a revisao de segredos. Nao ha push automatico. Pendencias atuais e futuras ficam em `docs/PENDENCIAS.md`.

As cores do mapa e os tracejados ficam em `dist/data/ambiental/paleta.json`, entrada independente lida pela interface, pelo preparador e pelo verificador. O catalogo gerado contem apenas a referencia `palette_file`; nunca e usado como entrada de cores. Se a paleta faltar ou estiver invalida, os comandos e a interface exibem erro claro. A adaptacao parte de [Okabe e Ito](https://jfly.uni-koeln.de/color/), com tons clareados para satelite escuro. O verificador usa [Machado, Oliveira e Fernandes (2009)](https://www.inf.ufrgs.br/~oliveira/pubs_files/CVD_Simulation/CVD_Simulation.html), em RGB linear, na severidade 1. Confere contraste de traco de pelo menos 3:1 no fundo de referencia `#203d31`, usando opacidade ambiental de 65% e CAR/selecao de 100%, e pode gerar amostras com `--saida PASTA`. A simulacao nao substitui avaliacao com usuarios, nem garante contraste em todo fundo ou com opacidade reduzida.

A legenda inicia recolhida no desktop e no celular. Ao entrar na largura de celular ou trocar municipio nesse tamanho, volta a recolher; pode ser aberta manualmente para consulta compacta. A reorganizacao dos filtros e do mapa no celular esta registrada para a Etapa 2b.

A Esri usa zoom nativo ate 16 e amplia acima dele. Falhas de carregamento mostram um tile local, aviso e nova tentativa. O limite reduz os tiles com texto de indisponibilidade; imagens desse tipo devolvidas com HTTP 200 nao sao detectadas automaticamente. A data de aquisicao e desconhecida.

Os panes ambientais e de destaque do CAR deixam os cliques atravessar suas superficies vazias. As camadas ambientais usam um renderizador SVG compartilhado por tipo; apenas os desenhos recebem eventos. Em TI, mineracao e embargo, somente o contorno recebe cliques. O destaque do CAR permanece sem interacao, permitindo selecionar outro imovel.

CAR e declaratorio: Ativo nao comprova regularidade. Intersecoes nao demonstram autoria ou infracao. Poligonos de exibicao sao simplificados, focos nao medem hectares queimados e mosaicos nao sao fotografias de uma unica data. A base e uma copia datada, sem atualizacao automatica.

## Etapa 2c-1: focos de calor Brasil

Abra `dist/focos.html` pelo servidor local ou use "Focos Brasil" no menu de qualquer pagina. Index, mapa, dados e focos usam o mesmo cabecalho e logo, gerados por `assets/site-header.js`. A visao nacional permanece separada das camadas do mapa CAR. A pagina carrega somente malha, indice e contagens dos anos do periodo escolhido. Nao inclui mapa de calor nem pontos (Etapa 2c-2, ainda nao autorizada).

```powershell
.\.venv\Scripts\python.exe scripts\coletar_focos_brasil.py --ate 2026-11-06
.\.venv\Scripts\python.exe tools\preparar_focos_brasil.py
.\.venv\Scripts\python.exe tools\verificar_focos_brasil.py
node --test tests/test_focos_model.cjs
node --test tests/test_site_header.cjs
```

Brutos e proveniencia ficam em `../dados/brasil/brutos/focos/`; normalizados e auditorias em `../dados/brasil/processados/focos/`. O coletor preserva arquivos existentes e confere SHA-256. O lote aprovado inclui anuais de referencia 2003-2025, mensais somente de 2026 e uma amostra de abril/2025. Nao ampliar automaticamente. Novembro/2026 e provisorio; o periodo inicial e novembro/2025 a outubro/2026, em UTC.

Produtos de navegacao em `dist/data/focos-brasil/` sao ignorados, exceto `manifesto.json`, que registra fontes, hashes, tamanhos, cobertura e auditorias. Um clone requer regeneracao ou copia desses produtos. Servir os `.gz` como arquivos binarios sem `Content-Encoding: gzip`: a interface descomprime explicitamente e valida SHA-256. Nao e necessaria biblioteca nova no navegador. Dependencias Python: requests, numpy, pyshp e shapely >=2.1 (GEOS >=3.12).

Atribuicao usa a geometria original IBGE 2025; somente a exibicao e simplificada. Em divisa, escolhe o codigo original se cobrir o ponto; caso contrario, o menor codigo. Sem municipio, coordenadas invalidas e areas operacionais ficam auditados e fora da soma municipal. As classes absolutas sao fixas: 0; 1-10; 11-50; 51-200; 201-1.000; 1.001-5.000; >5.000. Anuais sao produtos de referencia INPE; em 2026 filtra-se AQUA_M-T. Todos os satelites nao constituem serie comparavel. Focos nao representam incendios unicos ou area queimada.

Citar: INPE, Banco de Dados de Queimadas, Programa Queimadas; IBGE, Malha Municipal Digital 2025; acesso em 06/11/2026. O acesso INPE e livre e gratuito segundo sua FAQ; nao foi identificada licenca especifica de redistribuicao. Conferir os termos antes de distribuir os dados fora do ambiente local.

## Etapa 5a: busca local e filtros persistentes

O autocomplete do mapa consulta `dist/data/busca-municipios.json`, gerado dos produtos locais da malha IBGE 2025 da 2c-1. Contem nomes, UF, geocodigo e limites de enquadramento de 5.571 unidades municipais (inclui DF e Fernando de Noronha; exclui as duas areas operacionais). Nao consulta geocodificador nem servico externo durante a busca. Aceita acentos, caixa, trechos, UF e geocodigo; setas, Enter e Esc controlam a lista. A busca por CAR continua usando os arquivos cadastrais locais.

```powershell
.\.venv\Scripts\python.exe tools\preparar_busca.py
.\.venv\Scripts\python.exe tools\verificar_busca.py
node --test tests/test_etapa5a.cjs
```

O indice pequeno da busca e versionado. Para regenera-lo, restaure os produtos ignorados da 2c-1. A identificacao por clique usa a malha da base cadastral em memoria; fora dela, carrega a malha nacional local sob demanda e verifica seu hash. Nao desenha camadas de focos no mapa principal. Como a malha de exibicao e simplificada, limites proximos de divisas nao servem para determinacao cadastral ou medicao. Fora da cobertura configurada, informa as UFs com CAR disponivel e oferece abrir o municipio em Focos Brasil; essa pagina aceita `?municipio=CODIGO` para enquadrar o destino.

A URL do mapa guarda `municipio`, `car`, `camadas` (municipios, car, ti, anm, embargos, prodes, deter, focos), `inicio`, `fim`, `classe`, `opacidade` (10-100, padrao 65), `base` (satellite/terrain) e `colorir` (0/1, registros CAR). Uma selecao diferente do padrao grava todos os campos, inclusive os vazios; `camadas=` significa todas desligadas. Cada alteracao confirmada cria uma entrada no historico; mover o slider so confirma a URL ao finalizar a mudanca. Voltar/avancar aplica os controles sem criar outras entradas. Sem parametros, usa os padroes sem aviso. Links parciais recebem os valores padrao ausentes com aviso; valores invalidos, repetidos, datas impossiveis/invertidas, CAR incompativel e parametros desconhecidos sao tratados sem interromper a pagina. Um CAR com formato valido tambem e conferido no arquivo cadastral; se nao existir, a selecao e removida com aviso.

As oito classes DETER da paleta estao disponiveis antes de carregar qualquer recorte. Limpar filtros restaura municipio, CAR, camadas, datas, classe, opacidade, coloracao e mapa base, e remove a query da URL. Nao altera indicadores, organizacao visual do mapa ou a cobertura do CAR.

A cobertura do codigo novo da 5a vem exclusivamente de `car_ufs` em `dist/data/catalogo.json` (hoje `["AM"]`). Validacao de codigos, prioridade do autocomplete e avisos leem essa lista, sem UF fixa nos modulos novos. `tools/preparar_dados.py` deriva a lista das UFs da malha IBGE que possuem registros CAR locais. Os pontos legados ainda fixos em AM/Amazonas permanecem preservados e estao inventariados no relatorio da revisao. `.gitattributes` exige LF nos textos e preserva os formatos binarios.
