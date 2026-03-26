from typing import Dict, List, Optional
from core.jira_client import JiraClient
from services.board_repository import BoardRepository
from services.issue_repository import IssueRepository
from services.metrics_calculator import MetricsCalculator

class ProjetoService:
    """
    Serviço para gerenciar métricas de um projeto específico
    """
    
    def __init__(self, client: JiraClient, nome_projeto: str, chave_projeto: str):
        self.client = client
        self.nome = nome_projeto
        self.chave = chave_projeto
        self.boards = BoardRepository(client)
        self.issues = IssueRepository(client)
        self._cached_metrics = None
    
    def get_board_id(self) -> Optional[int]:
        """Retorna ID do board associado ao projeto"""
        return self.boards.get_board_id(self.nome)
    
    def get_sprint_ids(self) -> List[int]:
        """Retorna IDs das sprints ativas do projeto"""
        board_id = self.get_board_id()
        if not board_id:
            return []
        return self.boards.get_sprint_ids(board_id)
    
    def get_sprint_names(self) -> List[str]:
        """Retorna nomes das sprints ativas do projeto"""
        board_id = self.get_board_id()
        if not board_id:
            return []
        return self.boards.get_sprint_names(board_id)
    
    def get_ciclo(self) -> str:
        """Retorna o ciclo da sprint atual (ex: Sprint 26Q1.5)"""
        nomes = self.get_sprint_names()
        if not nomes:
            return f"{self.nome} - Sem sprint"
        
        # Extrair ciclo do primeiro nome
        import re
        match = re.search(r'(Sprint\s+\d{2}Q\d\.\d+)', nomes[0])
        return match.group(1) if match else nomes[0]
    
    def calcular_metricas(self) -> Dict:
        """Calcula todas as métricas do projeto"""
        sprint_ids = self.get_sprint_ids()
        
        if not sprint_ids:
            return {
                "total_tarefas": 0,
                "taxa_conclusao": 0.0,
                "tarefas_nao_aprovadas": 0,
                "bugs_proatividade": 0,
                "bugs_reprovados_qa": 0
            }
        
        dados = self.issues.buscar_tudo_paralelo(sprint_ids, self.chave)
        
        return MetricsCalculator.consolidar_metricas(
            issues=dados["issues"],
            rejeitadas=dados["rejeitadas"],
            bugs_proatividade=dados["bugs_proatividade"],
            bugs_reprovados=dados["bugs_reprovados"]
        )
    
    def get_metricas(self) -> Dict:
        """Retorna métricas (com cache)"""
        if not self._cached_metrics:
            self._cached_metrics = self.calcular_metricas()
        return self._cached_metrics
    
    def limpar_cache(self):
        """Limpa cache de métricas"""
        self._cached_metrics = None