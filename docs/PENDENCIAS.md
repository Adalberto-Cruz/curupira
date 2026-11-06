# Pendências do Hibama

## Escopo e referências desta atualização

Registro de planejamento de 06/11/2026, sem implementar etapas nem autorizar publicação. A ordem abaixo substitui a ordem anterior da PROPOSTA_HIBAMA_CODEX.md e deste arquivo.

Fontes: ATUALIZACAO_PLANO_2026-11-06.md; PROPOSTA_VERIFICACAO_CAMPO_E_RELATORIOS.md, Parte D atualizada (especialmente D.1, item 8); PADRAO_VISUAL_PDF_HIBAMA.md. A seção 8 atualizada de PESQUISA_MODELO_IA_HIBAMA.md foi relida como referência para a futura etapa de APP/IA; os nove cuidados abaixo são os da atualização do plano. A revisão de fontes acrescenta AUDITORIA_FONTES_HIBAMA.md (06/11/2026), incluindo a segunda rodada com a seção 2.7, nos pontos solicitados de carbono, turbidez, licenças, vazamento e fontes ainda não verificadas.

Regras mantidas: uma etapa por vez, com testes, relatório e aprovação; mostrar a lista antes de commitar; nenhum push sem autorização. A 5a foi concluída e commitada em 5fa2a11. A Etapa 4 parte 1 foi commitada em 038b378. O handoff de 06/11/2026 autoriza a parte 2, prova isolada MapLibre, e esta atualização documental. A escolha do motor e a migração continuam dependendo de decisão posterior. A prova MapLibre ainda precisa de medições reais; ver docs/PROVA_MAPLIBRE_ETAPA4_2.md.

## Nova ordem aprovada

1. **5a — Busca e filtros na URL.** Concluída; permanece no plano como ponto de partida.
2. **4 — Dados escaláveis.** Prova pequena de PMTiles primeiro; só depois, a migração.
3. **2b — Interação e visualização.** Agrupamento, detalhe por zoom, modo foco, layout no celular, cor própria por classe DETER e painel lendo paleta.json.
4. **6 — Dossiê do imóvel.** Cruzamentos por CAR, camadas novas abaixo e relatórios em PDF.
5. **9 — v1.0 pública.** Somente o que já é dominado: CAR, TI, UC, assentamentos, quilombolas, florestas públicas não destinadas (CNFP), PRODES, DETER, focos e embargos. Sem Earth Engine ao vivo.
6. **3 — Earth Engine na interface.** Com o backend de demonstração descrito na hospedagem.
7. **2c-2 — Focos no mapa principal.** Mancha de calor e pontos.
8. **5b — Indicadores percentuais.**
9. **APP e Reserva Legal — Motor de regras.** Referência: PESQUISA_MODELO_IA_HIBAMA.md, incluindo a revisão externa atualizada.
10. **IA — Classificador em lote e índice de atenção.**
11. **Potencial de carbono (estimativa).**
12. **7 — Expansão operacional.** O escopo aprovado já é o Brasil todo. A execução pode ser feita por UF, com validação progressiva, sem reduzir a meta nacional a um piloto no AM/PA.

A 2c-2 continua dependendo de liberação específica. A 2c-1 já fornece o coroplético nacional e a série de referência, sem mapa de calor ou pontos no mapa principal.

## Escopo nacional — decisão do handoff de 06/11/2026

- **Meta: Brasil inteiro.** O site e os pipelines de CAR/camadas ainda têm cobertura operacional AM; esta documentação não altera a cobertura implementada. Focos de referência já são nacionais.
- O planejamento inicial usa **~7,2 milhões de imóveis CAR** como ordem de grandeza, não uma contagem nacional atual validada. A cópia Source Cooperative declara 8.453.552 linhas e 8.437.938 códigos distintos, com referência em 16/07/2026; reconciliar datas, duplicações e recortes antes de contar imóveis.
- PMTiles nacional deve ser planejado em **vários GB**, acima do limite de **1 GB do site publicado no GitHub Pages**. Extrapolação apenas ilustrativa da parte 1: 81.307.541 B / 98.982 códigos × 7.200.000 ≈ 5,91 GB decimais. Não é medição nacional nem substitui MT/PA: complexidade das geometrias, precisão, buffers e níveis alteram o tamanho.
- A prova MapLibre reutiliza o PMTiles do AM e deve medir também MT ou PA antes da decisão Leaflet × MapLibre. A preparação da prova não autoriza migrar os dados ou modificar o site atual.

### Fontes nacionais e verificações antes da migração

Atualização de 06/11/2026 baseada no relatório `FONTES_ETAPA6_E_CAR_NACIONAL.md`, em `outputs/` do chat de verificação. O resumo abaixo registra os achados e as pendências; não implementa filtros, coleta ou integração.

| Fonte | Cobertura / estado | Licença / limites | Ação pendente |
|---|---|---|---|
| CAR / SICAR (SFB) | Meta nacional; base implementada AM | Não foi identificada licença/termos publicados para AREA_IMOVEL; dado acessível publicamente não equivale a licença aberta. O espelho declara `other`. | Registrar atribuição SFB; esclarecer termos antes de redistribuir; publicar só campos permitidos, sem dados pessoais. |
| Cópia CAR — Source Cooperative | **8.453.552 registros/perímetros (~8,45 milhões)**, com contagens por UF verificadas; referência 16/07/2026, arquivo alterado em 02/08/2026 | Cópia do SICAR, sem atualização automática e sem licença específica SICAR identificada; declara `other`. Registros não equivalem a imóveis únicos. Não contém `cod_municipio_ibge` como coluna própria. | Na futura visualização e contagem, filtrar cancelados (`ind_status=CA`), preservando o bruto e a auditoria. Resolver códigos duplicados/situações conflitantes antes de contar imóveis; definir associação à malha/código IBGE sem tratar município textual como geocódigo. A cópia não foi adotada como base do site. |
| DETER / INPE | Amazônia Legal e Cerrado; não cobre todo o Brasil | Preservar atribuição/licença da fonte. Fora da cobertura, ausência de alerta não significa ausência de alteração. | Avisar essa cobertura no site e nos dossiês na implementação nacional. |
| Embargos / Ibama | Base nacional confirmada em CSV/XML/JSON, com polígonos WKT em `GEOM_AREA_EMBARGADA`; arquivos consultados atualizados em 06/11/2026. Hoje o site usa cópia IPAAM restrita ao AM. | CKAN declara Outra (Aberta). Há registros sem geometria e campos pessoais no bruto; filtrar os atributos antes de publicar. | Substituir a cópia IPAAM pela base nacional oficial; considerar `SIT_CANCELADO`, `DES_STATUS_FORMULARIO`, `SIT_DESEMBARGO` e histórico ligado por `SEQ_TAD`. Não inferir vigência de um único campo. A cópia local IPAAM não contém esses indicadores de situação. |

Verificação do espelho: GeoParquet 1.1, EPSG:4326, 3.258.574.258 B; esquema/footer e contagens de registros por UF conferidos, além de amostra tabular de 25 registros de RR, sem novas geometrias. O esquema observado contém `cod_imovel`, `ind_status`, `cod_estado`, `municipio`, `des_condic`, `ind_tipo`, `mod_fiscal`, `num_area`, `dat_criaca`, `dat_atuali`, `cod_tema`, `nom_tema`, `bbox` e `geometry`. Não confundir condição administrativa (`des_condic`) com situação (`ind_status`). Contém só perímetros AREA_IMOVEL; APP/RL não estão incluídas. Há duas geometrias suspeitas em arquivo separado, em outro CRS. Permanecem pendentes o checksum integral nacional e os códigos únicos por UF; os 8.437.938 códigos distintos são declaração do catálogo, não recálculo nacional desta verificação. Não foram identificadas colunas estruturadas de nome de titular/CPF/CNPJ no esquema, sem garantia sobre todos os valores de texto. O `updated` do STAC é 02/08/2026, distinto da referência dos dados e da data mostrada na página do produto; preservar as três datas no inventário da futura coleta.

Fontes consultadas: [coleção CAR](https://source.coop/tristangruppwri/cadastral/brazil-car-area-imovel), [STAC da coleção](https://data.source.coop/tristangruppwri/cadastral/brazil-car-area-imovel/collection.json), [limites Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [cobertura DETER no catálogo INPE](https://data.inpe.br/), [embargos nacionais Ibama](https://dadosabertos.ibama.gov.br/dataset/fiscalizacao-termo-de-embargo).

## Hospedagem planejada

Os limites e valores abaixo são os registrados no plano; conferir as condições vigentes quando for implementar.

| Parte | Destino | Condições e pendências |
|---|---|---|
| Site oficial estático | GitHub Pages | Endereço permanente; plano registra limite de 1 GB publicado e cerca de 100 GB/mês de banda, com limite flexível. |
| Processamento e treino da IA | AWS Learner Lab, em lote | Abrir a sessão, processar, exportar os arquivos e fechar. Sem servidor de IA permanentemente ligado. |
| Demonstração de Earth Engine ao vivo | AWS Learner Lab: S3 para o site e Lambda para a API do Earth Engine | Somente demonstração/apresentação: orçamento de US$ 100, conta vinculada ao curso e risco de desativação. Não é a hospedagem oficial permanente. |
| Dados pesados nacionais, incluindo PMTiles | S3 do Learner Lab para a apresentação | Depois avaliar Cloudflare R2 ou Azure com crédito do Student Pack. Não ativar R2/Azure agora. Manter os dados pesados fora do Git e do Pages. |

- R2: conferir armazenamento, operações e custos antes de ativar; a franquia Standard publicada é 10 GB-mês, não armazenamento ilimitado. Azure: o Student Pack anuncia crédito de US$ 100, sujeito à elegibilidade e aos termos. Nenhum serviço foi ativado. Referências: [R2](https://developers.cloudflare.com/r2/pricing/) e [Student Pack](https://education.github.com/pack).
- Antes de usar o Learner Lab para demonstrar o site, testar se o site estático no S3 continua acessível depois de End Lab. Isso foi relatado por usuários, mas não está documentado oficialmente no material do plano; não presumir que funcione.
- A IA roda em lote e gera JSON/PMTiles estáticos, que o site apenas lê. Não há servidor de IA ligado continuamente.
- Validar a distribuição dos produtos ambientais e dos demais arquivos pesados fora do Git na Etapa 4. Os recortes e interseções atuais estão ignorados e preservados em backup externo validado.

## Etapa 2b: pendências preservadas

- Corrigir o texto do status de focos: mostrar uma única data de atualização e formatar meses como **nov/2025**, em vez de **2025-11**. Preservar o período selecionado em seu controle próprio; esta atualização não altera a interface.

- No celular, o mapa fica espremido no meio da página, depois de todos os filtros. Rever os controles e o espaço do mapa nesta etapa, junto de agrupamento, detalhe por zoom e modo foco.
- Conferir cor própria por classe DETER e o painel lendo a paleta centralizada em dist/data/ambiental/paleta.json.
- Mapa de calor e pontos dos focos nacionais ficam na 2c-2, na nova posição da ordem. A camada antiga do mapa CAR do AM continua datada de 29/10 a 04/11/2026, com todos os satélites; não comparar suas contagens com a série nacional de referência.

## Etapa 6: camadas novas e cruzamentos por CAR

- **Unidades de Conservação:** CNUC/MMA, edição **2026_07**, distinguindo esfera administrativa e Proteção Integral/Uso Sustentável. CSV e dicionário confirmados; licença CC Atribuição no catálogo, sem versão numérica confirmada. O link do shapefile retornou página OneDrive, sem ZIP: tamanho, CRS, checksum e esquema binário atual permanecem pendentes. Conferir `limite` (UC ou zona de amortecimento) e `quali_pol`, sem contar ZA como área da UC. Fonte: [catálogo CNUC](https://dados.mma.gov.br/dataset/unidadesdeconservacao).
- **Assentamentos rurais e territórios quilombolas:** INCRA/Acervo Fundiário, **pendentes por login gov.br**; também houve falha DNS na consulta. Confirmar downloads atuais, datas, licença específica, tamanho, CRS e campos após acesso autorizado. Os esquemas encontrados nas republicações do Ibama não substituem os arquivos atuais do Acervo; não usar suas datas de sincronização como data da fonte. Fonte: [Acervo Fundiário](https://acervofundiario.incra.gov.br/acervo/login.php).
- **Florestas públicas:** CNFP/SFB **confirmado**, ano-base **2025**, publicação declarada **junho/2026**. ZIP de **229.469.123 B**, Shapefile PolygonZ em SIRGAS 2000 (EPSG:4674), cabeçalho DBF com **12.874 registros**; campos, CSV e dicionário conferidos, sem auditoria espacial integral. Catálogo declara CC Atribuição, sem versão explícita; campo de licença no PDF está em branco. Não presumir `codigo` como chave estável/preenchida. Manter destaque para floresta pública não destinada (Tipo B), como alerta cruzado com o CAR na v1.0; interseção não comprova, isoladamente, infração ou titularidade. Fonte: [catálogo CNFP](https://dados.florestal.gov.br/dataset/cadastro-nacional-de-florestas-publicas-cnfp).
- Antes de baixar qualquer base nova, conferir fonte oficial, licença, data e formato. Interseção é evidência para análise, não comprovação de infração.
- Validar os cruzamentos por CAR e a qualidade espacial antes de incluí-los no dossiê. Os verificadores atuais não substituem essa validação.

## Etapa 6: relatórios em PDF antes da v1.0 pública

Escopo da Parte D.1, item 8, da proposta de verificação:

- Entram na v1.0 o **PDF do dossiê do imóvel** e o **PDF do panorama do município**.
- O dossiê inclui a seção **Próximo passo recomendado e canais oficiais**, com a fase recomendada e o órgão competente. Conferir os canais oficiais na implementação; o site documenta a orientação e não envia encaminhamentos ou denúncias sozinho.
- A ficha de missão completa fica na v1.1, junto com a IA. Receber resultados de campo fica na v2.0.

Seguir PADRAO_VISUAL_PDF_HIBAMA.md, usando a estrutura e o acabamento da referência real referencias/referencia_pdf_riskai_sompo.pdf. Não inventar outro estilo; adaptar identidade e conteúdo do projeto.

- A4, fundo branco, margens próximas de 15 mm; panorama em paisagem e dossiê do imóvel em retrato.
- Cabeçalho com logo à esquerda, título em destaque, filtros/período e metadados de origem: data da base e data/hora de geração. Filete fino na cor principal da marca.
- DM Sans e hierarquia clara entre título, números dos cards e tabela. Seis cards no formato da referência, com um card de destaque na cor da marca e texto branco.
- Tabela com cabeçalho grafite escuro (#333438), texto branco, linhas zebradas claras, números à direita e formatos brasileiros. Repetir o cabeçalho e indicar continuação nas páginas seguintes.
- Destaques de índice alto (referência visual: índice >= 75) e travas críticas somente na cor do texto, sem pintar a linha inteira. Blocos de índice de atenção, nota de 0 a 100, trava e contribuição dos blocos devem trazer fonte/data quando o índice estiver disponível; não antecipar cálculos da IA ou da 5b nem inventar métricas para preencher a v1.0.
- Cores de marca: verde escuro #153e35 e laranja #d98646; cores das camadas em dist/data/ambiental/paleta.json. Definir uma única cor de alerta legível em impressão nessa paleta. Se nome/logo mudarem antes da v1.0, atualizar os pontos centralizados.
- Mapa do imóvel com polígono CAR e camadas que cruzam. Esperar os tiles carregarem ou preparar imagem estática/SVG antes de window.print(), evitando mapa cinza no PDF.
- Página HTML dedicada para o relatório, CSS de impressão e @page com orientação/margens adequadas, seguida de window.print() para Salvar como PDF. Usar print-color-adjust: exact e break-inside: avoid em cards, gráficos, blocos e linhas; repetir thead. Não requer backend.
- Rodapé com projeto, dados públicos, data/hora e Página X de Y. Usar os contadores de impressão quando suportados; caso contrário, mostrar data/hora. Identificar a base e seu SHA-256 no rodapé da última página.
- Fontes e limitações sempre presentes: CAR declaratório; interseção não prova infração; foco não é área queimada; geometria simplificada. Incluir o aviso: Evidências para análise. Não constitui laudo, autuação ou prova de infração.
- Não exibir nome de titular/pessoa, CPF ou CNPJ. Identificar o imóvel somente pelo código do CAR, com link para a consulta oficial do SICAR.
- Exportar dados passa a oferecer Relatório em PDF como padrão, Dados brutos (JSON) e, opcionalmente, Planilha (CSV).
- Aceite: comparar o PDF lado a lado com a referência real; testar Chrome desktop e Android (Imprimir > Salvar como PDF), sem cards/tabelas cortados. Enviar capturas das páginas para revisão antes do commit dessa implementação.

## Etapa 9: obrigatório antes do primeiro push público

1. **Nome definitivo do projeto: ANGELIM**, por decisão de Adalberto. Executar a renomeação **Hibama → ANGELIM na Etapa 9, antes do primeiro push público**; esta atualização apenas registra a decisão, sem renomear o site agora.
   - **Observação informada por Adalberto:** há registro da marca "ANGELIM" em vigor no INPI, classe 42, de titular terceiro, de 2021. Este registro documental não representa uma nova consulta ao INPI.
   - **Escopo de uso do projeto:** apenas acadêmico e open source, sem registro de marca próprio e sem uso comercial.
   - **Texto do site na Etapa 9:** identificar expressamente ANGELIM como **projeto acadêmico**, incluindo essa informação na apresentação do projeto.
2. **Histórico público limpo:** preparar uma branch nova somente com o estado atual, sem os cerca de 121 MB de dados antigos no histórico. Preservar o histórico atual localmente. A execução dessa preparação depende da liberação da Etapa 9.
3. **Privacidade:** nunca exibir nome de pessoa/titular, CPF ou CNPJ; identificar imóveis somente pelo código do CAR, com link para a consulta oficial do SICAR.
4. **Documentação e licenças:** LICENSE, README e tabela de fontes com a licença de cada dado. Conforme a auditoria:
   - Dado derivado de PRODES/DETER que for redistribuído deve ficar sob **CC BY-SA 4.0**. Considerar a obrigação ShareAlike na decisão sobre a licença do projeto e manter a atribuição das fontes no site e nos PDFs.
   - Não redistribuir textos ou dados do **Imazon sob NC-ND**. Eventual uso de polígonos Simex depende de cessão e da verificação dos termos; não presumir permissão a partir da existência do produto.
   - Os **dados do MapBiomas são CC BY 4.0**, com redistribuição de derivados mediante atribuição. Nos materiais do MapBiomas, CC BY-SA é a licença dos textos/notícias, não dos dados.
   - O **JRC TMF exige a atribuição "Source: EC JRC"**, além de citar Vancutsem et al. 2021, conforme a auditoria.
   - **Planet NICFI fica fora do site público**, por seu acesso restrito e uso não comercial.

A v1.0 pública mantém apenas o escopo de camadas listado na nova ordem e não inclui Earth Engine ao vivo. Nenhuma preparação de histórico, remoção de dados, publicação ou push foi executado nesta atualização.

## Etapa da IA: nove cuidados obrigatórios

O exemplo externo com Earth Engine reduceRegions, LightGBM, SHAP e calibração é referência, não código a copiar sem revisão.

1. Não avaliar no próprio treino. Usar previsões fora da dobra, splits espaciais e precisão, recall e F1 por classe.
2. Não passar groups para CalibratedClassifierCV.fit. Preparar os splits e fornecê-los em cv: cv=list(GroupKFold(n).split(X, y, grupos)).
3. Não aplicar fillna(0) aos índices: NDVI zero representa solo exposto. Manter NaN, tratado pelo LightGBM.
4. As janelas de antes/depois devem ser relativas à data de cada alerta, sem janelas fixas para todos os registros.
5. Filtro de nuvem de 30% não substitui máscara SCL. Reaproveitar a máscara do servidor_earth_engine.py.
6. Proibir uso da fonte do rótulo como feature, como a classificação do MapBiomas usada para rotular o alvo.
7. Detectar classe rara sem positivo em uma dobra e marcar dados insuficientes.
8. Se make_valid produzir GeometryCollection com linhas, manter somente as partes poligonais antes de calcular área e perímetro.
9. Separar queimada de degradação e listar todas as classes acima do limiar, em vez de retornar somente a classe máxima.

### Regras contra vazamento — auditoria de fontes, seção 3

Além dos nove cuidados acima, aplicar as cinco regras da auditoria:

1. Uma fonte não pode ser rótulo e feature da mesma classe.
2. Produto derivado conta como a fonte original. MapBiomas Alerta deriva do DETER e DETER-R pertence à família INPE. Se o rótulo da classe vier do INPE, nenhum desses dois produtos entra como feature ou validação dessa classe.
3. A validação precisa ser independente do rótulo: outro sensor/produtor, como RADD, amostra fotointerpretada manualmente ou anos separados, conforme o desenho de validação adotado.
4. Processos ANM, autos de infração e embargos nunca são rótulos de ML: indicam solicitação ou atuação da fiscalização, não comprovam a atividade observada, e introduzem viés de seleção.
5. Manter queimada e degradação como classes separadas.

### Papel das fontes por classe — auditoria, seção 3.1

L = rótulo de treino; F = feature; V = validação. Os papéis abaixo são os registrados na auditoria; conferir as regras legais e fontes aplicáveis na implementação. A BHO referida na tabela é a BHO 6 da ANA.

| Classe | Como decide | Rótulo (L) | Features (F) permitidas | Validação (V) |
|---|---|---|---|---|
| APP | regra | — | — | CAR + BHO/Massas d'Água ANA (rios, largura do art. 4º) + ANADEM (encosta e topo de morro) |
| Reserva Legal | regra | — | — | CAR + uso da terra (80/35/20%) |
| Terra Indígena | regra (trava) | — | — | FUNAI |
| Embargo | regra (trava) | — | — | Ibama (histórico) |
| Floresta pública não destinada | regra (alerta) | — | — | CNFP Tipo B |
| Desmatamento | modelo | PRODES | Sentinel-2, Sentinel-1, focos INPE | RADD + Hansen GFC + amostra manual |
| Queimada | modelo | MapBiomas Fogo C5 | dNBR Sentinel-2, focos INPE | anos separados + amostra manual |
| Exploração madeireira | modelo | Simex (se cedido); senão JRC TMF degradação | textura S-2, S-1 | a fonte que não virou rótulo + amostra manual; Sinaflor/AUTEX separa autorizada de não autorizada |
| Garimpo | modelo | MapBiomas Mineração | solo exposto e turbidez S-2, ANM como contexto | Amazon Mining Watch + amostra manual |
| Pastagem | modelo | TerraClass 2022/2024 | fenologia S-2 | MapBiomas Cobertura (só V, nunca F) |

TerraClass e MapBiomas usam imagens semelhantes: a validação de pastagem é apenas parcialmente independente. Reportar essa limitação na ficha do modelo.

### Fontes adicionadas — auditoria, seção 2.7

Tabela da auditoria, com a referência temporal do CNFP corrigida pela verificação posterior de fontes de 06/11/2026. CNFP entra na Etapa 6/v1.0; BHO 6, Massas d'Água e ANADEM acompanham o motor de APP. As demais referências permanecem nas etapas posteriores correspondentes. Este registro não autoriza coleta nem implementação.

| Fonte | Resolução / período | Acesso | Licença | Para que serve |
|---|---|---|---|---|
| ANA — **BHO 6** (v6.2.4, out/2022) + Massas d'Água | vetor; na Amazônia, escala 1:250.000 (a BHO 2017 ainda tinha trechos 1:1.000.000) | SNIRH / metadados.snirh.gov.br (gpkg) | acesso livre | **Obrigatória para APP.** O Argon deixou para depois, mas sem hidrografia o motor de APP não roda. A BHO não tem largura do rio: a largura sai do polígono de Massas d'Água ou da MapBiomas Água. |
| ANADEM v1 (ANA + IPH/UFRGS) | 30 m, terreno sem viés da vegetação | EE `projects/et-brasil/assets/anadem/v1` | acesso livre | **APP de encosta (> 45°) e topo de morro** (art. 4º, V e IX). Nenhuma das duas auditorias tinha relevo. |
| Hansen Global Forest Change v1.13 (UMD) | 30 m, 2000–2025 | EE `UMD/hansen/global_forest_change_2025_v1_13` | CC BY 4.0 | **Validação independente de desmatamento** (não é INPE), junto com o RADD. |
| JRC Tropical Moist Forest v1.2025 (Comissão Europeia) | 30 m, 1990–2025, separa **degradação** de desmatamento | EE e download no site do JRC | livre, sem restrição de uso; atribuição "Source: EC JRC" + citar Vancutsem et al. 2021 | **Exploração madeireira / degradação.** Cobre o buraco se o Simex não for cedido. Últimos ~3 anos têm incerteza entre degradação e desmatamento (o próprio JRC avisa). |
| Amazon Mining Watch (Earth Genome + Pulitzer) | Sentinel-2; anual 2018–2025 e trimestral até Q3/2026; atualizado 16/10/2026 | source.coop/earthgenome/amazon-mining-watch | Creative Commons 4.0 | **Validação independente de garimpo** (modelo próprio, não MapBiomas). Trimestres recentes são provisórios. |
| MapBiomas 10 m, Coleção 2 (beta) | Sentinel-2, 10 m, 2016–2023 | plataforma MapBiomas | CC BY | Uso da terra mais fino para imóvel pequeno. É beta: o próprio MapBiomas pede cautela ao comparar anos. Só feature/contexto, nunca rótulo. |
| CNFP — Florestas Públicas (SFB) | vetor; ano-base 2025, publicação junho/2026 conforme verificação posterior do recurso | dados.florestal.gov.br | Creative Commons Atribuição (marcada no portal; versão específica não confirmada) | **Floresta pública não destinada (Tipo B):** CAR em cima dela é o principal sinal de grilagem. Vira trava/alerta no motor de regras. |

## v1.1: ficha de missão de drone e ferramenta de hash

- **Ficha de missão completa:** v1.1, junto com a IA, conforme Parte D.1, item 8. Consultar a matriz de decisão, sensores, alcance e cadeia de custódia adotados nos itens 1 a 5 quando essa implementação for liberada.
- Modelo híbrido: quanto à missão de drone, exibir publicamente somente a etiqueta de verificação de alta resolução recomendada. A ficha completa de drone é gerada sob demanda no navegador, após instituição, registro SARPAS e termo de responsabilidade, sem salvar no servidor. Essa barreira não autentica o usuário nem constitui controle de acesso.
- Na ficha, não sobrevoar sedes/residências; focar o polígono de alteração. Preservar a trava de nenhuma recomendação de drone em TI. Conferir cada citação legal em fonte oficial no momento da implementação e aplicar as correções da Parte D.2, sem reutilizar normas não confirmadas ou autorizações que não se aplicam ao voo.
- **Ferramenta de hash no navegador:** arrastar fotos, calcular SHA-256 com crypto.subtle.digest, ler GPS do EXIF e gerar certificado PDF/TXT. Tudo local/offline, sem enviar arquivos, conforme Parte D.1, item 6. Incluída na v1.1 por orientação do usuário.
- Orientar a preservação de originais RAW/JPEG com EXIF completo, logs de voo e manifesto SHA-256 antes de abrir os originais em software, conforme os cuidados de custódia da Parte D.1.

## v2.0: resultados de campo

- Receber resultados de campo somente na v2.0, conforme o corte de escopo da Parte D.1, item 8. Não implementar recebimento de ortomosaico/laudo ou fechamento de verificação na v1.0.

## Etapa 5b: indicadores — pendências preservadas

- Incluir opção focos por 1.000 km² no coroplético nacional: contagens absolutas favorecem municípios grandes. Definir denominador e comparabilidade antes de implementar.
- Verificar se o TerraBrasilis publica floresta remanescente do PRODES antes de propor o denominador de floresta preservada.

## Potencial de carbono (estimativa) — após a IA

Fontes e regras definidas na auditoria, seção 2.5:

- **Fonte principal: ESA CCI Biomass v7.0**, CEDA, 100 m, série anual de 2005–2012 e 2015–2024. Preparar/importar o recorte necessário para processamento. A disponibilidade da v7 no Earth Engine, oficial ou comunitário, permanece entre as verificações de acesso abaixo; a escolha da fonte principal já está definida.
- **Protótipo: ESA CCI Biomass v6.0 no Earth Engine**, asset ESA/CCI/Above_Ground_Biomass/V6_0, 100 m, anos 2007, 2010 e 2015–2022, com bandas agb e agb_sd. Usar enquanto a v7 não estiver importada.
- AGB representa biomassa acima do solo em massa seca, em Mg/ha; conforme a definição registrada na auditoria, não inclui raiz, toco ou folha. Documentar as contas, unidades e fontes: **carbono = AGB × 0,47**, fração padrão do IPCC; **CO2e = carbono × 44/12**. Validar o tratamento das áreas ao obter estoque por imóvel.
- Exibir sempre a **faixa de incerteza** a partir do desvio padrão por pixel, usando agb_sd no protótipo v6. Definir a propagação da incerteza no cálculo agregado; não mostrar falsa precisão. Radar pode subestimar biomassa em floresta muito densa por perda de sensibilidade.
- **GEDI, com resolução de 1 km, somente como contexto regional**, não como estimativa por imóvel. Não tratá-lo como validação independente da ESA CCI: desde a v6, a calibração da ESA CCI usa lidar GEDI.
- **Imóvel com menos de aproximadamente 10 ha, ou menos de 10 pixels de 100 m: mostrar somente a faixa, sem número pontual.** Para os demais imóveis, manter a estimativa acompanhada da faixa e das limitações.
- Publicar somente os valores calculados por imóvel/município, com citação obrigatória de ESA CCI, projeto Biomass CCI e DOI do dataset usado. Os termos não asseguram qualidade nem dão direito explícito de redistribuir o raster; **não hospedar cópia do raster no site**.
- A série anual permite estudar perda de carbono comparando o ano anterior e o seguinte ao desmatamento PRODES, com método e período explicitados antes de calcular.
- Apresentar por imóvel, junto da situação cadastral, percentual de floresta e estoque estimado em tCO2e, com método, período, incertezas e validação documentados. Usar estimativa de biomassa/carbono e avisar que não é laudo nem crédito de carbono.
- Estudar faixa ilustrativa de US$ 5-15/tCO2e, com a referência CPI/PUC-Rio 2025 indicada pelo usuário; conferir a publicação e o contexto antes de usar os valores.
- Incluir alertas de inaptidão: CAR não ativo, sobreposição com TI ou embargo, desmatamento recente e ausência de titularidade comprovada. Definir critérios antes de implementar; CAR e interseções não comprovam titularidade ou infração.
- Nunca chamar o resultado de crédito de carbono ou valor do imóvel. Usar Potencial de carbono (estimativa); TFFF apenas como contexto nacional.

## Backlog: qualidade da água

- Reavaliar o produto INPE aguas-continentais-rrs quando houver cobertura da Amazônia. A informação anterior era de cobertura somente do Tietê (SP); confirmar a cobertura oficial ao retomar. Não integrar agora.
- Para o produto futuro, adotar o nome **indicador de turbidez por satélite** (proxy de turbidez/sedimento), conforme a seção 4 da auditoria; nunca apresentá-lo como qualidade da água ou IQA.
- Comparar cada trecho com a **linha de base do próprio rio**, mostrando a anomalia, não um valor absoluto comparado entre rios. Rios de água branca, como Solimões e Madeira, já têm turbidez natural elevada.
- **Calibrar e validar com ANA/Hidroweb e ORE-HYBAM.** Onde não houver estação para validar, mostrar sem validação local; considerar a cobertura esparsa das estações e o alcance regional da observação.
- Exigir pelo menos **três pixels de largura de rio, aproximadamente 30 m**, e máscara de nuvem SCL antes de usar o indicador.
- Turbidez anômala a jusante de garimpo é somente indício para eventual verificação de Fase 2, nunca prova. Respeitar as travas e o escopo da fase de verificação quando essa função for implementada.
- **Mercúrio fica fora do indicador:** satélite não o mede. Não exibir afirmação ou valor de mercúrio sem estudo de campo e fonte específica verificada.

## Fontes ainda não verificadas

Atualização da seção 6 de AUDITORIA_FONTES_HIBAMA.md:

- Se a ESA CCI Biomass v7.0 já existe no Earth Engine (oficial ou no catálogo
  comunitário `projects/sat-io/...`). Conferido de novo em 06/11: o
  comunitário segue na v6 (atualizado em 09/2025) e o oficial na v6. Para usar
  a v7 é preciso baixar o recorte do AM no CEDA e subir como asset próprio.
- Plataforma de download do SAD.
- Se a Rede Simex cede os polígonos para projeto acadêmico.
- Licença formal do TerraClass no GeoPortal.

Resolvidos em 06/11: licença do JRC TMF (livre, com atribuição), do CNFP (CC
Atribuição) e do MapBiomas (CC BY 4.0); hidrografia de referência para APP
(BHO 6 da ANA, que já usa a base do IBGE 1:250.000 na Amazônia).

Limite que fica registrado: na Amazônia a BHO 6 é 1:250.000, então igarapés
pequenos podem não aparecer e a APP deles não é calculada. Mostrar isso no
dossiê. Opção para depois: drenagem gerada a partir do ANADEM, comparada com a
hidrografia declarada no próprio CAR.

## Reprodução e verificação

- Guia de reprodução: **docs/REPLICAR.md**, distinguindo o pipeline AM existente da expansão nacional ainda pendente.
- Os scripts das camadas do Amazonas continuam usando ../dados/amazonas/; a generalização dessas camadas por UF fica para a expansão. A série nacional de focos da 2c-1 usa ../dados/brasil/. Os originais no pai permanecem preservados; usar as cópias mantidas no repositório.
- Não executar o coletor DETER antigo como substituto de coletar_deter_por_ano.py: gids históricos não são globalmente únicos.
- Validar geração completa, cruzamentos por CAR e qualidade espacial nas etapas correspondentes. Os verificadores atuais não substituem essa validação.
- Hospedagem oficial estática, demonstração com backend e distribuição dos dados seguem os destinos e dependências registrados acima. Nenhuma etapa nova está liberada por este registro.
