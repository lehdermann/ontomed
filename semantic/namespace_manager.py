import requests
from typing import Optional


class BlazegraphNamespaceManager:
    """
    Manages Blazegraph namespaces via REST API.
    
    Args:
        base_url: Base URL of the Blazegraph server
    """
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self._session = requests.Session()
        
    def create_namespace(self, name: str) -> bool:
        """
        Creates a namespace in Blazegraph if it doesn't exist.
        
        Args:
            name: Name of the namespace
            
        Returns:
            bool: True if namespace was created or already exists
            
        Raises:
            requests.RequestException: If the request fails
        """
        try:
            # Check if namespace exists
            check_url = f"{self.base_url}/namespace/{name}/status"
            response = self.session.get(check_url)
            
            if response.status_code == 200:
                logger.info(f"Namespace '{name}' already exists.")
                return True  # Namespace already exists
            
            # Create namespace
            create_url = f"{self.base_url}/namespace"
            response = self.session.post(create_url, data={"namespace": name})
            
            if response.status_code == 201:
                logger.info(f"Namespace '{name}' created successfully.")
                return True
            
            # Handle 409 (Conflict) - namespace already exists
            if response.status_code == 409:
                logger.info(f"Namespace '{name}' already exists.")
                return True
            
            # For other errors, raise an exception
            response.raise_for_status()
            return False
                
        except requests.RequestException as e:
            raise requests.RequestException(f"Failed to create namespace: {e}")
