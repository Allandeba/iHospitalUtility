# Fase base para servir os arquivos (imagem do Nginx ou outro servidor web)
FROM nginx:alpine AS base
WORKDIR /usr/share/nginx/html
EXPOSE 80

# Fase de build com o SDK do .NET para compilar o WebAssembly
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG configuration=Release
WORKDIR /src

# Copiar o projeto Blazor ou .NET WebAssembly
COPY ["src/iHospitalUtility/iHospitalUtility.csproj", "src/iHospitalUtility/"]
RUN dotnet restore "src/iHospitalUtility/iHospitalUtility.csproj"

# Copiar os arquivos restantes
COPY . .
WORKDIR "/src/src/iHospitalUtility"

# Build da aplicação WebAssembly
RUN dotnet publish "iHospitalUtility.csproj" -c $configuration -o /app/publish /p:UseAppHost=false

# Fase final, copiar os arquivos gerados para o servidor Nginx
FROM base AS final
WORKDIR /usr/share/nginx/html

# Copiar os arquivos de saída do build (arquivos .wasm, .html, .js, etc.)
COPY --from=build /app/publish/wwwroot ./
