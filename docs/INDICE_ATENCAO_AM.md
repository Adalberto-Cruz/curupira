# Índice de atenção por CAR — AM, regras v1.0.0

**Índice por regras sobre dados públicos. Não é laudo nem prova de infração. Modelo de IA (LightGBM) em desenvolvimento.**

Escopo: somente os CARs da base local do Amazonas. É a camada de priorização por regras solicitada para a apresentação, sem treinar, executar ou simular o LightGBM. A nota não é probabilidade de infração, precisão de modelo, regularidade ambiental ou avaliação de titularidade. Pesos são escolhas explícitas de priorização, ainda sem calibração ou validação de desempenho.

## Regra e pesos

Configuração versionada: `dist/data/atencao/pesos.json`. Os dados estáticos registram a versão e o SHA-256 dessa configuração.

1. Qualquer cruzamento TI ou embargo na base existente ativa **trava crítica: nota 100**. Duas travas não somam 200. A vigência dos embargos não foi revalidada: a fonte atual é a cópia IPAAM/Ibama já usada pelo projeto, não a futura base nacional. Interseção, inclusive contato na divisa, demanda conferência; não comprova infração nem titularidade.
2. Sem trava, somam-se os fatores abaixo, limitados a 100. Contribuições são arredondadas a uma casa decimal antes da soma.

| Fator | Cálculo | Máximo |
|---|---|---:|
| PRODES | 40 × fração da área geodésica do CAR coberta pela união dos polígonos PRODES | 40 |
| DETER | Soma de pontos por alerta e classe, limitada ao máximo do fator | 35 |
| ANM | 3 pontos por processo cruzado | 15 |
| Focos AM | 1 ponto por detecção cruzada na amostra | 10 |

| Classe DETER | Pontos por registro |
|---|---:|
| MINERACAO | 6 |
| CS_DESORDENADO, CS_GEOMETRICO, CORTE_SELETIVO | 4 |
| DESMATAMENTO_CR, DESMATAMENTO_VEG, DEGRADACAO | 2 |
| CICATRIZ_DE_QUEIMADA | 1 |

Exemplo sem trava: 25% PRODES = 10 pontos; um alerta de mineração + um corte geométrico + um desmatamento = 12; dois processos ANM = 6; três focos = 3. Nota = **31**. Um processo ANM não comprova mineração em atividade; o fator é contexto administrativo. Contagens DETER são registros de alertas e podem representar eventos relacionados/sobrepostos; não são eventos independentes comprovados.

Se houver trava, os fatores continuam visíveis como soma base e o campo “Complemento da trava crítica” acrescenta apenas o necessário para chegar a 100. Assim as contribuições exibidas sempre fecham a nota final. Uma nota 100 também pode resultar da soma saturada dos fatores sem trava; nesse caso o painel não declara trava.

## Fontes, áreas e recuperação de prévias

O lote usa as contagens e os registros já existentes em `dist/data/ambiental/intersecoes/{municipio}.json`. Ausência de um fator no mapa esparso significa nenhum cruzamento registrado naquele processamento, não ausência comprovada no território. Nenhuma nova coleta é executada.

Os cruzamentos antigos não possuem área PRODES e limitam a prévia a 20 registros. Portanto:

- A área é calculada com as geometrias originais locais do CAR (`dist/data/geometrias`) e os polígonos originais PRODES já disponíveis em `../dados/amazonas/brutos/ambiental/prodes_am.geojson`. Não se usa área do alerta inteiro, área declarada como denominador ou geometria simplificada de exibição.
- União/dissolução dos polígonos antes da interseção evita contar duas vezes a mesma área PRODES no CAR. A área é geodésica no elipsoide GRS80, em hectares; polígonos com orientação consistente e buracos preservados. A fração usada no escore é limitada a 0..1; as áreas medidas são preservadas, sem cortar a medida para forçar 100%.
- Geometrias inválidas são reparadas com make_valid(method='structure') em memória, seguindo o processamento herdado. Não se altera a geometria de origem. Reparação cartográfica não certifica limites cadastrais.
- Para prévias completas, recuperam-se os polígonos pelos IDs existentes. Para prévias truncadas, recuperam-se todos os hits com índice espacial sobre a fonte original; a contagem deve coincidir com a armazenada. DETER usa a fonte local `deter_am.geojson` e as classes completas, sem extrapolar as primeiras 20.
- Aplica-se o mesmo filtro territorial do preparador original: só entram feições que intersectam a malha original IBGE AM 2025. Isso é necessário, por exemplo, para CARs de divisa em Lábrea: uma feição fora da malha não pode aparecer apenas na recuperação e inflar a contagem. A regressão tem teste próprio.
- Divergência de contagem, ID ausente/repetido, classe sem peso, área inutilizável ou código inválido interrompem o lote. Uma execução parcial não recebe manifesto complete=true e não deve ser publicada.

PRODES: incrementos da base local de 2008 a 2025, sem inferir supressão recente ou ilegalidade. DETER: período completo disponível na cópia local, indicado no manifesto. TI: limites/fases Funai da cópia existente. Embargos: cópia IPAAM/Ibama, sem nova validação de vigência. Focos: **amostra AM de 29/10 a 04/11/2026, todos os satélites**; não é a série nacional de referência, nem número de incêndios únicos ou área queimada. ANM: processos SIGMINE locais. Não há decaimento temporal: a nota junta o contexto histórico dessas bases e janelas diferentes, que podem afetar a comparação.

O manifesto registra URLs, períodos e notas do catálogo ambiental, hashes das fontes PRODES/DETER/IBGE e, por município, hashes dos cadastros, geometrias, cruzamentos e saída. CARs podem se sobrepor; não somar áreas ou notas como área territorial única. Dados derivados mantêm as licenças das respectivas fontes, incluindo CC BY-SA 4.0 nos derivados PRODES/DETER; a licença MIT do código não relicencia os dados.

## Interface e ranking

- Nota 0–100 e contribuição de cada fator no dossiê e no detalhe do CAR no mapa.
- Aba **Imóveis que pedem atenção**, com seletor de município AM e até 20 registros com nota positiva, em ordem decrescente. Empates usam código CAR em ordem alfabética, sem critério oculto.
- Cadastros cancelados (CA) não entram no top 20; continuam com nota e situação no próprio detalhe. AT, PE e SU permanecem elegíveis.
- Cada linha abre o imóvel correspondente. O painel do mapa oferece link para a lista do município.
- Zero não comprova regularidade. Falha de carregamento ou CAR não localizado mostra “indisponível”, sem substituir por zero; permite nova tentativa. Respostas antigas não devem substituir a seleção atual.
- Somente código CAR identifica o imóvel. Nenhum nome de pessoa, CPF ou CNPJ é exportado ou exibido pelo novo produto.

## Reprodução e publicação

Usar o `.venv` existente, sem conda base e sem instalar pacotes no sistema:

```powershell
.\.venv\Scripts\python.exe tools/atencao_am.py --output work/atencao-am-NOVA-EXECUCAO
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_atencao_am.py'
node --test tests/test_atencao.cjs
```

O diretório de saída deve ser novo; o script recusa sobrescrever. Para esta entrega, foi passado `--deadline-utc 2026-11-06T15:45:00Z`, correspondente a 12h45 de Brasília. Se não houver versão estável até esse limite, não publicar; manter o site existente. Os resultados municipais e o manifesto só são copiados para `dist/data/atencao/` após conclusão e verificação do lote. `pesos.json` é configuração manual versionada; os demais resultados dessa pasta ficam ignorados pelo Git.

Após testes e revisão: apresentar lista/diff stat, obter confirmação de commit e publicar código a partir dele, com os dados gerados conferidos por SHA-256. O site S3/API Gateway exige gzip HTTP nos .json/.geojson comuns com Content-Encoding gzip e tipo correto. Os produtos .json.gz de focos permanecem sem Content-Encoding. Nenhum corpo transferido pode alcançar 10.000.000 bytes. Não incluir provas ou arquivos APP/RL. Sem push.
