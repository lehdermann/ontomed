# OntoMed

**A Framework for Medical Ontology Management and Structured Template Engineering**

## Overview

OntoMed is a modular framework for managing medical knowledge using semantic technologies, natural language processing, and structured prompt management. The system addresses the challenge of organizing medical knowledge in a structured format while enabling natural language interaction with medical ontologies through a conversational interface.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

## Key Features

- **Semantic Knowledge Management**: Store and query medical knowledge in a semantically rich format
- **Natural Language Processing**: Interact with medical ontologies through a conversational interface
- **Prompt Template Management**: Create, validate, and manage templates for medical content generation
- **Interactive Visualization**: Explore semantic relationships through a graph-based interface
- **LLM Integration**: Generate concept embeddings and enhance responses with large language models
- **Modular Architecture**: Based on object-oriented design principles for maintainability and extensibility
- **Containerized Deployment**: Docker support for simplified deployment and scalability

## System Architecture

OntoMed's architecture is organized into five main modules:

```
OntoMed/
├── core/                # Shared utilities
├── semantic/            # Semantic database connectors and services
├── nlp/                 # Natural language processing components
├── prompt/              # Template management and validation
├── api/                 # REST API for system integration
├── dashboard/           # Interactive web interface
├── examples/            # Usage examples
├── docker/              # Containerization and deployment
└── docs/                # Documentation
```

## Modules

### 1. Semantic Module

Manages the storage and retrieval of medical concepts in a semantically rich format:

- Graph database connectors with abstract interfaces
- SPARQL query processing with robust error handling
- Relationship inference and concept mapping
- Statistical analysis of ontology structure

### 2. NLP Module

Enables natural language interaction with the medical ontology:

- Entity recognition for medical terminology
- Intent classification for query understanding
- Bifurcated processing pipeline for efficiency
- Conversation context management
- Integration with LLMs for enhanced responses

### 3. Prompt Module

Manages templates for medical content generation:

- Template validation with schema enforcement
- Variable substitution and formatting
- Category management and organization
- Template suggestions based on context
- Integration with LLMs for content enhancement

### 4. API Module

Provides RESTful endpoints for system integration:

- Concept retrieval and relationship queries
- Template management operations
- Natural language query processing
- Authentication and rate limiting
- Comprehensive error handling

## Installation and Setup

### Prerequisites

- Python 3.9+
- Docker and Docker Compose (for containerized deployment)

### Local Installation

```bash
# Clone the repository
git clone https://github.com/lehdermann/ontomed.git
cd OntoMed

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dashboard dependencies
cd dashboard
pip install -r requirements.txt
cd ..
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Access the dashboard at http://localhost:3000
# API will be available at http://localhost:8000
```

## Usage Examples

### Semantic Module

```python
from ontomed.semantic.service import SemanticService
from ontomed.semantic.factory import ConnectorFactory

# Initialize semantic service with a connector
connector = ConnectorFactory.create_connector("memory")
semantic_service = SemanticService(connector)

# Query a medical concept
concept = semantic_service.get_concept("Hypertension")
print(f"Concept: {concept.label}")

# Get related concepts
related = semantic_service.get_related_concepts("Hypertension")
for relation, concepts in related.items():
    print(f"{relation}: {', '.join([c.label for c in concepts])}")
```

### NLP Module

```python
from ontomed.nlp.processor import NLPProcessor
from ontomed.semantic.service import SemanticService

# Initialize NLP processor with semantic service
semantic_service = SemanticService(connector)
nlp_processor = NLPProcessor(semantic_service)

# Process a natural language query
response = nlp_processor.process_query("O que é hipertensão e como é tratada?")
print(response.content)

# Continue conversation with context
follow_up = nlp_processor.process_query("Quais são os fatores de risco?", response.conversation_id)
print(follow_up.content)
```

### Prompt Module

```python
from ontomed.prompt.template_manager import TemplateManager
from ontomed.prompt.validator import PromptValidator

# Initialize template manager
template_manager = TemplateManager()

# Load and validate a template
template = template_manager.get_template("disease_explanation")
validator = PromptValidator()
validation_result = validator.validate(template)

if validation_result.is_valid:
    # Fill template with data
    filled_template = template_manager.fill_template(
        "disease_explanation",
        {
            "disease": "Hipertensão",
            "definition": "Pressão arterial cronicamente elevada",
            "symptoms": ["Dor de cabeça", "Tontura", "Visão turva"]
        }
    )
    print(filled_template)
```

## Design Principles

OntoMed follows established software design principles and patterns:

- **Separation of Concerns**: Each module has a specific responsibility
- **SOLID Principles**: Single responsibility, Open-closed, Liskov substitution, Interface segregation, Dependency inversion
- **Design Patterns**: Factory, Strategy, Repository, Adapter, Observer, Template Method
- **Error Handling**: Comprehensive exception handling with meaningful error messages
- **Testing**: Unit tests and integration tests for critical components

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- [Paper](docs/paper.md) - Academic paper describing the system architecture and implementation
- [NLP Module](docs/paper_nlp.md) - Detailed documentation of the NLP module
- [API Reference](docs/api_documentation.md) - Complete API endpoint documentation
- [Architecture](docs/architecture.md) - System architecture and design principles
- [User Guide](docs/user_guide.md) - Guide for end users of the system
- [Developer Guide](docs/developer_guide.md) - Guide for developers extending the system
- [Changelog](docs/changelog.md) - Record of changes and improvements

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository at https://github.com/lehdermann/ontomed
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
