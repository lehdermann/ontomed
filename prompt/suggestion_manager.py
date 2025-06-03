from typing import Dict, List, Any
from llm.interface import LLMInterface
from prompt.template_manager import TemplateManager

class SuggestionManager:
    """Gerenciador de sugestões de templates."""
    
    def __init__(self, llm: LLMInterface):
        """Inicializa o gerenciador de sugestões.
        
        Args:
            llm: Interface do LLM para geração
        """
        self.llm = llm
        self.template_manager = TemplateManager(llm)
    
    def suggest_template(self, concept: Dict[str, Any], template_type: str) -> Dict[str, Any]:
        """Sugere um template baseado em um conceito.
        
        Args:
            concept: Dicionário com informações do conceito
            template_type: Tipo de template desejado
            
        Returns:
            Sugestão de template
        """
        # Preparar prompt para sugestão
        prompt = f"""
        Por favor, sugira um template do tipo {template_type} para o conceito: {concept['name']}.
        
        O template deve incluir:
        - Variáveis relevantes para o conceito
        - Estrutura adequada para o tipo de conteúdo
        - Descrição clara do propósito
        - Exemplo de uso
        
        Responda no formato JSON:
        {{
            "name": "Nome do Template",
            "type": "{template_type}",
            "content": "Conteúdo do template",
            "variables": ["lista", "de", "variáveis"],
            "description": "Descrição do template",
            "example": "Exemplo de uso"
        }}
        """
        
        # Gerar sugestão usando LLM
        suggestion = self.llm.generate_structured(prompt)
        
        # Validar e formatar a sugestão
        return self._format_suggestion(suggestion)
    
    def suggest_category(self, concept: Dict[str, Any]) -> Dict[str, Any]:
        """Sugere uma categoria de template baseada em um conceito.
        
        Args:
            concept: Dicionário com informações do conceito
            
        Returns:
            Sugestão de categoria
        """
        # Preparar prompt para sugestão de categoria
        prompt = f"""
        Por favor, sugira uma categoria de template adequada para o conceito: {concept['name']}.
        
        Considere as seguintes categorias:
        - Explicação
        - Descrição
        - Sumário
        - Exemplo
        - Estruturado
        - Embedding
        
        Responda no formato JSON:
        {{
            "category": "Nome da Categoria",
            "reason": "Justificativa para a escolha"
        }}
        """
        
        # Gerar sugestão usando LLM
        suggestion = self.llm.generate_structured(prompt)
        
        return suggestion
    
    def suggest_variables(self, concept: Dict[str, Any], template_type: str) -> List[str]:
        """Sugere variáveis relevantes para um template.
        
        Args:
            concept: Dicionário com informações do conceito
            template_type: Tipo de template
            
        Returns:
            Lista de variáveis sugeridas
        """
        # Preparar prompt para sugestão de variáveis
        prompt = f"""
        Por favor, sugira variáveis relevantes para um template do tipo {template_type} sobre o conceito: {concept['name']}.
        
        Considere as seguintes características do conceito:
        - Tipo: {concept.get('type', '')}
        - Descrição: {concept.get('description', '')}
        - Propriedades: {concept.get('properties', {})}
        
        Liste as variáveis no formato:
        - variavel1
        - variavel2
        - variavel3
        """
        
        # Gerar sugestão usando LLM
        suggestion = self.llm.generate_text(prompt)
        
        # Extrair variáveis da sugestão
        return [v.strip() for v in suggestion.split("\n") if v.strip()]
    
    def _format_suggestion(self, suggestion: Dict[str, Any]) -> Dict[str, Any]:
        """Formata uma sugestão de template.
        
        Args:
            suggestion: Sugestão de template
            
        Returns:
            Template formatado
        """
        # Garantir que todos os campos obrigatórios existam
        required_fields = ["name", "type", "content", "variables", "description"]
        for field in required_fields:
            if field not in suggestion:
                suggestion[field] = ""
        
        # Formatar variáveis como lista
        if isinstance(suggestion["variables"], str):
            suggestion["variables"] = [v.strip() for v in suggestion["variables"].split("\n") if v.strip()]
        
        return suggestion
