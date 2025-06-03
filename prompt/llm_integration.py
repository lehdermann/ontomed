from typing import Dict, Any, List
from llm.interface import LLMInterface
from prompt.manager import PromptManager

class LLMPromptManager(PromptManager):
    """Extension of PromptManager that integrates with LLM."""
    
    def __init__(self, llm: LLMInterface):
        """Initialize the LLM prompt manager.
        
        Args:
            llm: The LLM interface to use for generation
        """
        super().__init__()
        self.llm = llm
    
    def fill_and_generate(self, template_name: str, parameters: Dict[str, Any]) -> str:
        """Fill template with parameters and generate content using LLM.
        
        Args:
            template_name: Name of the template to use
            parameters: Dictionary of parameters to fill in the template
            
        Returns:
            Generated content
        """
        # Get the template
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Fill the template
        filled_template = self.fill_template(template, parameters)
        
        # Generate content using LLM
        return self.llm.generate_text(filled_template)
    
    def generate_structured(self, template_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate structured content using LLM.
        
        Args:
            template_name: Name of the template to use
            parameters: Dictionary of parameters to fill in the template
            
        Returns:
            Dictionary containing the structured response
        """
        # Get the template
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Fill the template
        filled_template = self.fill_template(template, parameters)
        
        # Generate structured response using LLM
        return self.llm.generate_structured(filled_template)
    
    def get_embedding(self, template_content: str, parameters: Dict[str, Any]) -> List[float]:
        """Get embedding for template content.
        
        Args:
            template_content: Content of the template to use
            parameters: Dictionary of parameters to fill in the template
            
        Returns:
            List of floats representing the embedding
        """
        try:
            import logging
            logger = logging.getLogger(__name__)
            
            # Manually replace variables in the template
            filled_template = template_content
            for key, value in parameters.items():
                placeholder = "{{" + key + "}}"
                if placeholder in filled_template:
                    # Convert value to string if not None
                    str_value = str(value) if value is not None else ""
                    filled_template = filled_template.replace(placeholder, str_value)
                    logger.info(f"Replaced {placeholder} with {str_value[:30]}...")
            
            # Check for any remaining placeholders
            import re
            placeholders = re.findall(r'\{\{(\w+)\}\}', filled_template)
            if placeholders:
                logger.warning(f"Unreplaced placeholders: {placeholders}")
            
            # Generate embedding using LLM
            logger.info(f"Generating embedding for text: {filled_template[:100]}...")
            return self.llm.generate_embeddings(filled_template)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating embedding: {str(e)}")
            return []
