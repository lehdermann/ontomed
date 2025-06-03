from typing import Dict, List, Any
from prompt.template_manager import TemplateManager

class CategoryManager:
    """Template categories manager."""
    
    def __init__(self, template_manager: TemplateManager):
        """Initialize the category manager.
        
        Args:
            template_manager: Template manager
        """
        self.template_manager = template_manager
        self.categories = [
            {
                "id": "explanation",
                "name": "Explanation",
                "description": "Templates for concept explanation",
                "type": "Text"
            },
            {
                "id": "description",
                "name": "Description",
                "description": "Templates for detailed description",
                "type": "Text"
            },
            {
                "id": "summary",
                "name": "Summary",
                "description": "Templates for generating summaries",
                "type": "Text"
            },
            {
                "id": "example",
                "name": "Example",
                "description": "Templates for generating examples",
                "type": "Text"
            },
            {
                "id": "structured",
                "name": "Structured",
                "description": "Templates for structured content",
                "type": "Structured"
            }
        ]
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all template categories.
        
        Returns:
            List of categories
        """
        return self.categories
    
    def validate_template(self, template_data: Dict[str, Any]) -> List[str]:
        """Validate a template.
        
        Args:
            template_data: Template data
            
        Returns:
            List of found errors
        """
        errors = []
        
        # Check required fields
        required_fields = ["name", "type", "content", "variables", "category_id"]
        for field in required_fields:
            if field not in template_data:
                errors.append(f"Required field '{field}' not found")
        
        # Check valid type
        valid_types = ["Text", "Structured"]
        if template_data.get("type") not in valid_types:
            errors.append(f"Invalid type. Valid types: {', '.join(valid_types)}")
        
        # Check variables
        variables = template_data.get("variables", [])
        if not isinstance(variables, list):
            errors.append("Variables must be a list")
        
        # Check category
        category_id = template_data.get("category_id")
        if category_id:
            category = next((c for c in self.categories if c["id"] == category_id), None)
            if not category:
                errors.append(f"Category '{category_id}' not found")
            elif category["type"] != template_data.get("type"):
                errors.append(f"Template type does not match category type")
        
        return errors
    
    def get_category_by_id(self, category_id: str) -> Dict[str, Any]:
        """Get a category by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Found category
        """
        category = next((c for c in self.categories if c["id"] == category_id), None)
        if not category:
            raise ValueError(f"Category with ID {category_id} not found")
        return category
    
    def get_category_name(self, category_id: str) -> str:
        """Get a category name by ID.
        
        Args:
            category_id: Category ID
            
        Returns:
            Category name or empty string if not found
        """
        try:
            category = self.get_category_by_id(category_id)
            return category.get("name", "")
        except ValueError:
            # If category is not found, return the ID as fallback
            return category_id if category_id else "General"
    
    def validate_category(self, category_id: str) -> bool:
        """Validate if a category exists.
        
        Args:
            category_id: Category ID
            
        Returns:
            True if the category is valid, False otherwise
        """
        try:
            self.get_category_by_id(category_id)
            return True
        except ValueError:
            return False
    
    def get_category_templates(self, category_id: str) -> List[Dict[str, Any]]:
        """Get templates from a specific category.
        
        Args:
            category_id: Category ID
            
        Returns:
            List of templates in the category
        """
        templates = self.template_manager.get_templates()
        return [t for t in templates if t.get("category_id") == category_id]
    
    def validate_template(self, template_data: Dict[str, Any]) -> List[str]:
        """Validate a template.
        
        Args:
            template_data: Template data
            
        Returns:
            List of found errors
        """
        errors = []
        
        # Validate required fields
        required_fields = ["name", "description", "category_id", "type", "content"]
        for field in required_fields:
            if not template_data.get(field):
                errors.append(f"The field '{field}' is required")
        
        # Validate template type
        valid_types = ["Text", "Structured", "Embedding"]
        if template_data.get("type") not in valid_types:
            errors.append(f"Invalid template type. Valid types: {', '.join(valid_types)}")
        
        # Validate category
        valid_categories = [c["id"] for c in self.get_categories()]
        if template_data.get("category_id") not in valid_categories:
            errors.append(f"Invalid category. Valid categories: {', '.join(valid_categories)}")
        
        return errors
    
    def create_template(self, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new template.
        
        Args:
            template_data: Template data
            
        Returns:
            Created template
        """
        errors = self.validate_template(template_data)
        if errors:
            raise ValueError("\n".join(errors))
            
        return self.template_manager.create_template(template_data)
    
    def update_template(self, template_id: str, template_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing template.
        
        Args:
            template_id: Template ID
            template_data: Updated template data
            
        Returns:
            Template atualizado
        """
        errors = self.validate_template(template_data)
        if errors:
            raise ValueError("\n".join(errors))
            
        return self.template_manager.update_template(template_id, template_data)
    
    def delete_template(self, template_id: str) -> None:
        """Exclui um template.
        
        Args:
            template_id: ID do template
        """
        self.template_manager.delete_template(template_id)
