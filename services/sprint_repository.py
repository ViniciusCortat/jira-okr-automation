from typing import List, Dict
from core.jira_client import JiraClient

class SprintRepository:
    """Responsável apenas por buscar dados de sprints"""
    
    def __init__(self, client: JiraClient):
        self.client = client
        self._sprint_ids: List[int] = []
        self._sprint_names: List[str] = []
    
    def carregar_sprints_ativas(self):
        """Carrega IDs e nomes das sprints ativas"""
        if self._sprint_ids:
            return
        
        sprints = self.client.get_active_sprints_via_agile()
        if sprints:
            self._sprint_ids = [s["id"] for s in sprints if s.get("id")]
            self._sprint_names = [s["name"] for s in sprints if s.get("name")]
    
    @property
    def ids(self) -> List[int]:
        self.carregar_sprints_ativas()
        return self._sprint_ids
    
    @property
    def nomes(self) -> List[str]:
        self.carregar_sprints_ativas()
        return self._sprint_names
    
    @property
    def primeiro_nome(self) -> str:
        return self.nomes[0] if self.nomes else "Sprint Desconhecida"
    
    def extrair_ciclo(self, nome_completo: str) -> str:
        """Extrai apenas o ciclo do nome (ex: 'Sprint 26Q1.5')"""
        import re
        if not nome_completo:
            return "Sprint Desconhecida"
        match = re.search(r'(Sprint\s+\d{2}Q\d\.\d+)', nome_completo)
        return match.group(1) if match else nome_completo
    
    @property
    def ciclos(self) -> List[str]:
        ciclos = set()
        for nome in self.nomes:
            ciclos.add(self.extrair_ciclo(nome))
        return sorted(list(ciclos)) if ciclos else []