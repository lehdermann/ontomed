from typing import Dict, Any, List
from llm.interface import LLMInterface
from prompt.template_manager import TemplateManager

class EditorManager:
    """Template editor manager."""
    
    def __init__(self, llm: LLMInterface, template_manager: TemplateManager):
        """Initialize the editor manager.
        
        Args:
            llm: LLM interface for editing assistance
            template_manager: Template manager
        """
        self.llm = llm
        self.template_manager = template_manager
    
    def analyze_template(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes an existing template.
        
        Args:
            template: Template to be analyzed
            
        Returns:
            Template analysis
        """
        # Prepare prompt for analysis
        prompt = f"""
        Please analyze the following template:
        
        Name: {template['name']}
        Type: {template['type']}
        Category: {template.get('category', '')}
        
        Content:
        {template['content']}
        
        Variables: {template['variables']}
        
        Provide a detailed analysis including:
        1. Template strengths
        2. Areas for improvement
        3. Optimization suggestions
        4. Compatibility with other templates
        
        Respond in JSON format:
        {{
            "strengths": ["strengths"],
            "improvements": ["areas for improvement"],
            "optimizations": ["optimization suggestions"],
            "compatibility": ["compatible templates"]
        }}
        """
        
        # Generate analysis using LLM
        analysis = self.llm.generate_structured(prompt)
        return analysis
    
    def suggest_improvements(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Suggests improvements for a template.
        
        Args:
            template: Template to be improved
            
        Returns:
            Improvement suggestions
        """
        # Prepare prompt for suggestions
        prompt = f"""
        Please suggest improvements for the following template:
        
        Name: {template['name']}
        Type: {template['type']}
        Category: {template.get('category', '')}
        
        Content:
        {template['content']}
        
        Variables: {template['variables']}
        
        Suggest:
        1. Content improvements
        2. Addition of relevant variables
        3. Structure optimization
        4. Description improvements
        
        Respond in JSON format:
        {{
            "content_improvements": ["content improvements"],
            "variables": ["suggested variables"],
            "structure": ["structure optimizations"],
            "description": ["description improvements"]
        }}
        """
        
        # Generate suggestions using LLM
        suggestions = self.llm.generate_structured(prompt)
        return suggestions
    
    def validate_changes(self, original: Dict[str, Any], updated: Dict[str, Any]) -> List[str]:
        """Validates changes to a template.
        
        Args:
            original: Original template
            updated: Updated template
            
        Returns:
            List of found errors
        """
        errors = []
        
        # Validate type
        if original["type"] != updated["type"]:
            errors.append("The template type cannot be changed")
            
        # Validate variables
        if len(updated["variables"]) < len(original["variables"]):
            errors.append("Cannot remove existing variables")
            
        # Validate content
        if not updated["content"]:
            errors.append("Template content cannot be empty")
            
        # Validate name
        if not updated["name"]:
            errors.append("Template name cannot be empty")
            
        return errors
    
    def update_template(self, template_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Updates an existing template.
        
        Args:
            template_id: Template ID
            updated_data: Updated template data
            
        Returns:
            Updated template
        """
        # Get original template
        original = self.template_manager.get_template(template_id)
        
        # Validate changes
        errors = self.validate_changes(original, updated_data)
        if errors:
            raise ValueError("\n".join(errors))
            
        # Update template
        return self.template_manager.update_template(template_id, updated_data)
    
    def delete_template(self, template_id: str) -> None:
        """Deletes a template.
        
        Args:
            template_id: Template ID
        """
        # Check dependencies before deleting
        template = self.template_manager.get_template(template_id)
        
        # Prepare prompt to check dependencies
        prompt = f"""
        Please analyze if this template has dependencies that need to be considered before deletion:
        
        Name: {template['name']}
        Type: {template['type']}
        Category: {template.get('category', '')}
        
        Content:
        {template['content']}
        
        Variables: {template['variables']}
        
        Respond in JSON format:
        {{
            "dependencies": ["found dependencies"],
            "warnings": ["important warnings"]
        }}
        """
        
        # Generate dependency analysis using LLM
        dependencies = self.llm.generate_structured(prompt)
        
        # If there are dependencies, raise a warning
        if dependencies.get("dependencies"):
            warnings = dependencies.get("warnings", [])
            if warnings:
                raise Warning("\n".join(warnings))
                
        # Delete template
        self.template_manager.delete_template(template_id)
