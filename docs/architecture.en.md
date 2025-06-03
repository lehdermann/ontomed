# OntoMed: Architecture and Design Principles

## Overview

OntoMed is a modular solution for managing medical knowledge using semantic technologies and structured prompt management. The system demonstrates object-oriented programming principles and software design best practices.

## Architecture

OntoMed's architecture is organized into four main modules:

```
MedKnowBridge/
├── core/                # Shared utilities
├── semantic/            # Semantic database connectors and services
├── prompt/              # Template management and validation
├── api/                 # REST API for system integration
├── examples/            # Usage examples
├── docker/              # Containerization and deployment
└── docs/                # Documentation
```

### Semantic Module

The semantic module implements a layered architecture for interacting with graph databases:

1. **Abstract Interface** (`interface.py`) - Defines the contract that all connectors must follow
2. **Factory** (`factory.py`) - Implements the Factory pattern to create different types of connectors
3. **Service** (`service.py`) - Provides a high-level API for semantic operations
4. **Concrete Implementations** (`memory_connector.py`) - Specific implementations of the interface

### Prompt Module

The prompt module manages templates for generating medical content:

1. **Validator** (`validator.py`) - Ensures templates follow the expected schema
2. **Manager** (`manager.py`) - Loads, validates, and fills templates
3. **Templates** (`templates/`) - YAML definitions of templates for different use cases

### API Module

The API module exposes system functionality through a REST interface:

1. **Main Application** (`main.py`) - FastAPI application with middleware and error handling
2. **Models** (`models.py`) - Pydantic models for request/response validation
3. **Semantic Endpoints** (`semantic.py`) - REST endpoints for the semantic module
4. **Prompt Endpoints** (`prompt.py`) - REST endpoints for the prompt module
5. **Server** (`server.py`) - Uvicorn server configuration and startup

### Docker Module

The Docker module provides containerization and deployment:

1. **Docker Compose** (`docker-compose.yml`) - Service orchestration for API and BlazegraphDB
2. **Dockerfile** (`Dockerfile`) - Container definition for the API service
3. **Initialization Scripts** - Setup for database namespaces and sample data

## Implemented Design Principles

### 1. Design Patterns

- **Factory Pattern** - Implemented in `GraphDatabaseFactory` to create database connectors
- **Singleton Pattern** - Applied in `PromptManager` and `GraphDatabaseFactory` to ensure a single instance
- **Service Pattern** - Implemented in `GraphDatabaseService` to provide a high-level API

### 2. SOLID Principles

- **Single Responsibility Principle (SRP)** - Each class has a single responsibility
- **Open/Closed Principle (OCP)** - Extension via interfaces and abstract classes
- **Liskov Substitution Principle (LSP)** - Concrete implementations can substitute interfaces
- **Interface Segregation Principle (ISP)** - Specific interfaces for different purposes
- **Dependency Inversion Principle (DIP)** - Dependency on abstractions, not concrete implementations

### 3. Programming Best Practices

- **Encapsulation** - Private attributes with appropriate access methods
- **Static Typing** - Use of type hints to improve type safety
- **Exception Handling** - Proper capture and handling of errors
- **Structured Logging** - Informative log messages at different levels
- **Documentation** - Detailed docstrings for classes and methods

## Data Flow

The typical data flow in OntoMed follows this pattern:

1. **Knowledge Storage**:
   - Medical concepts are modeled as entities in a graph
   - Semantic relationships are established between concepts
   - The database service manages persistence

2. **Knowledge Querying**:
   - SPARQL queries are generated to retrieve information
   - Results are transformed into usable data structures
   - Multiple fallbacks are implemented to ensure robustness
   - Special handling for complex URIs and IDs

3. **Content Generation**:
   - Templates are automatically loaded from the filesystem
   - Templates are selected based on the use case
   - Parameters are validated against the template schema
   - The template is filled with data from medical knowledge
   - Support for different template types (text, structured, embedding)

## Extensibility

OntoMed was designed to be easily extensible:

1. **New Database Connectors**:
   - Implement the `GraphDatabaseInterface`
   - Register the new connector with `GraphDatabaseFactory`

2. **New Templates**:
   - Create YAML files following the defined schema
   - Add to the templates directory
   - Templates are automatically detected and loaded

3. **New API Endpoints**:
   - Create new router modules following the existing pattern
   - Register the router with the main FastAPI application

4. **New Use Cases**:
   - Combine existing services in new workflows
   - Extend base classes for specific functionalities

5. **Deployment Options**:
   - Modify Docker configuration for different environments
   - Add new services to the Docker Compose setup
   - Flexible configuration via environment variables
   - Communication between services using Docker service names

## User Interface

OntoMed includes an interactive dashboard with several specialized pages:

1. **Home**: System overview and knowledge graph statistics

2. **Visualizer**: Interactive visualization of concepts and their relationships
   - Graphical display of semantic relationships
   - Clean and professional interface without debug messages
   - Robust handling of different API response formats

3. **Concepts**: Detailed exploration of stored concepts
   - Display of detailed information: name, type, description
   - Visualization of relationships in a separate table
   - Extraction of readable labels from URIs

4. **Generator**: Content generation based on concepts
   - Selection of concepts with consistent display names
   - Support for different template types
   - Visualization of complete data for debugging

## Conclusion

OntoMed demonstrates how object-oriented principles and design best practices can be applied to create a modular, extensible, and robust system for managing medical knowledge and generating AI-based content. The recent improvements have significantly increased the system's robustness, usability, and flexibility.
