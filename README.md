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

O build restaura as dependências, compila e executa a suíte xUnit em `Release`
antes de publicar o Blazor. Um teste que falha ou uma execução sem testes
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
