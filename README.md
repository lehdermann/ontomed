# OntoMed

**Bridging Medical Knowledge with Semantic Intelligence**

## Overview

OntoMed is a modular framework for managing medical knowledge using semantic technologies and structured prompt management. It demonstrates object-oriented programming principles and best practices in software design.

## Novidades e Melhorias

### Maio 2025

- ✅ Correção do sistema de carregamento de templates
- ✅ Melhorias na interface do dashboard (Visualizer, Generator, Concepts)
- ✅ Correção do endpoint de relacionamentos na API
- ✅ Suporte aprimorado para ambientes Docker
- ✅ Documentação atualizada e expandida

Consulte o [changelog completo](docs/changelog.md) para mais detalhes.

## Key Components

1. **Semantic Module** - Graph database connectors and services for storing and querying medical knowledge
   - Consultas SPARQL robustas com tratamento de erros
   - Múltiplos fallbacks para garantir a disponibilidade dos dados
   - Tratamento especial para URIs e IDs complexos

2. **Prompt Module** - Comprehensive management of templates, including editing, exporting, and validation for generating consistent AI-driven medical content. Key components include:
   - `TemplateManager` for managing templates with automatic loading from filesystem
   - `EditorManager` for editing and analyzing templates
   - `ExportManager` for exporting and importing templates
   - `CategoryManager` for managing template categories
   - `SuggestionManager` for providing template suggestions
   - `DependencyManager` for handling template dependencies
   - `PromptValidator` for validating templates

3. **Dashboard** - Interactive web interface for exploring and managing medical concepts
   - Visualização de conceitos e relacionamentos
   - Geração de conteúdo baseado em templates
   - Interface limpa e profissional

4. **Core Module** - Shared utilities and interfaces

## Installation and Setup

Ensure all dependencies are installed and the environment is correctly set up. Follow these steps:

```bash
# Clone the repository
git clone https://github.com/yourusername/OntoMed.git

# Install dependencies
pip install -r requirements.txt
```

## Usage Examples

### Managing Templates

```python
from prompt.template_manager import TemplateManager
from prompt.editor_manager import EditorManager
from prompt.export_manager import ExportManager

# Initialize managers
llm = LLMFactory.create_llm()
template_manager = TemplateManager(llm)
editor_manager = EditorManager(llm, template_manager)
export_manager = ExportManager(llm, template_manager)

# Edit a template
analysis = editor_manager.analyze_template({
    "name": "Sample Template",
    "type": "Text",
    "content": "This is a sample content.",
    "variables": {}
})

# Export a template
exported_template = export_manager.export_template("template_id")
print(exported_template)
```

```python
from medknowbridge.semantic import GraphDatabaseService
from medknowbridge.prompt import PromptManager

# Initialize services
db_service = GraphDatabaseService()
prompt_manager = PromptManager()

# Connect to database
db_service.connect()

# Query medical concept
hypertension_data = db_service.query_concept("Hypertension")

# Generate explanation using prompt template
explanation = prompt_manager.fill_template(
    "diagnostic_explanation",
    {
        "condition": "Hypertension",
        "medical_concepts": hypertension_data
    }
)

print(explanation)
```

## Design Principles

- **Modularity** - Independent components with well-defined interfaces
- **Extensibility** - Easy addition of new database connectors or templates
- **Robustness** - Comprehensive error handling and validation
- **Maintainability** - Well-documented code structured according to design patterns

## Documentation

A documentação completa do OntoMed está disponível no diretório `docs/`:

- [Arquitetura](docs/architecture.md) - Visão geral da arquitetura e princípios de design
- [API](docs/api_documentation.md) - Documentação da API REST
- [Detalhes de Implementação](docs/implementation_details.md) - Detalhes técnicos das implementações recentes
- [Melhorias no Dashboard](docs/dashboard_improvements.md) - Descrição das melhorias na interface do usuário
- [Changelog](docs/changelog.md) - Registro de alterações e melhorias

## License

MIT License
