# Template Variables in OntoMed

This document describes the variables that can be used in OntoMed templates, explaining their purpose, format, and usage examples.

## Introduction

The OntoMed template system allows the creation of structured prompts for different purposes, such as content generation, concept explanations, and embedding generation. Templates use double curly brace syntax (`{{variable}}`) to insert dynamic values.

## Template Structure

Each template is defined in a YAML file with the following structure:

```yaml
template_id: unique_identifier
name: Template Name
description: Description of what the template does
version: 1.0
type: template_type (text, embedding, structured)
content: |
  Template text with {{variables}}
parameters:
  - name: variable_name
    description: Variable description
    required: true/false
metadata:
  domain: template_domain
  usage: template_usage
  author: template_author
```

## Available Variables

### Concept Variables

These variables are used to represent information about medical concepts:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{concept_name}}` or `{{display_name}}` | Name of the medical concept | "Diabetes Mellitus" |
| `{{id}}` | Unique identifier of the concept | "http://purl.bioontology.org/ontology/SNOMEDCT/73211009" |
| `{{concept_description}}` or `{{description}}` | Detailed description of the concept | "Metabolic disorder characterized by chronic hyperglycemia" |
| `{{concept_type}}` or `{{type}}` | Type or category of the concept | "Disease", "Procedure", "Substance" |
| `{{concept_properties}}` | Additional properties of the concept | "chronic: true, onset: gradual" |

### Relationship Variables

These variables are used to represent relationships between concepts:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{relationships}}` | List of concept relationships | List of relationship objects |
| `{{relationship.type}}` | Type of relationship | "is_a", "part_of", "treats" |
| `{{relationship.target}}` | Target concept of the relationship | "Insulin" |
| `{{relationship.label}}` | Descriptive label of the relationship | "is treated with" |

### Context Variables

These variables provide additional context for the template:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{language}}` | Preferred output language | "pt-BR", "en-US" |
| `{{detail_level}}` | Desired level of detail | "basic", "detailed", "expert" |
| `{{audience}}` | Target audience for the content | "patient", "clinician", "researcher" |

### Nested Object Variables

For concepts represented as complete objects, you can access nested properties:

| Variable | Description | Example |
|----------|-------------|---------|
| `{{concept.label}}` | Name/label of the concept object | "Diabetes Mellitus" |
| `{{concept.id}}` | ID of the concept object | "http://purl.bioontology.org/ontology/SNOMEDCT/73211009" |
| `{{concept.type}}` | Type of the concept object | "Disease" |
| `{{concept.description}}` | Description of the concept object | "Metabolic disorder..." |
| `{{concept.relationships}}` | Relationships of the concept object | List of relationships |
| `{{concept.annotations}}` | Annotations of the concept object | List of annotations |

## Usage Examples

### Concept Embedding Template

```yaml
template_id: concept_embedding
name: Concept Embedding Template
description: Template for generating embeddings for medical concepts
version: 1.0
type: embedding
content: |
  Concept: {{concept_name}}
  Description: {{concept_description}}
  Type: {{concept_type}}
  Properties: {{concept_properties}}
```

### Concept Explanation Template

```yaml
template_id: concept_explanation
name: Concept Explanation
description: Template for generating detailed explanations of medical concepts
version: 1.0
type: text
content: |
  You are a medical and medical ontologies expert.
  
  Please provide a detailed and educational explanation about the following medical concept:
  
  Concept: {{display_name}}
  ID: {{id}}
  Type: {{type}}
  Description: {{description}}
  
  Your explanation should include:
  
  1. A clear definition of the concept in accessible language
  2. The medical context in which this concept is relevant
  3. How this concept relates to other medical concepts
  4. Its importance in clinical practice
  5. Concrete examples of its application
```

## Best Practices

1. **Always define parameters**: Document all parameters your template expects to receive.
2. **Use default values**: When possible, provide default values for optional parameters.
3. **Check types**: Ensure that expected data types are clearly documented.
4. **Test your templates**: Verify that your template works with different variable values.
5. **Maintain consistency**: Use consistent variable names across all your templates.

## Variable Extension

The OntoMed template system is extensible. New variables can be added as needed, as long as they are properly documented and implemented in the code that processes the templates.

To add new variables, update this document and ensure the template processor can provide the corresponding values.
