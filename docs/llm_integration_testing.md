# OntoMed LLM Integration Testing Guide

This guide describes how to test the integration of OntoMed with Large Language Models (LLMs) for content generation, embeddings, and structured responses.

## Prerequisites

1. OntoMed installed and configured
2. Access to an LLM API (OpenAI, Anthropic, etc.)
3. Environment variables configured with the necessary API keys
4. Templates loaded in the system (including `concept_embedding.yaml`)

## 1. Testing Embedding Generation

Embedding generation is essential for semantic representation of medical concepts. To test:

### Via Dashboard

1. Go to the **Generator** page in the dashboard
2. Select a medical concept from the list
3. Choose an "Embedding" type template (e.g., `concept_embedding`)
4. Click on "Generate Content"
5. Verify that the embedding is generated and displayed correctly

### Via Direct API

```bash
# Test embedding generation via API
curl -X POST "http://localhost:8000/api/llm/embedding" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "text": "Hypertension is a medical condition characterized by high blood pressure in the arteries",
    "template_id": "concept_embedding"
  }'
```

### Via Python

```python
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Generate embedding for a text
embedding = api_client.get_embedding("Hypertension is a medical condition characterized by high blood pressure in the arteries")

# Check the result
print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")
```

## 2. Testing Text Content Generation

### Via Dashboard

1. Go to the **Generator** page in the dashboard
2. Select a medical concept from the list
3. Choose a "Text" type template
4. Adjust the generation parameters (temperature, max_tokens)
5. Click on "Generate Content"
6. Verify that the text content is generated and displayed correctly

### Via Direct API

```bash
# Test content generation via API
curl -X POST "http://localhost:8000/api/llm/generate" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "prompt": "Explain hypertension in simple terms for a patient",
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Via Python

```python
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Generate text content
content = api_client.generate_content(
    prompt="Explain hypertension in simple terms for a patient",
    temperature=0.7,
    max_tokens=500
)

# Check the result
print(content)
```

## 3. Testing Structured Content Generation

### Via Dashboard

1. Go to the **Generator** page in the dashboard
2. Select a medical concept from the list
3. Choose a "Structured" type template
4. Adjust the generation parameters
5. Click on "Generate Content"
6. Verify that the structured content (JSON) is generated and displayed correctly

### Via Direct API

```bash
# Test structured content generation via API
curl -X POST "http://localhost:8000/api/llm/structured" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "prompt": "Provide structured information about hypertension",
    "schema": {
      "type": "object",
      "properties": {
        "name": {"type": "string"},
        "symptoms": {"type": "array", "items": {"type": "string"}},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
        "treatments": {"type": "array", "items": {"type": "string"}}
      }
    },
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Via Python

```python
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Generate structured content
structured_content = api_client.generate_structured(
    prompt="Provide structured information about hypertension",
    temperature=0.7,
    max_tokens=500
)

# Check the result
import json
print(json.dumps(structured_content, indent=2, ensure_ascii=False))
```

## 4. Testing Automatic Template Loading

To verify if the system is automatically loading templates:

1. Go to the **Generator** page in the dashboard
2. Check if the templates are available in the dropdown list
3. Alternatively, use the API to list available templates:

```bash
# List available templates
curl -X GET "http://localhost:8000/api/templates" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## 5. Testing Fallbacks and Error Handling

To test the system's robustness in case of failures:

### Template Fallback Test

1. Try to generate content with a non-existent template:

```python
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

try:
    # Try to generate content with non-existent template
    content = api_client.generate_content(
        prompt="Test",
        template_id="non_existent_template"
    )
    print("Content generated with fallback:", content)
except Exception as e:
    print("Error:", str(e))
```

### Relationships Fallback Test

```python
from utils.api_client import APIClient

# Initialize API client
api_client = APIClient()

# Try to get relationships with invalid ID
relationships = api_client.get_relationships("non_existent_concept")
print("Fallback result:", relationships)
```

## 6. Verificação de Logs

Para uma análise mais detalhada, verifique os logs do sistema:

```bash
# Verificar logs da API
docker logs ontomed-api

# Verificar logs do dashboard
docker logs ontomed-dashboard
```

## Resolução de Problemas Comuns

### Erro de Autenticação com a API do LLM

- Verifique se a variável de ambiente com a chave da API está configurada corretamente
- Confirme se a chave da API não expirou ou foi revogada
- Verifique se o formato da chave está correto

### Templates Não Aparecem no Dashboard

- Verifique se os arquivos de template estão no diretório correto (`prompt/templates/`)
- Confirme se os arquivos têm a extensão `.yaml` ou `.yml`
- Verifique os logs para erros de validação de templates

### Erro na Geração de Embeddings

- Verifique se o template `concept_embedding.yaml` existe e está correto
- Confirme se o modelo de embedding está disponível e configurado
- Verifique se o conceito contém dados suficientes para gerar um embedding significativo

### Comunicação entre Serviços em Docker

- Verifique se os serviços estão usando os nomes corretos para comunicação (`api` em vez de `localhost`)
- Confirme se as variáveis de ambiente `ONTO_MED_API_URL` estão configuradas corretamente
- Verifique se todos os serviços estão em execução com `docker-compose ps`

## Conclusão

Este guia fornece os passos básicos para testar a integração do OntoMed com LLMs. Ao seguir estes procedimentos, você pode verificar se o sistema está corretamente configurado para gerar embeddings, conteúdo textual e respostas estruturadas usando modelos de linguagem.
