from typing import List, Dict

class MetricsCalculator:
    """Responsável apenas por calcular métricas a partir de issues"""
    
    @staticmethod
    def calcular_taxa_conclusao(issues: List[Dict]) -> float:
        if not issues:
            return 0.0
        
        total = len(issues)
        concluidas = 0
        keywords = ["done", "concluído", "resolved", "closed", "fechado"]
        
        for issue in issues:
            if "fields" not in issue:
                continue
            status = issue["fields"].get("status", {}).get("name", "").lower()
            if any(k in status for k in keywords):
                concluidas += 1
        
        return round((concluidas / total * 100), 2) if total > 0 else 0.0
    
    @staticmethod
    def consolidar_metricas(issues: List[Dict], rejeitadas: List[int], 
                            bugs_proatividade: int, bugs_reprovados: int) -> Dict:
        return {
            "total_tarefas": len(issues),
            "taxa_conclusao": MetricsCalculator.calcular_taxa_conclusao(issues),
            "tarefas_nao_aprovadas": sum(rejeitadas),
            "bugs_proatividade": bugs_proatividade,
            "bugs_reprovados_qa": bugs_reprovados
        }