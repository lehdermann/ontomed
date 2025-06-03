from typing import Dict, Any, List
import os
import yaml
import logging
import re
from typing import Dict, List, Any, Optional
from llm.interface import LLMInterface
from prompt.llm_integration import LLMPromptManager

logger = logging.getLogger(__name__)

class TemplateManager:
    """Gerenciador de templates para geração de conteúdo."""
    
    def __init__(self, llm: LLMInterface):
        """Inicializa o gerenciador de templates.
        
        Args:
            llm: Interface do LLM para geração
        """
        self.llm = llm
        self.prompt_manager = LLMPromptManager(llm)
        self.templates = []
        self.templates_dir = self._get_templates_dir()
        self._load_templates_from_disk()
    
    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cria um novo template.
        
        Args:
            template_data: Dados do template
            
        Returns:
            Template criado
        """
        # Validar dados do template
        required_fields = ["name", "type", "content", "variables"]
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Campo obrigatório '{field}' não encontrado")
        
        # Criar ID único
        template_id = f"temp_{len(self.templates) + 1}"
        
        # Adicionar template
        template = {
            "id": template_id,
            **template_data
        }
        self.templates.append(template)
        
        return template
    
    def get_template(self, template_id: str) -> Dict[str, Any]:
        """Obtém um template pelo ID.
        
        Args:
            template_id: ID do template
            
        Returns:
            Template encontrado
        """
        template = next((t for t in self.templates if t["id"] == template_id), None)
        if not template:
            raise ValueError(f"Template com ID {template_id} não encontrado")
        return template
    
    def update_template(self, template_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Atualiza um template existente.
        
        Args:
            template_id: ID do template
            updated_data: Dados atualizados
            
        Returns:
            Template atualizado
        """
        # Encontrar template
        template = self.get_template(template_id)
        
        # Atualizar dados
        for key, value in updated_data.items():
            if key != "id":
                template[key] = value
        
        return template
    
    def delete_template(self, template_id: str) -> None:
        """Exclui um template.
        
        Args:
            template_id: ID do template
        """
        # Encontrar e remover template
        self.templates = [t for t in self.templates if t["id"] != template_id]
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Obtém todos os templates.
        
        Returns:
            Lista de templates
        """
        return self.templates
    
    def generate_content(self, template: Dict[str, Any], concept: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> str:
        """Gera conteúdo usando um template específico.
        
        Args:
            template: Template a ser usado
            concept: Dicionário com informações do conceito
            temperature: Controle de aleatoriedade (0.0 a 1.0)
            max_tokens: Número máximo de tokens
            
        Returns:
            Conteúdo gerado
        """
        # Usar todos os parâmetros do conceito diretamente
        # Isso garante que qualquer variável no template possa ser preenchida
        parameters = concept
        
        # Gerar conteúdo usando o template
        # Nota: O LLMPromptManager.fill_and_generate não aceita temperature e max_tokens
        # Vamos preencher o template manualmente e usar diretamente o LLM
        
        # Preencher o template usando uma abordagem mais robusta
        template_content = template["content"]
        try:
            # Verificar se o template tem o formato esperado
            if not template_content:
                raise ValueError("Template vazio")
                
            # Registrar o template original para debug
            logger.info(f"Template original: {template_content[:100]}...")
            
            # Encontrar todas as variáveis no formato {{var}}
            pattern = r'\{\{(\w+)\}\}'
            variables = re.findall(pattern, template_content)
            
            # Registrar as variáveis encontradas
            logger.info(f"Variáveis encontradas no template: {variables}")
            
            # Substituir cada variável pelo seu valor
            for var in variables:
                if var in parameters:
                    value = str(parameters[var]) if parameters[var] is not None else ""
                    placeholder = "{{" + var + "}}"
                    template_content = template_content.replace(placeholder, value)
                    logger.info(f"Substituindo {placeholder} por {value[:50]}...")
                else:
                    logger.warning(f"Variável {var} não encontrada nos parâmetros")
                    # Substituir por um valor vazio ou um placeholder
                    template_content = template_content.replace("{{" + var + "}}", f"[{var} não disponível]")
            
            # Verificar se ainda há variáveis não substituídas
            remaining_vars = re.findall(pattern, template_content)
            if remaining_vars:
                logger.warning(f"Variáveis não substituídas: {remaining_vars}")
                
            # Adicionar instruções de temperatura no prompt, já que não podemos passar como parâmetro
            if temperature > 0.7:
                template_content = f"Instrução: Seja criativo e variável em suas respostas.\n\n{template_content}"
            elif temperature < 0.3:
                template_content = f"Instrução: Seja conciso e direto em suas respostas.\n\n{template_content}"
                
            # Gerar texto usando o LLM (sem parâmetros extras que não são suportados)
            return self.llm.generate_text(template_content)
        except Exception as e:
            logger.error(f"Erro ao preencher template: {str(e)}")
            raise ValueError(f"Erro ao preencher template: {str(e)}")
    
    def generate_structured(self, template: Dict[str, Any], concept: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 500) -> Dict[str, Any]:
        """Gera conteúdo estruturado usando um template.
        
        Args:
            template: Template a ser usado
            concept: Dicionário com informações do conceito
            temperature: Controle de aleatoriedade (0.0 a 1.0)
            max_tokens: Número máximo de tokens
            
        Returns:
            Conteúdo estruturado
        """
        # Usar todos os parâmetros do conceito diretamente
        # Isso garante que qualquer variável no template possa ser preenchida
        parameters = concept
        
        # Gerar conteúdo estruturado usando o template
        # Nota: O LLMPromptManager.fill_and_generate_structured não aceita temperature e max_tokens
        # Vamos preencher o template manualmente e usar diretamente o LLM
        
        # Preencher o template usando uma abordagem mais robusta
        template_content = template["content"]
        try:
            # Verificar se o template tem o formato esperado
            if not template_content:
                raise ValueError("Template vazio")
                
            # Registrar o template original para debug
            logger.info(f"Template original: {template_content[:100]}...")
            
            # Encontrar todas as variáveis no formato {{var}}
            pattern = r'\{\{(\w+)\}\}'
            variables = re.findall(pattern, template_content)
            
            # Registrar as variáveis encontradas
            logger.info(f"Variáveis encontradas no template: {variables}")
            
            # Substituir cada variável pelo seu valor
            for var in variables:
                if var in parameters:
                    value = str(parameters[var]) if parameters[var] is not None else ""
                    placeholder = "{{" + var + "}}"
                    template_content = template_content.replace(placeholder, value)
                    logger.info(f"Substituindo {placeholder} por {value[:50]}...")
                else:
                    logger.warning(f"Variável {var} não encontrada nos parâmetros")
                    # Substituir por um valor vazio ou um placeholder
                    template_content = template_content.replace("{{" + var + "}}", f"[{var} não disponível]")
            
            # Verificar se ainda há variáveis não substituídas
            remaining_vars = re.findall(pattern, template_content)
            if remaining_vars:
                logger.warning(f"Variáveis não substituídas: {remaining_vars}")
                
            # Adicionar instruções de temperatura no prompt, já que não podemos passar como parâmetro
            if temperature > 0.7:
                template_content = f"Instrução: Seja criativo e variável em suas respostas.\n\n{template_content}"
            elif temperature < 0.3:
                template_content = f"Instrução: Seja conciso e direto em suas respostas.\n\n{template_content}"
                
            # Gerar conteúdo estruturado usando o LLM (sem parâmetros extras que não são suportados)
            return self.llm.generate_structured(template_content)
        except Exception as e:
            logger.error(f"Erro ao preencher template estruturado: {str(e)}")
            raise ValueError(f"Erro ao preencher template estruturado: {str(e)}")
    
    def _get_templates_dir(self) -> str:
        """Obtém o diretório de templates.
        
        Returns:
            Caminho para o diretório de templates
        """
        # Diretório base do projeto
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Diretório de templates
        templates_dir = os.path.join(base_dir, "prompt", "templates")
        
        # Verificar se o diretório existe
        if not os.path.exists(templates_dir):
            logger.warning(f"Diretório de templates não encontrado: {templates_dir}")
            os.makedirs(templates_dir, exist_ok=True)
        
        return templates_dir
    
    def _load_templates_from_disk(self) -> None:
        """Carrega templates do sistema de arquivos."""
        if not os.path.exists(self.templates_dir):
            logger.warning(f"Diretório de templates não encontrado: {self.templates_dir}")
            return
        
        # Limpar templates existentes
        self.templates = []
        
        # Listar arquivos YAML no diretório de templates
        for filename in os.listdir(self.templates_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                try:
                    # Caminho completo para o arquivo
                    file_path = os.path.join(self.templates_dir, filename)
                    
                    # Carregar template do arquivo
                    with open(file_path, "r", encoding="utf-8") as f:
                        template_data = yaml.safe_load(f)
                    
                    # Validar dados do template
                    if not template_data or not isinstance(template_data, dict):
                        logger.warning(f"Template inválido: {filename}")
                        continue
                    
                    # Extrair nome do template do arquivo
                    template_name = template_data.get("name", os.path.splitext(filename)[0])
                    
                    # Criar ID único baseado no nome do arquivo
                    template_id = os.path.splitext(filename)[0]
                    
                    # Adicionar template à lista
                    template = {
                        "id": template_id,
                        "name": template_name,
                        "type": template_data.get("type", "text"),
                        "content": template_data.get("template", ""),
                        "variables": [param.get("name") for param in template_data.get("parameters", [])],
                        "description": template_data.get("description", ""),
                        "status": "Ativo",
                        "category": template_data.get("metadata", {}).get("domain", "general")
                    }
                    
                    self.templates.append(template)
                    logger.info(f"Template carregado: {template_name} ({template_id})")
                    
                except Exception as e:
                    logger.error(f"Erro ao carregar template {filename}: {str(e)}")
        
        logger.info(f"Total de templates carregados: {len(self.templates)}")
    
    def get_embedding(self, template_id: str, concept: Dict[str, Any]) -> List[float]:
        """Gera embedding para um conceito usando um template específico.
        
        Args:
            template_id: ID do template
            concept: Dicionário com informações do conceito
            
        Returns:
            Lista de floats representando o embedding
        """
        try:
            # Obter template
            template = self.get_template(template_id)
            
            # Preparar parâmetros baseados no conceito
            parameters = {
                "concept_name": concept.get("name", concept.get("label", "")),
                "concept_description": concept.get("description", ""),
                "concept_type": concept.get("type", ""),
                "concept_properties": concept.get("properties", {})
            }
            
            # Preencher o template
            template_content = template["content"]
            for key, value in parameters.items():
                placeholder = "{{" + key + "}}"
                template_content = template_content.replace(placeholder, str(value))
            
            # Gerar embedding
            return self.llm.generate_embeddings(template_content)
            
        except Exception as e:
            logger.error(f"Erro ao gerar embedding: {str(e)}")
            raise ValueError(f"Erro ao gerar embedding: {str(e)}")
    
    def add_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Adiciona um template à lista.
        
        Args:
            template_data: Dados do template
            
        Returns:
            Template adicionado
        """
        # Validar dados do template
        required_fields = ["name", "type", "content"]
        for field in required_fields:
            if field not in template_data:
                raise ValueError(f"Campo obrigatório '{field}' não encontrado")
        
        # Criar ID único se não existir
        if "id" not in template_data:
            template_data["id"] = f"temp_{len(self.templates) + 1}"
        
        # Adicionar template à lista
        self.templates.append(template_data)
        
        return template_data
