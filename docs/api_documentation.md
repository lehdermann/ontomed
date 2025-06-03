# OntoMed API Documentation
# OntoMed API Documentation

## Overview

The OntoMed API provides a RESTful interface for interacting with the OntoMed framework, including LLM integration for content generation, knowledge graph management, and semantic relationship processing.

## API Endpoints

### LLM Integration

#### 1. Generate Content

- **Endpoint**: `/api/llm/generate`
- **Method**: POST
- **Description**: Generate content using the LLM based on a prompt or template.

**Request Body**:
```json
{
    "prompt": "string",
    "temperature": 0.7,
    "max_tokens": 500,
    "template_id": "optional"
}
```

**Response**:
```json
{
    "success": true,
    "content": "generated text"
}
```

#### 2. Generate Embedding

- **Endpoint**: `/api/llm/embedding`
- **Method**: POST
- **Description**: Generate vector embeddings for text using the LLM.

**Request Body**:
```json
{
    "text": "string",
    "template_id": "optional"
}
```

**Response**:
```json
{
    "success": true,
    "embedding": [float, float, ...]
}
```

#### 3. Generate Structured Response

- **Endpoint**: `/api/llm/structured`
- **Method**: POST
- **Description**: Generate a structured JSON response using the LLM.

**Request Body**:
```json
{
    "prompt": "string",
    "schema": {"json": "schema"},
    "temperature": 0.7,
    "max_tokens": 500
}
```

**Response**:
```json
{
    "success": true,
    "response": {"json": "object"}
}
```

### Semantic Integration

#### 1. List Concepts

- **Endpoint**: `/api/concepts`
- **Method**: GET
- **Description**: Retrieve all concepts from the semantic database.

**Response**:
```json
[
    {
        "id": "concept_uri",
        "label": "Concept Name",
        "type": "Concept Type",
        "relationships": []
    },
    ...
]
```

#### 2. Get Concept

- **Endpoint**: `/api/concepts/{concept_id}`
- **Method**: GET
- **Description**: Retrieve a specific concept by ID.

**Response**:
```json
{
    "id": "concept_uri",
    "label": "Concept Name",
    "type": "Concept Type",
    "relationships": [
        {
            "type": "relationship_type",
            "target": "target_concept_uri",
            "label": "relationship_label"
        },
        ...
    ]
}
```

#### 3. Get Concept Relationships

- **Endpoint**: `/api/concepts/relationships/{concept_id}`
- **Method**: GET
- **Description**: Retrieve all relationships for a specific concept.

**Response**:
```json
[
    {
        "type": "relationship_type",
        "target": "target_concept_uri",
        "label": "relationship_label"
    },
    ...
]
```

#### 4. Get Graph Statistics

- **Endpoint**: `/api/statistics`
- **Method**: GET
- **Description**: Retrieve detailed statistics about the ontology.

**Response**:
```json
{
    "total_concepts": 76,
    "total_relationships": 21,
    "class_count": 76,
    "subclass_count": 68,
    "annotation_count": 120,
    "axiom_count": 4,
    "property_count": 44
}
```

**Field Descriptions**:
- `total_concepts`: Total number of concepts in the ontology
- `total_relationships`: Total number of relationships between concepts
- `class_count`: Number of classes defined in the ontology
- `subclass_count`: Number of subclass relationships
- `annotation_count`: Number of annotations associated with ontology elements
- `axiom_count`: Number of logical axioms (equivalentClass, disjointWith, etc.)
- `property_count`: Total number of properties (ObjectProperty, DatatypeProperty, AnnotationProperty)

**Error Handling**:
- If the concept is not found, returns a 404 error
- If relationships cannot be retrieved in the standard format, the API will attempt multiple fallback strategies:
  1. Try to extract relationships from the full concept
  2. Search for the concept in the complete list of concepts
  3. Return an empty list if all fallbacks fail

#### 4. Upload Ontology

- **Endpoint**: `/api/ontologies/upload`
- **Method**: POST
- **Description**: Upload and load an ontology file into the semantic database.

**Request**:
- Multipart form data with a file field containing the ontology file
- Supported formats: RDF/XML, Turtle, JSON-LD, OWL

**Response**:
```json
{
    "success": true,
    "message": "Ontology uploaded and loaded successfully"
}
```

### Template Management

#### 1. List Templates

- **Endpoint**: `/api/templates`
- **Method**: GET
- **Description**: List all available templates.

**Response**:
```json
[
    {
        "id": "template_id",
        "name": "Template Name",
        "type": "text|structured|embedding",
        "category": "category_id",
        "description": "Template description"
    },
    ...
]
```

#### 2. Get Template

- **Endpoint**: `/api/templates/{template_id}`
- **Method**: GET
- **Description**: Get a specific template by ID.

**Response**:
```json
{
    "id": "template_id",
    "name": "Template Name",
    "type": "text|structured|embedding",
    "category": "category_id",
    "content": "Template content with {{variables}}",
    "variables": ["variable1", "variable2"],
    "description": "Template description"
}
```

## Error Handling

All API endpoints follow a consistent error handling pattern:

```json
{
    "success": false,
    "error": "Error message",
    "code": "ERROR_CODE"
}
```

The API implements multiple fallback strategies for critical operations to ensure robustness:

1. **Relationship Retrieval**: Multiple methods to extract relationships from different data structures
   - Primary endpoint: `/api/concepts/relationships/{concept_id}`
   - Fallback 1: Extract from full concept data
   - Fallback 2: Search in complete concept list
   
2. **Template Loading**: Graceful handling of missing templates with informative error messages
   - Templates are loaded automatically from the filesystem
   - The system provides clear error messages when templates are missing
   - Default templates are included for common operations like concept embedding

3. **Concept Lookup**: Alternative methods to find concepts when primary lookup fails
   - Robust handling of different ID formats and special characters
   - Support for extracting readable labels from URIs
   - Fallback to ID when label is not available

## Authentication

The API requires an API key for authentication. The key should be provided in the request headers:

```http
Authorization: Bearer YOUR_API_KEY
```

## Error Handling

The API returns standardized error responses:

```json
{
    "success": false,
    "error": "error message",
    "code": "error_code"
}
```

## Example Usage

### Using Python

```python
import requests

url = "http://localhost:8000/llm/generate"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

data = {
    "prompt": "Explique o que é diabetes",
    "temperature": 0.7,
    "max_tokens": 500
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### Using cURL

```bash
curl -X POST \
  http://localhost:8000/llm/generate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explique o que é diabetes",
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

## API Documentation

The full API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
