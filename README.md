# iHospitalUtility

| **Redes Sociais** | **Linguagens** | **Versão do .NET** | **Tecnologia** | **Último Commit** | **CI/CD** |
| ----------------- | -------------- | ------------------ | -------------- | ----------------- | ---------- |
| [![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/allan-debastiani/) | ![GitHub language count](https://img.shields.io/github/languages/count/allandeba/iHospitalUtility) ![GitHub top language](https://img.shields.io/github/languages/top/allandeba/iHospitalUtility) | ![GitHub target](https://img.shields.io/badge/.NET%20Core-8.0-green) | ![Blazor](https://img.shields.io/badge/blazor-%235C2D91.svg?style=for-the-badge&logo=blazor&logoColor=white) | ![GitHub last commit](https://img.shields.io/github/last-commit/allandeba/iHospitalUtility) | Coolify: build, testes e deploy |



## Visão Geral

Seja bem-vindo ao iHospitalUtility, um aplicativo intuitivo com o objetivo primario de calcular a idade gestacional corrigida.
Ele tem a possibilidade de instalar no celular e utilizar offline para facilitar acesso e calculo ao mais variados ambientes.

**Para utilizar o sistema, acesse: [iHospitalUtility.allandeba.dev.br](https://iHospitalUtility.allandeba.dev.br)**

## Tecnologias Utilizadas

- **Framework:** .Net Core 8.0 | Blazor WebAssembly | PWA
- **Testes Unitários:** xUnit
- **Conteinerização:** Docker
- **Hospedagem:** Servidor VPS Linux
- **UI:** MudBlazor

## CI/CD no Coolify

O GitHub mantém o código-fonte; build, testes e publicação são responsabilidade
exclusiva do recurso de produção do iHospitalUtility no Coolify, usando a branch
`main` e o `Dockerfile` deste repositório. Não há workflows de GitHub Actions
para deploy, limpeza por SSH ou notificações externas.

O build valida as regressões do Service Worker com Node e executa a suíte xUnit
em `Release` antes de publicar o Blazor. Um teste que falha ou uma execução xUnit
sem testes
interrompe o build: a imagem final não é gerada e a versão em execução não é
substituída. Os resultados aparecem nos logs de build do deploy no Coolify.
Os testes e seus relatórios não são copiados para a imagem pública do Nginx.

Para executar o mesmo gate localmente, sem instalar o SDK no host:

```bash
docker build --progress=plain -t ihospitalutility:local .
```

A configuração de rejeição de suíte vazia e timeout está em `ci.runsettings`.
Aprovação desta suíte comprova os cenários cobertos pelos testes, não validação
clínica nem cobertura integral de PWA, instalação e entradas inválidas.

## Uso offline

Na primeira abertura, mantenha a conexão até aparecer **Disponível offline**.
Antes disso, a tela informa que a preparação ainda está em andamento; uma falha
no download não é apresentada como disponibilidade offline. Depois da confirmação,
a página inicial, a calculadora e os links internos podem ser abertos/recarregados
sem rede, mesmo que a calculadora não tenha sido visitada durante a preparação.
Não é possível preparar o aplicativo pela primeira vez sem conexão.

A publicação gera `service-worker-assets.js` pelo SDK do Blazor, com versão e
integridade dos recursos. O worker mantém uma versão completa no cache, sem
depender de Workbox/CDN. Fontes externas são opcionais: sua indisponibilidade não
impede o uso offline. Não há cache genérico de dados ou requisições de escrita.

Uma versão nova aguarda as abas antigas fecharem, sem forçar recarga ou misturar
recursos de publicações diferentes. Para aplicar uma atualização, feche todas
as abas/janelas do aplicativo (inclusive a PWA instalada) e abra novamente.
Caches antigos deste aplicativo são removidos na ativação; preferências no
localStorage e caches de outros aplicativos não são apagados.

O modo offline deve ser testado em uma versão publicada. `dotnet run` utiliza
um worker de desenvolvimento sem precache, para evitar código antigo durante
edições locais.

### Testes da PWA

O Dockerfile exige os testes unitários JavaScript e xUnit antes de produzir a
imagem final. Os testes de navegador são uma verificação adicional, executada
contra os arquivos reais de um `dotnet publish`/build Docker, não contra o servidor
de desenvolvimento. Requerem Node 22+ e o Chromium do Playwright disponível.

```bash
node --test tests/pwa/service-worker.test.cjs
npm ci --prefix tests/pwa
npm exec --prefix tests/pwa -- playwright install chromium
npm run browser --prefix tests/pwa -- /caminho/para/wwwroot-publicado
npm run lifecycle --prefix tests/pwa -- /caminho/para/wwwroot-publicado
```

Os testes usam somente loopback e perfis descartáveis: primeira visita e recarga
sem rede, navegação/cálculo, atualização aguardando abas, preservação de
preferências e rejeição de um download com integridade incorreta. Para verificar
a migração do worker anterior, forneça também `PWA_LEGACY_DIR` apontando para uma
publicação da versão antiga ao executar `lifecycle`.
