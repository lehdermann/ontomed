#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Semantic endpoints for the OntoMed API.
Provides REST endpoints for interacting with the semantic module.
"""

import os
import sys
from fastapi import APIRouter, HTTPException, Depends, UploadFile
from typing import List, Dict, Any
from rdflib import Graph

# Add the current directory to the path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from semantic.factory import GraphDatabaseFactory
from semantic.service import GraphDatabaseService
from semantic.memory_connector import MemoryConnector

from models import Concept, ConceptCreate, ConceptQuery, SuccessResponse, ErrorResponse, ConceptRelationship

# Create router
router = APIRouter(
    prefix="/api",
    tags=["semantic"],
    responses={404: {"model": ErrorResponse}}
)

# Dependency to get database service
def get_db_service():
    """
    Dependency to get a database service instance.
    
    Returns:
        GraphDatabaseService: Database service instance
    """
    # Create factory and get the default Blazegraph connector
    factory = GraphDatabaseFactory()
    default_connector = factory.default_connector
    
    # Initialize service with Blazegraph connector
    service = GraphDatabaseService(
        connector_type="blazegraph",
        base_url=default_connector.base_url,
        namespace=default_connector.namespace
    )
    
    # Connect to the database
    if not service.connect():
        raise HTTPException(status_code=500, detail="Failed to connect to graph database")
        
    return service

@router.get("/statistics", response_model=Dict[str, int])
async def get_graph_statistics(db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Retrieves statistics about the graph database.
    
    Args:
        db_service: Database service instance
        
    Returns:
        Dict[str, int]: Dictionary with graph statistics
    """
    try:
        return db_service.get_graph_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting graph statistics: {str(e)}")

@router.post("/clear", response_model=SuccessResponse)
async def clear_database(service: GraphDatabaseService = Depends(get_db_service)):
    """
    Clears all data from the graph database.
    
    Returns:
        SuccessResponse: Response indicating success or failure
    """
    try:
        success = service.connector.clear_database()
        if success:
            return SuccessResponse(message="Database cleared successfully")
        else:
            raise HTTPException(status_code=500, detail="Failed to clear database")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/concepts", response_model=List[Concept])
async def get_concepts(service: GraphDatabaseService = Depends(get_db_service)):
    """
    Get all concepts from the semantic database.
    
    Args:
        service: Database service instance
        
    Returns:
        List[Concept]: List of concepts
    """
    try:
        # Get concepts using the service
        concepts = service.get_concepts()
        return concepts
    except Exception as e:
        logger.error(f"Error getting concepts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/concepts/", response_model=SuccessResponse, status_code=201)
async def create_concept(concept: ConceptCreate, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Create a new concept in the semantic database.
    
    Args:
        concept: Concept to create
        db_service: Database service instance
        
    Returns:
        SuccessResponse: Success message
    """
    try:
        # Convert from API model to internal format
        concept_data = {
            "id": concept.id,
            "label": concept.label,
            "relationships": [
                {
                    "type": rel.type,
                    "target": rel.target,
                    "label": rel.label
                }
                for rel in concept.relationships
            ]
        }
        
        # Store the concept
        success = db_service.store_concept(concept.id, concept_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store concept")
        
        return SuccessResponse(
            message=f"Concept {concept.id} created successfully",
            data={"concept_id": concept.id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating concept: {str(e)}")

@router.get("/concepts/")
async def list_concepts(db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    List all concepts in the semantic database.
    
    Args:
        db_service: Database service instance
        
    Returns:
        List[Dict]: List of concepts
    """
    try:
        concepts = db_service.list_concepts()
        return concepts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing concepts: {str(e)}")
    """
    Create a new concept in the semantic database.
    
    Args:
        concept: Concept to create
        db_service: Database service instance
        
    Returns:
        SuccessResponse: Success message
    """
    try:
        # Convert from API model to internal format
        concept_data = {
            "id": concept.id,
            "label": concept.label,
            "relationships": [
                {
                    "type": rel.type,
                    "target": rel.target,
                    "label": rel.label
                }
                for rel in concept.relationships
            ]
        }
        
        # Store the concept
        success = db_service.store_concept(concept.id, concept_data)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store concept")
        
        return SuccessResponse(
            message=f"Concept {concept.id} created successfully",
            data={"concept_id": concept.id}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating concept: {str(e)}")

@router.post("/ontologies/upload", summary="Upload and load ontology")
async def upload_ontology(file: UploadFile, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Upload and load an ontology into the semantic database.

    Args:
        file: Ontology file to upload
        db_service: Database service instance

    Returns:
        SuccessResponse: Success message
    """
    try:
        # Read the file content
        content = await file.read()
        file_extension = file.filename.split('.')[-1].lower()
        
        # Log file details
        print(f"Uploading ontology file: {file.filename}, size: {len(content)} bytes, extension: {file_extension}")
        
        # Map file extensions to RDF formats
        format_map = {
            'ttl': 'turtle',
            'jsonld': 'json-ld',
            'rdf': 'xml',
            'owl': 'xml',
            'xml': 'xml'
        }
        
        # Get the appropriate format, default to 'turtle' if unknown
        rdf_format = format_map.get(file_extension, 'turtle')
        print(f"Using RDF format: {rdf_format}")
        
        # Parse the ontology
        g = Graph()
        g.parse(data=content, format=rdf_format)
        print(f"Successfully parsed the ontology. Number of triples: {len(g)}")
        
        # Ensure the connector is connected
        if not db_service.connector.is_connected():
            if not db_service.connector.connect():
                raise HTTPException(status_code=500, detail="Failed to connect to graph database")
        
        # Import the graph into the database
        success = db_service.import_rdflib_graph(g)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to import ontology into the database")
            
        return SuccessResponse(message="Ontology uploaded and loaded successfully")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error uploading ontology: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error uploading ontology: {str(e)}")


@router.get("/ontology/triples", summary="List all triples in the ontology")
async def list_ontology_triples(
    limit: int = 100,
    db_service: GraphDatabaseService = Depends(get_db_service)
):
    """
    Lista todas as triplas da ontologia carregada.
    
    Args:
        limit: Número máximo de triplas a retornar
        db_service: Serviço de banco de dados
        
    Returns:
        Lista de triplas no formato (sujeito, predicado, objeto)
    """
    try:
        # Obter estatísticas para o total de triplas
        stats = db_service.get_graph_statistics()
        total_concepts = stats.get("total_concepts", 0)
        total_relationships = stats.get("total_relationships", 0)
        
        return {
            "triples": [],
            "total_triples": total_concepts + total_relationships,
            "message": "Endpoint simplificado. Use /api/concepts para obter informações sobre os conceitos."
        }
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"Error retrieving ontology triples: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving ontology triples: {str(e)}")


@router.get("/concepts", response_model=List[Concept], summary="List all concepts")
async def list_concepts(
    db_service: GraphDatabaseService = Depends(get_db_service)
):
    """
    Lista todos os conceitos cadastrados (ou aplique filtros via query params).
    """
    try:
        # Vamos supor que o serviço tenha um método para listar tudo
        all_data = db_service.list_concepts()
        return [ Concept(**d) for d in all_data ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concepts/{concept_id:path}", response_model=Concept)
async def get_concept(concept_id: str, 
                     relationship_type: str = None, 
                     db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Get a concept from the semantic database.
    
    Args:
        concept_id: ID of the concept to get
        relationship_type: Optional type of relationships to filter by
        db_service: Database service instance
        
    Returns:
        Concept: The requested concept
    """
    try:
        print(f"DEBUG - Buscando conceito com ID: {concept_id}")
        
        # Primeiro, tente obter o conceito diretamente
        concept_data = db_service.query_concept(concept_id, relationship_type)
        
        # Se não encontrar, tente buscar na lista completa de conceitos
        if not concept_data:
            print(f"DEBUG - Conceito não encontrado via query_concept, tentando buscar na lista completa")
            all_concepts = db_service.get_concepts()
            
            for concept in all_concepts:
                if concept.get("id") == concept_id:
                    concept_data = {
                        "id": concept.get("id"),
                        "label": concept.get("label"),
                        "relationships": concept.get("relationships", [])
                    }
                    break
        
        if not concept_data:
            raise HTTPException(status_code=404, detail=f"Concept {concept_id} not found")
        
        # Convert to API model
        relationships = []
        for rel in concept_data.get("relationships", []):
            relationships.append(ConceptRelationship(
                type=rel.get("type", ""),
                target=rel.get("target", ""),
                label=rel.get("label", "")
            ))
        
        return Concept(
            id=concept_data.get("id", concept_id),
            label=concept_data.get("label", ""),
            relationships=relationships
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving concept: {str(e)}")

@router.post("/concepts/query/", response_model=Concept)
async def query_concept(query: ConceptQuery, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Query a concept from the semantic database.
    
    Args:
        query: Query parameters
        db_service: Database service instance
        
    Returns:
        Concept: The requested concept
    """
    try:
        # Query the concept
        concept_data = db_service.query_concept(query.concept_id, query.relationship_type)
        
        if not concept_data:
            raise HTTPException(status_code=404, detail=f"Concept {query.concept_id} not found")
        
        # Convert to API model
        relationships = []
        for rel in concept_data.get("relationships", []):
            relationships.append(ConceptRelationship(
                type=rel.get("type", ""),
                target=rel.get("target", ""),
                label=rel.get("label", "")
            ))
        
        return Concept(
            id=concept_data.get("id", query.concept_id),
            label=concept_data.get("label", ""),
            relationships=relationships
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying concept: {str(e)}")


# Endpoint separado para relacionamentos que não usa o path parameter para evitar conflitos
@router.get("/concepts/{concept_id}/relationships", response_model=dict)
async def get_concept_relationships_v2(concept_id: str, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Get relationships for a specific concept (versão 2).
    
    Args:
        concept_id: ID of the concept
        db_service: Database service instance
        
    Returns:
        Dict: Dictionary with concept ID, label and relationships
    """
    try:
        # Obter o conceito completo
        concept_data = await get_concept(concept_id, None, db_service)
        
        if not concept_data or not isinstance(concept_data, dict):
            return {"id": concept_id, "label": "", "relationships": []}
        
        # Extrair relacionamentos relevantes
        relationships = []
        if "relationships" in concept_data:
            for rel in concept_data["relationships"]:
                rel_type = rel.get("type", "")
                if rel_type in ["disjointWith", "subClassOf", "equivalentClass", "comment", "label"]:
                    relationships.append(rel)
        
        return {
            "id": concept_id,
            "label": concept_data.get("label", ""),
            "relationships": relationships
        }
        
    except Exception as e:
        print(f"Erro ao processar relacionamentos (v2): {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing relationships: {str(e)}")


@router.get("/concepts/relationships/{concept_id}", response_model=dict)
async def get_concept_relationships(concept_id: str, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Get relationships for a specific concept.
    
    Args:
        concept_id: ID of the concept
        db_service: Database service instance
        
    Returns:
        Dict: Dictionary with concept ID, label and relationships
    """
    try:
        # Remover o prefixo "relationships/" se existir
        original_id = concept_id
        if concept_id.startswith("relationships/"):
            concept_id = concept_id[len("relationships/"):]
        
        print(f"Buscando relacionamentos para o conceito: {concept_id} (ID original: {original_id})")
        
        # Obter o conceito completo
        concept_data = await get_concept(concept_id, None, db_service)
        
        # Se não conseguiu obter o conceito, retornar objeto vazio
        if not concept_data:
            print(f"Nenhum dado encontrado para o conceito: {concept_id}")
            return {"id": f"relationships/{concept_id}", "label": "", "relationships": []}
        
        # Verificar se o conceito tem relacionamentos
        if not isinstance(concept_data, dict):
            print(f"Formato inesperado para o conceito: {type(concept_data)}")
            return {"id": f"relationships/{concept_id}", "label": "", "relationships": []}
        
        # Se não houver relacionamentos, retornar lista vazia
        if "relationships" not in concept_data:
            print(f"Nenhum relacionamento encontrado para o conceito: {concept_id}")
            return {"id": f"relationships/{concept_id}", "label": "", "relationships": []}
        
        # Filtrar os relacionamentos relevantes
        filtered_relationships = []
        for rel in concept_data["relationships"]:
            rel_type = rel.get("type", "")
            
            # Incluir relacionamentos semânticos importantes
            if rel_type in ["disjointWith", "subClassOf", "equivalentClass"]:
                filtered_relationships.append(rel)
            # Incluir comentários (descrições)
            elif rel_type == "comment":
                filtered_relationships.append(rel)
            # Incluir labels (nomes)
            elif rel_type == "label":
                filtered_relationships.append(rel)
        
        # Retornar os relacionamentos filtrados
        # Este é o formato que o cliente API espera
        return {
            "id": f"relationships/{concept_id}",
            "label": concept_data.get("label", ""),
            "relationships": filtered_relationships
        }
        
    except Exception as e:
        print(f"Erro ao processar relacionamentos: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error processing relationships: {str(e)}")

@router.delete("/concepts/{concept_id}", response_model=SuccessResponse)
async def delete_concept(concept_id: str, db_service: GraphDatabaseService = Depends(get_db_service)):
    """
    Delete a concept from the semantic database.

    Args:
        concept_id: ID of the concept to delete
        db_service: Database service instance

    Returns:
        SuccessResponse: Success message
    """
    try:
        # Delete the concept
        success = db_service.delete_concept(concept_id)

        if success:
            return SuccessResponse(message=f"Concept {concept_id} deleted successfully")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to delete concept {concept_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
