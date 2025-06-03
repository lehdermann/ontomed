# OntoMed API

This directory contains a REST API for the OntoMed framework, providing HTTP endpoints for interacting with the semantic and prompt modules.

## Installation

### Standard Installation

Ensure you have installed the required dependencies:

```bash
pip install -r ../requirements.txt
```

### Docker Installation (Recommended for Demonstrations)

For a complete demonstration environment with pre-loaded data, use the Docker setup:

```bash
cd ../docker
./start_services.sh
```

This will start both the API server and a BlazegraphDB instance with sample medical concepts already loaded.

## Starting the API Server

### Manual Start

To start the API server manually, run:

```bash
python server.py
```

By default, the server will run on `http://127.0.0.1:8000`. You can customize the host, port, and other options:

```bash
python server.py --host 0.0.0.0 --port 8080 --reload --log-level debug
```

### Docker Start (With Pre-loaded Data)

When using Docker, the API is automatically started and configured to connect to BlazegraphDB:

```bash
cd ../docker
./start_services.sh
```

## API Documentation

Once the server is running, you can access the interactive API documentation at:

- Swagger UI: `http://127.0.0.1:8000/docs` (or `http://localhost:8000/docs` when using Docker)
- ReDoc: `http://127.0.0.1:8000/redoc` (or `http://localhost:8000/redoc` when using Docker)

## API Endpoints

### Semantic Module

- `GET /semantic/concepts/{concept_id}` - Get a concept by ID
- `POST /semantic/concepts/` - Create a new concept
- `POST /semantic/concepts/query/` - Query concepts with filters
- `DELETE /semantic/concepts/{concept_id}` - Delete a concept (not implemented yet)

### Prompt Module

- `GET /prompt/templates/` - List all available templates
- `GET /prompt/templates/{template_id}` - Get a template by ID
- `POST /prompt/templates/` - Create a new template
- `POST /prompt/templates/upload/` - Upload a template file (YAML or JSON)
- `POST /prompt/fill/` - Fill a template with parameters

## Example Usage

### Pre-loaded Data (Docker Environment)

When using the Docker setup, the following medical concepts are pre-loaded:

- **Hypertension**: With causes, symptoms, complications, and treatments
- **DiabetesMellitus**: Type 2 diabetes with related medical information
- **Asthma**: With triggers, symptoms, and treatment options

You can immediately query these concepts without adding them first.

### Creating a New Concept

```bash
curl -X POST "http://localhost:8000/semantic/concepts/" \
     -H "Content-Type: application/json" \
     -d '{
           "id": "Migraine",
           "label": "Migraine Headache",
           "relationships": [
             {
               "type": "hasCause",
               "target": "GeneticPredisposition",
               "label": "Genetic Predisposition"
             },
             {
               "type": "hasSymptom",
               "target": "ThrobbingPain",
               "label": "Throbbing Pain"
             },
             {
               "type": "hasTreatment",
               "target": "Triptans",
               "label": "Triptans"
             }
           ]
         }'
```

### Retrieving a Concept

```bash
curl -X GET "http://localhost:8000/semantic/concepts/Hypertension"
```

### Semantic Query

```bash
curl -X GET "http://localhost:8000/semantic/query/?query=SELECT%20%3Fsymptom%20%3Flabel%20WHERE%20%7B%20med%3AHypertension%20med%3AhasSymptom%20%3Fsymptom%20.%20%3Fsymptom%20rdfs%3Alabel%20%3Flabel%20.%20%7D"
```

### Complete Demonstration

For a full demonstration of all features, run:

```bash
cd ../examples
python demonstration.py
```

This script demonstrates querying existing concepts, adding new ones, performing semantic queries, and generating medical explanations.

### Filling a Template

```bash
curl -X POST "http://127.0.0.1:8000/prompt/fill/" \
     -H "Content-Type: application/json" \
     -d '{
           "template_id": "diagnostic_explanation",
           "parameters": {
             "condition": "Hypertension",
             "medical_concepts": "- Caused by: Genetic Factors\n- Symptom: Headache",
             "patient_data": {
               "age": 62,
               "gender": "female",
               "risk_factors": ["Family history", "High-sodium diet"]
             }
           }
         }'
```

## Error Handling

The API returns appropriate HTTP status codes and error messages for different error conditions:

- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server-side error

Error responses follow this format:

```json
{
  "detail": "Error message describing the problem"
}
```

## Security Considerations

For production deployment, consider:

1. Restricting CORS settings to specific origins
2. Adding authentication (e.g., OAuth2, API keys)
3. Using HTTPS
4. Implementing rate limiting
