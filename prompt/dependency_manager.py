from typing import Dict, List, Any
from llm.interface import LLMInterface
from prompt.template_manager import TemplateManager

class DependencyManager:
    """Template dependency manager."""
    
    def __init__(self, llm: LLMInterface):
        """Initialize the dependency manager.
        
        Args:
            llm: LLM interface for dependency analysis
        """
        self.llm = llm
        self.template_manager = TemplateManager(llm)
    
    def analyze_dependencies(self, template: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes template dependencies.
        
        Args:
            template: Template to be analyzed
            
        Returns:
            Dependency analysis
        """
        # Prepare prompt for dependency analysis
        prompt = f"""
        Please analyze the dependencies of this template:
        
        Name: {template['name']}
        Type: {template['type']}
        Category: {template.get('category', '')}
        
        Content:
        {template['content']}
        
        Variables: {template['variables']}
        
        Analysis:
        1. Templates this one depends on
        2. Templates that depend on this one
        3. Compatibility with other templates
        4. Potential conflicts
        
        Respond in JSON format:
        {{
            "dependencies": ["templates this depends on"],
            "dependents": ["templates that depend on this"],
            "compatibility": ["compatible templates"],
            "conflicts": ["potential conflicts"]
        }}
        """
        
        # Generate analysis using LLM
        analysis = self.llm.generate_structured(prompt)
        return analysis
    
    def find_related_templates(self, template: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Finds related templates.
        
        Args:
            template: Reference template
            
        Returns:
            List of related templates
        """
        # Prepare prompt to find related templates
        prompt = f"""
        Please find templates related to this template:
        
        Name: {template['name']}
        Type: {template['type']}
        Category: {template.get('category', '')}
        
        Content:
        {template['content']}
        
        Variables: {template['variables']}
        
        Consider:
        1. Templates with similar purposes
        2. Templates that can be used together
        3. Templates that complement this one
        
        Respond in JSON format:
        {{
            "related_templates": [
                {{
                    "name": "Template Name",
                    "type": "Type",
                    "category": "Category",
                    "relationship": "Relationship Type"
                }}
            ]
        }}
        """
        
        # Generate analysis using LLM
        related = self.llm.generate_structured(prompt)
        return related["related_templates"]
    
    def visualize_dependencies(self, template_id: str) -> Dict[str, Any]:
        """Visualizes template dependencies.
        
        Args:
            template_id: Template ID
            
        Returns:
            Structure for dependency visualization
        """
        # Get template
        template = self.template_manager.get_template(template_id)
        
        # Analyze dependencies
        dependencies = self.analyze_dependencies(template)
        
        # Find related templates
        related_templates = self.find_related_templates(template)
        
        # Prepare visualization structure
        visualization = {
            "nodes": [
                {
                    "id": template_id,
                    "name": template["name"],
                    "type": template["type"],
                    "category": template.get("category", ""),
                    "status": template.get("status", "")
                }
            ],
            "edges": [],
            "related": []
        }
        
        # Add dependencies
        for dep in dependencies["dependencies"]:
            visualization["nodes"].append({
                "id": dep["id"],
                "name": dep["name"],
                "type": dep["type"],
                "category": dep["category"],
                "status": dep["status"]
            })
            visualization["edges"].append({
                "source": template_id,
                "target": dep["id"],
                "type": "dependency",
                "label": "Depends on"
            })
        
        # Add dependent templates
        for dep in dependencies["dependents"]:
            visualization["nodes"].append({
                "id": dep["id"],
                "name": dep["name"],
                "type": dep["type"],
                "category": dep["category"],
                "status": dep["status"]
            })
            visualization["edges"].append({
                "source": dep["id"],
                "target": template_id,
                "type": "dependent",
                "label": "Is required by"
            })
        
        # Add related templates
        for rel in related_templates:
            visualization["related"].append({
                "id": rel["id"],
                "name": rel["name"],
                "type": rel["type"],
                "category": rel["category"],
                "relationship": rel["relationship"]
            })
        
        return visualization
    
    def check_conflicts(self, template1: Dict[str, Any], template2: Dict[str, Any]) -> List[str]:
        """Checks for conflicts between two templates.
        
        Args:
            template1: First template
            template2: Second template
            
        Returns:
            List of found conflicts
        """
        # Prepare prompt to check for conflicts
        prompt = f"""
        Please check for potential conflicts between these two templates:
        
        Template 1 - {template1['name']}:
        Type: {template1['type']}
        Category: {template1.get('category', '')}
        
        Content:
        {template1['content']}
        
        Variables: {template1['variables']}
        
        Template 2 - {template2['name']}:
        Type: {template2['type']}
        Category: {template2.get('category', '')}
        
        Content:
        {template2['content']}
        
        Variables: {template2['variables']}
        
        Check for:
        1. Variable conflicts
        2. Purpose conflicts
        3. Structure conflicts
        4. Content conflicts
        
        Respond in JSON format:
        {{
            "conflicts": ["list of conflicts found"]
        }}
        """
        
        # Generate analysis using LLM
        conflicts = self.llm.generate_structured(prompt)
        return conflicts["conflicts"]
