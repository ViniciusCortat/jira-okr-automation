from typing import List, Dict, Optional
from core.jira_client import JiraClient
from config.settings import Settings

class BoardRepository:
    """Gerencia acesso a múltiplos boards"""
    
    def __init__(self, client: JiraClient):
        self.client = client
        self._boards_cache = {}
    
    def get_board_id(self, nome_board: str) -> Optional[int]:
        """Retorna ID do board pelo nome (produto, suporte, etc)"""
        board_map = {
            "produto": Settings.BOARD_PRODUTO,
            "suporte": Settings.BOARD_SUPORTE
        }
        return board_map.get(nome_board.lower())
    
    def get_sprints_ativas(self, board_id: int) -> List[Dict]:
        """Busca sprints ativas de um board específico"""
        cache_key = f"board_{board_id}_sprints"
        
        if cache_key in self._boards_cache:
            return self._boards_cache[cache_key]
        
        try:
            url = f"{self.client.base_url}/rest/agile/1.0/board/{board_id}/sprint"
            params = {"state": "active"}
            headers = self.client.auth.get_headers()
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            sprints = data.get("values", [])
            self._boards_cache[cache_key] = sprints
            return sprints
            
        except Exception:
            return []
    
    def get_sprint_ids(self, board_id: int) -> List[int]:
        """Retorna IDs das sprints ativas de um board"""
        sprints = self.get_sprints_ativas(board_id)
        return [s["id"] for s in sprints if s.get("id")]
    
    def get_sprint_names(self, board_id: int) -> List[str]:
        """Retorna nomes das sprints ativas de um board"""
        sprints = self.get_sprints_ativas(board_id)
        return [s["name"] for s in sprints if s.get("name")]