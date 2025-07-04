#!/bin/bash

# Script simples para listar DeploymentConfigs com réplicas ativas
# Saída em formato CSV diretamente para stdout

# Imprimir cabeçalho
echo "NAMESPACE,DEPLOYMENTCONFIG,READY_REPLICAS,DESIRED_REPLICAS"

# Para cada namespace
for ns in $(oc get namespaces -o jsonpath='{.items[*].metadata.name}'); do
    # Buscar DCs com réplicas prontas > 0
    oc get dc -n $ns -o jsonpath='{range .items[?(@.status.readyReplicas>0)]}{"\""}{$.metadata.namespace}{"\""},{"\""}{.metadata.name}{"\""},{"\""}{.status.readyReplicas}{"\""},{"\""}{.spec.replicas}{"\""}{"\
"}{end}' 2>/dev/null
done
