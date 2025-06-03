import json
from typing import Dict, List, Any
from llm.interface import LLMInterface
from prompt.template_manager import TemplateManager

class ExportManager:
    """Template export and import manager."""
    
    def __init__(self, llm: LLMInterface, template_manager: TemplateManager):
        """Initialize the export manager.
        
        Args:
            llm: LLM interface for template analysis
            template_manager: Template manager
        """
        self.llm = llm
        self.template_manager = template_manager
    
    def export_template(self, template_id: str, include_dependencies: bool = True) -> Dict[str, Any]:
        """Exports a template.
        
        Args:
            template_id: Template ID
            include_dependencies: Include dependent templates
            
        Returns:
            Exported template
        """
        # Get template
        template = self.template_manager.get_template(template_id)
        
        # Prepare export structure
        export_data = {
            "template": template,
            "metadata": {
                "version": "1.0",
                "export_date": "2025-05-09",
                "dependencies_included": include_dependencies
            }
        }
        
        # Include dependencies if requested
        if include_dependencies:
            dependencies = self._get_dependencies(template_id)
            export_data["dependencies"] = dependencies
        
        return export_data
    
    def _get_dependencies(self, template_id: str) -> List[Dict[str, Any]]:
        """Gets dependent templates.
        
        Args:
            template_id: Template ID
            
        Returns:
            List of dependent templates
        """
        # Prepare prompt to find dependencies
        prompt = f"""
        Please find all templates that directly depend on this template:
        
        ID: {template_id}
        
        List only the IDs of the dependent templates.
        Respond in JSON format:
        {{
            "dependencies": ["id1", "id2", "id3"]
        }}
        """
        
        # Generate analysis using LLM
        dependencies = self.llm.generate_structured(prompt)
        
        # Get details of dependent templates
        dependent_templates = []
        for dep_id in dependencies["dependencies"]:
            try:
                template = self.template_manager.get_template(dep_id)
                dependent_templates.append(template)
            except:
                continue
        
        return dependent_templates
    
    def import_template(self, export_data: Dict[str, Any]) -> Dict[str, Any]:
        """Imports an exported template.
        
        Args:
            export_data: Exported template data
            
        Returns:
            Imported template
        """
        # Validate export_data structure
        required_fields = ["template", "metadata"]
        for field in required_fields:
            if field not in export_data:
                raise ValueError(f"Required field '{field}' not found")
        
        # Check compatibility version
        if export_data["metadata"]["version"] != "1.0":
            raise ValueError("Unsupported template version")
        
        # Import main template
        imported_template = self.template_manager.create_template(export_data["template"])
        
        # Import dependencies if they exist
        if "dependencies" in export_data:
            for dep in export_data["dependencies"]:
                try:
                    self.template_manager.create_template(dep)
                except:
                    continue
        
        return imported_template
    
    def validate_export_file(self, file_content: str) -> bool:
        """Validates an export file.
        
        Args:
            file_content: File content
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Try to load JSON
            data = json.loads(file_content)
            
            # Check required fields
            required_fields = ["template", "metadata"]
            for field in required_fields:
                if field not in data:
                    return False
            
            # Check version
            if data["metadata"]["version"] != "1.0":
                return False
            
            return True
        except:
            return False
    
    def generate_export_file(self, template_id: str, include_dependencies: bool = True) -> str:
        """Generates an export file.
        
        Args:
            template_id: Template ID
            include_dependencies: Include dependent templates
            
        Returns:
            Export file content
        """
        # Export template
        export_data = self.export_template(template_id, include_dependencies)
        
        # Generate filename
        template = export_data["template"]
        filename = f"{template['name'].replace(' ', '_')}_template_export.json"
        
        # Convert to formatted JSON
        json_content = json.dumps(export_data, indent=2, ensure_ascii=False)
        
        return json_content, filename
