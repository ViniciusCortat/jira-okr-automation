from typing import List, Optional
from services.jql_service import JQLService

class SprintService:
    def __init__(self):
        self.jql_service = JQLService()
    
    def get_active_sprint_names(self) -> List[str]:
        """Retorna nomes das sprints ativas (ou fallback genérico)"""
        return self.jql_service.get_sprint_names()
    
    def get_sprint_metrics(self) -> dict:
        """Retorna métricas da sprint atual"""
        return self.jql_service.get_consolidated_metrics()
    
    def get_sprint_summary(self) -> dict:
        """Resumo completo da sprint"""
        return {
            "sprints": self.get_active_sprint_names(),
            "metrics": self.get_sprint_metrics()
        }