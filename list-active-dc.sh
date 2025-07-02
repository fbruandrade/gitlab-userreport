#!/bin/bash

# Script para listar DeploymentConfigs com réplicas ativas por namespace no OpenShift
# Saída em formato CSV

# Nome do arquivo de saída
output_file="active_deploymentconfigs_$(date +%Y-%m-%d).csv"

# Adicionar cabeçalho ao CSV
echo "NAMESPACE,DEPLOYMENTCONFIG,READY_REPLICAS,DESIRED_REPLICAS,LATEST_VERSION,AGE,SELECTOR" > "$output_file"

# Buscar todos os namespaces
for namespace in $(oc get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    # Buscar DCs com réplicas prontas > 0
    dcs=$(oc get dc -n "$namespace" -o jsonpath='{range .items[?(@.status.readyReplicas>0)]}{.metadata.name}{"\n"}{end}' 2>/dev/null)

    if [ -n "$dcs" ]; then
        while read -r dc; do
            # Obter informações detalhadas do DC
            ready_replicas=$(oc get dc "$dc" -n "$namespace" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || echo "0")
            desired_replicas=$(oc get dc "$dc" -n "$namespace" -o jsonpath='{.spec.replicas}' 2>/dev/null || echo "0")
            latest_version=$(oc get dc "$dc" -n "$namespace" -o jsonpath='{.status.latestVersion}' 2>/dev/null || echo "")
            created=$(oc get dc "$dc" -n "$namespace" -o jsonpath='{.metadata.creationTimestamp}' 2>/dev/null || echo "")

            # Calcular idade
            if [ -n "$created" ]; then
                created_sec=$(date -d "$created" +%s 2>/dev/null)
                current_sec=$(date +%s)
                age_sec=$((current_sec - created_sec))
                age_days=$((age_sec / 86400))
                age="${age_days}d"
            else
                age=""
            fi

            # Obter seletores (labels usados para identificar pods)
            selector=$(oc get dc "$dc" -n "$namespace" -o jsonpath='{.spec.selector}' 2>/dev/null | tr -d '{}' | tr ',' '/' || echo "")

            # Adicionar linha ao CSV (escapando vírgulas nos valores)
            echo "\"$namespace\",\"$dc\",\"$ready_replicas\",\"$desired_replicas\",\"$latest_version\",\"$age\",\"$selector\"" >> "$output_file"
        done <<< "$dcs"
    fi
done

echo ""                                                              
echo "Relatório CSV gerado em: $output_file"
echo "Total de DeploymentConfigs ativos: $(cat "$output_file" | wc -l | xargs expr - 1) em $(oc get namespaces -o jsonpath='{.items}' | jq '. | length') namespaces"
echo ""
echo "Você pode abrir este arquivo em Excel/LibreOffice ou visualizar com:"
echo "column -s, -t < $output_file | less -S"
