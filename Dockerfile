# Runtime: Coolify publica somente os arquivos estáticos aprovados pela CI.
FROM nginx:alpine AS base
WORKDIR /usr/share/nginx/html
EXPOSE 80
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Build e CI usam a mesma versão do SDK e o mesmo código-fonte.
FROM --platform=$BUILDPLATFORM mcr.microsoft.com/dotnet/sdk:8.0 AS build
ARG configuration=Release
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
WORKDIR /src

COPY ["src/iHospitalUtility/iHospitalUtility.csproj", "src/iHospitalUtility/"]
COPY ["src/tests/iHospitalUtility-Test-Unit/iHospitalUtility-Test-Unit.csproj", "src/tests/iHospitalUtility-Test-Unit/"]
RUN dotnet restore "src/tests/iHospitalUtility-Test-Unit/iHospitalUtility-Test-Unit.csproj" --disable-parallel

COPY . .

# Gate obrigatório: falha ou ausência de testes impede publish e imagem final.
RUN dotnet test "src/tests/iHospitalUtility-Test-Unit/iHospitalUtility-Test-Unit.csproj" \
    -c "$configuration" --no-restore --settings /src/ci.runsettings \
    --logger "console;verbosity=normal" --logger "trx;LogFileName=unit-tests.trx" \
    --results-directory /ci-results -m:1 /p:UseSharedCompilation=false

RUN dotnet publish "src/iHospitalUtility/iHospitalUtility.csproj" \
    -c "$configuration" --no-restore -o /app/publish \
    /p:UseAppHost=false /p:UseSharedCompilation=false -m:1

FROM base AS final
WORKDIR /usr/share/nginx/html
COPY --from=build /app/publish/wwwroot ./
