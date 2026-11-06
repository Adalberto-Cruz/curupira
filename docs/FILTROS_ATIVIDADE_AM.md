# Filtros por atividade — contexto ambiental AM

Atalhos na seção de camadas do mapa, somente sobre dados já existentes. Não treinam IA, classificam uso do solo ou comprovam atividade observada/infração. O índice de atenção por CAR não é alterado pelos atalhos.

| Atalho | Camadas ligadas | Classe DETER |
|---|---|---|
| Terras Indígenas | TI | Todas |
| Desmatamento | PRODES + DETER | DESMATAMENTO_CR + DESMATAMENTO_VEG |
| Focos de calor e queimadas | Focos Brasil + DETER | CICATRIZ_DE_QUEIMADA |
| Áreas embargadas | Embargos | Todas |
| Exploração madeireira | DETER | CS_DESORDENADO + CS_GEOMETRICO + CORTE_SELETIVO |
| Garimpo e mineração | DETER + processos ANM | MINERACAO |
| APP | Desativado | Em desenvolvimento |
| Reserva Legal | Desativado | Em desenvolvimento |
| Desmatamento para pastagem | Desativado | Em desenvolvimento |

Os atalhos são ações: ligam suas camadas e substituem o filtro de classe DETER. Outras camadas já ligadas, datas, opacidade, base e CAR selecionado são preservados. O texto do bloco informa esse comportamento. ANM continua sendo contexto administrativo, não comprovação de lavra ou garimpo. Focos Brasil continua a série de referência nacional; DETER/camadas ambientais têm o recorte AM existente e seus próprios períodos. O período ambiental não filtra os focos nacionais.

Sem município selecionado, nenhum atalho é aplicado e aparece “Selecione um município”. Para seleção fora do AM, informa-se que o contexto ambiental local só está disponível no Amazonas. Não há nova coleta, geração de dados ou inferência de pastagem.

Grupos de desmatamento e corte seletivo também aparecem no seletor de classes. Os valores ATIVIDADE_DESMATAMENTO e ATIVIDADE_CORTE_SELETIVO são filtros de interface, não classes inventadas na base. São serializados no parâmetro classe do link; restauração do link e histórico usam os mesmos grupos. Selecionar uma classe específica continua funcionando.

TI e DETER passam a ficar ligados por padrão, conforme pedido anterior. As camadas ambientais aparecem após selecionar um município; uma visão sem município não baixa todos os recortes do AM. Links com camadas explicitamente escolhidas continuam respeitados. “Limpar filtros” restaura o novo padrão.

Arquivos principais: dist/assets/atividades.js, ambiental.js, map-tools.js e map-state.js. A página mapa.html carrega o módulo antes dos executores e usa novos parâmetros de versão para evitar cache antigo.

Testes: mapeamento dos seis atalhos, grupos completos, rejeição sem município, três opções indisponíveis, preservação de filtros/CAR, restauração por URL e padrão TI/DETER. O teste de renderização ambiental existente carrega a mesma dependência nova. Testar visualmente no navegador local e conferir publicação por HTTPS antes do aceite; o navegador integrado não acessa sites externos e o Chrome público fica com o usuário.

Prazo desta entrega: estabilidade/publicação até 12h45 de Brasília em 06/11/2026. Sem push e sem alterações no motor APP/RL. Lista e diff stat devem preceder o commit, conforme o fluxo de revisão vigente.
