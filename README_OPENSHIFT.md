# Scripts para Listar DeploymentConfigs Ativos no OpenShift

Esta pasta contém scripts para listar DeploymentConfigs que possuem réplicas ativas em um cluster OpenShift, organizados por namespace.

## Requisitos

- Cliente OpenShift (`oc`) instalado e configurado
- Acesso a um cluster OpenShift
- Estar logado no cluster (`oc login`)

## Scripts Disponíveis

### 1. Script Completo (`list-active-dc.sh`)

Este script gera um relatório CSV completo com informações detalhadas sobre todos os DeploymentConfigs com réplicas ativas:

- **Namespace**: O namespace onde o DeploymentConfig está localizado
- **DeploymentConfig**: Nome do DeploymentConfig
- **Ready_Replicas**: Número de réplicas prontas
- **Desired_Replicas**: Número de réplicas desejadas
- **Latest_Version**: Versão mais recente do DeploymentConfig
- **Age**: Idade do DeploymentConfig
- **Selector**: Seletores usados para identificar pods

#### Uso

```bash
# 1. Tornar o script executável
chmod +x list-active-dc.sh

# 2. Executar o script
./list-active-dc.sh
```

O script gerará um arquivo CSV com o formato `active_deploymentconfigs_YYYY-MM-DD.csv`.

### 2. Script Simples (`list-active-dc-simple.sh`)

Uma versão simplificada que imprime diretamente para a saída padrão (stdout) em formato CSV, contendo apenas:

- **Namespace**: O namespace onde o DeploymentConfig está localizado
- **DeploymentConfig**: Nome do DeploymentConfig
- **Ready_Replicas**: Número de réplicas prontas
- **Desired_Replicas**: Número de réplicas desejadas

#### Uso

```bash
# 1. Tornar o script executável
chmod +x list-active-dc-simple.sh

# 2. Executar o script
./list-active-dc-simple.sh

# 3. Redirecionar para um arquivo (opcional)
./list-active-dc-simple.sh > meus_dcs_ativos.csv
```

## Exemplos de Uso

### Filtrar por namespace específico

```bash
# Usando grep para filtrar por namespace
./list-active-dc-simple.sh | grep "\"meu-namespace\""
```

### Abrir no Excel/LibreOffice

Após gerar o arquivo CSV, você pode abri-lo diretamente em qualquer aplicativo de planilha.

### Visualizar no terminal

```bash
# Formatar como tabela no terminal
column -s, -t < active_deploymentconfigs_2025-07-02.csv | less -S
```

## Solução de Problemas

- **Sem resultados**: Verifique se você está logado no cluster correto (`oc whoami`)
- **Erros de permissão**: Verifique se você tem permissões para listar DeploymentConfigs em diferentes namespaces
- **Script não executável**: Use `chmod +x script.sh` para tornar o script executável

## Notas

- Os DeploymentConfigs listados são apenas aqueles com réplicas prontas > 0
- Os scripts ignoram silenciosamente namespaces aos quais você não tem acesso
- O formato CSV permite fácil importação para ferramentas de análise
