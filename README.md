# CodeAnalyzer

| **Redes Sociais** | **Linguagens** | **Versão do .NET** | **Último Commit** |
| ----------------- | -------------- | ------------------ | ----------------- |
| [![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-blue)](https://www.linkedin.com/in/allan-debastiani/) | ![GitHub language count](https://img.shields.io/github/languages/count/allandeba/CodeAnalyzer) ![GitHub top language](https://img.shields.io/github/languages/top/allandeba/CodeAnalyzer) | ![GitHub target](https://img.shields.io/badge/.NET%20Core-8.0-green) | ![GitHub last commit](https://img.shields.io/github/last-commit/allandeba/CodeAnalyzer) |


## Visão Geral

Seja bem-vindo ao CodeAnalyzer, um aplicativo com o objetivo de auxiliar na validação de padrões de código.

## Padronização

- `StrictNaming`: O nome dos arquivos devem ser o mesmo da classe
- `Quantidade de objetos dentro de um arquivo`: Todos os arquivos devem conter um único objeto dentro de cada arquivo
Ou seja, não pode existir dentro de um arquivo `EMeuEnumType.cs` outro objeto além de `EMeuEnumType`

## Tecnologias Utilizadas

- **Framework:** .Net Core 8.0 | Console Application

## ⚙️ Configuração da aplicação

- Inicie o JSON com as informações pertinentes do seu projeto em `appSettings.json`:
`IgnoredFiles`: Lista de string contendo todos os arquivos que devem ser ignorados na verificação
`StrictNaming`: Variavel booleana onde identifica se o nome do arquivo deve ser o mesmo da classe dentro do arquivo
```json
{
    "AnalyzerConfig": {
      "IgnoredFiles": [
        "Program.cs",
        "GlobalUsings.g.cs",
        "MvcApplicationPartsAssemblyInfo.cs",
        ".NETCoreApp,Version=v8.0.AssemblyAttributes.cs",
        "AssemblyInfo.cs"
      ],
      "StrictNaming": true,
    }
}
```

## 👤 Utilização

- Execute o comando `dotnet run` em seu terminal
- Cole o path para a pasta que deseja analisar.
Exemplo: `C://Repositorios/MeuProjeto/`
- Ele retornará no console os arquivos que estão fora do [padrão](https://github.com/Allandeba/CodeAnalyzer/edit/main/README.md#padroniza%C3%A7%C3%A3o)
