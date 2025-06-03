"""
Script para inicializar os templates do sistema.
Este script carrega os templates do diretório templates/ e os registra no PromptManager.
"""

import os
import yaml
import logging
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_template_file(filepath: str) -> Dict[str, Any]:
    """
    Carrega um arquivo de template.
    
    Args:
        filepath: Caminho para o arquivo de template
        
    Returns:
        Dicionário com o conteúdo do template
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            if filepath.endswith('.yaml') or filepath.endswith('.yml'):
                return yaml.safe_load(f)
            else:
                logger.warning(f"Formato de arquivo não suportado: {filepath}")
                return {}
    except Exception as e:
        logger.error(f"Erro ao carregar template {filepath}: {e}")
        return {}

def register_concept_embedding_template() -> None:
    """
    Registra o template concept_embedding no PromptManager.
    """
    # Importar aqui para evitar problemas de importação circular
    from prompt.manager import PromptManager
    
    # Obter a instância do PromptManager (singleton)
    manager = PromptManager()
    
    # Caminho para o diretório de templates
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    
    # Caminho para o arquivo de template
    template_path = os.path.join(templates_dir, 'concept_embedding.yaml')
    
    # Verificar se o arquivo existe
    if not os.path.exists(template_path):
        logger.error(f"Template não encontrado: {template_path}")
        
        # Criar o template se não existir
        os.makedirs(os.path.dirname(template_path), exist_ok=True)
        
        template_data = {
            'template_id': 'concept_embedding',
            'name': 'Concept Embedding Template',
            'description': 'Template for generating embeddings for medical concepts',
            'version': '1.0',
            'type': 'embedding',
            'template': 'Conceito: {{concept_name}}\nDescrição: {{concept_description}}\nTipo: {{concept_type}}\nPropriedades: {{concept_properties}}',
            'parameters': [
                {'name': 'concept_name', 'description': 'Nome do conceito médico', 'required': True},
                {'name': 'concept_description', 'description': 'Descrição do conceito', 'required': False},
                {'name': 'concept_type', 'description': 'Tipo ou categoria do conceito', 'required': False},
                {'name': 'concept_properties', 'description': 'Propriedades adicionais do conceito', 'required': False}
            ],
            'metadata': {
                'domain': 'medical',
                'usage': 'embedding',
                'author': 'OntoMed'
            }
        }
        
        # Salvar o template
        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"Template criado: {template_path}")
        except Exception as e:
            logger.error(f"Erro ao criar template: {e}")
            return
    
    # Carregar o template
    template_data = load_template_file(template_path)
    if not template_data:
        logger.error(f"Falha ao carregar template: {template_path}")
        return
    
    # Registrar o template
    try:
        # Adicionar diretamente ao dicionário de templates
        template_id = template_data.get('template_id')
        if template_id:
            manager.templates[template_id] = template_data
            logger.info(f"Template registrado: {template_id}")
        else:
            logger.error(f"Template sem ID: {template_path}")
    except Exception as e:
        logger.error(f"Erro ao registrar template: {e}")

def initialize():
    """
    Inicializa os templates do sistema.
    """
    # Registrar o template concept_embedding
    register_concept_embedding_template()
    
    logger.info("Templates inicializados com sucesso")

# Executar a inicialização se o script for executado diretamente
if __name__ == "__main__":
    initialize()
