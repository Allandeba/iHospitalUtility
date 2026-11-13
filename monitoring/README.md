# Monitoramento operacional no Grafana

Pasta **iHospitalUtility**, dashboard UID `ihospitalutility-overview`:
https://monitor.allandeba.dev.br/d/ihospitalutility-overview

## Caminho dos dados

```text
HTTPS da aplicação → monitor Python (60 s) → Prometheus / Loki → Grafana
```

A aplicação é Blazor WebAssembly/PWA estática. O monitor consulta somente três
recursos públicos fixos: página inicial, `/_framework/blazor.boot.json` e
`/service-worker-assets.js`. Exige certificado confiável, HTTP 200 e formato/
marcador esperado. Mede duração, resultado, status HTTP, validade do certificado
e idade da coleta. Redirecionamentos são rejeitados. Não lê logs de usuários.

O histórico de métricas usa a retenção compartilhada atual do Prometheus:
7 dias, limitada também a 1 GB. Registros das verificações usam Loki: 72 horas.
A coleta não reconstrói períodos anteriores. Ausência ou coleta antiga não é
tratada como disponibilidade confirmada. A disponibilidade histórica se refere
às verificações efetivamente recebidas; não preenche lacunas como sucesso.

## Privacidade e limites

- Sem corpo/resposta, IP de usuário, query string, cookie, identificador ou dado
  clínico exportado. Apenas check fixo, código técnico limitado e números.
- Não instrumenta cálculos, JavaScript, uso offline, sessões, acessos reais,
  consumo do contêiner da aplicação ou validação clínica.
- Verificar os arquivos da PWA não prova instalação nem funcionamento offline.
- Sondas feitas neste servidor; não são teste de conectividade de outro local.
- Não há alertas de notificação ou envio Telegram nesta implementação.

## Operação gerenciada

`compose.monitoring.yaml` é um recurso Coolify próprio, no projeto
**iHospitalUtility**, independente do recurso que publica a aplicação.
A branch `monitoring/grafana` mantém somente essa adição; `main` e o trabalho
PWA em revisão não são alterados. O recurso fica fixado no commit validado,
sem autodeploy/previews nem domínio público. Nenhum backend de observabilidade
ou contêiner da aplicação precisa reiniciar para adicioná-lo.

O contêiner é não-root, somente leitura, sem mounts do host/socket Docker,
sem portas publicadas, com 64 MiB e 0,1 CPU. A rede privada externa
`isalesnotify-observability-ingest` dá acesso aos backends existentes; a rede
padrão permite consultar o HTTPS público. Heartbeat só fica saudável após
exportação de métricas aceita, expira em 180 s. Falha de Loki é registrada,
sem filas de crescimento ilimitado; falha dos backends não afeta a aplicação.

A pasta e o painel são salvos no banco persistente do Grafana pela API nativa.
`dashboard.json` é a definição versionada; não editar arquivos gerados em runtime.
Para reaplicar, enviar pela API `/api/dashboards/db` com folderUid
`ihospitalutility`, overwrite=true e reler o UID exato. Credenciais nunca entram
neste repositório. Um backup privado validado é preservado pelo operador.

## Testes e recuperação

```bash
python3 -m unittest discover -s monitoring -v
docker compose -f compose.monitoring.yaml config --quiet
docker build -f Dockerfile.monitoring -t ihospitalutility-monitor:local .
```

O Dockerfile exige os testes antes do runtime. Aceitação: consultar amostras
reais pelo Grafana, logs reais das sondas, checar frescor, renderização desktop/
mobile e preservar os recursos anteriores.

Para reverter só esta adição: parar o recurso **ihospitalutility-monitoring** no
Coolify e remover apenas o dashboard/pasta identificados acima via API/UI.
Isso não remove a aplicação nem seus arquivos, os demais dashboards ou dados
históricos dos backends. Não restaurar um SQLite antigo por cima de mudanças
posteriores de outros sistemas; o backup integral é recuperação de último caso.
