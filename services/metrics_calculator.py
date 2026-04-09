from typing import List, Dict
from datetime import datetime, timedelta
import re


class MetricsCalculator:
    """Cálculos auxiliares reutilizáveis por OKRs"""
    
    @staticmethod
    def extrair_ciclo(nome_sprint: str) -> str:
        """Extrai o ciclo do nome da sprint (ex: 'Sprint 26Q1.5')"""
        if not nome_sprint:
            return "Sprint Desconhecida"
        
        match = re.search(r'(Sprint\s+\d{2}Q\d\.\d+)', nome_sprint)
        if match:
            return match.group(1)
        
        parts = nome_sprint.split()
        if len(parts) >= 3:
            return f"{parts[0]} {parts[1]} {parts[2]}"
        
        return nome_sprint
    
    @staticmethod
    def calcular_taxa_conclusao(issues: List[Dict]) -> Dict:
        """Calcula total_tarefas, total_concluidas, taxa_conclusao"""
        total = len(issues)
        concluidas = 0
        keywords = ["done", "concluído", "resolved", "closed", "fechado"]
        
        for issue in issues:
            if "fields" not in issue:
                continue
            status = issue["fields"].get("status", {}).get("name", "").lower()
            if any(k in status for k in keywords):
                concluidas += 1
        
        taxa = (concluidas / total * 100) if total > 0 else 0
        
        return {
            "total_tarefas": total,
            "total_concluidas": concluidas,
            "taxa_conclusao": round(taxa, 2)
        }
    
    @staticmethod
    def hotfix_excedeu_limite(changelog: List[Dict], limite_horas: int = 48) -> bool:
        """Verifica se um hotfix excedeu o limite de horas em 'doing'"""
        tempo_doing = 0
        em_doing = False
        entrou_em = None
        
        for entry in sorted(changelog, key=lambda x: x['created']):
            data = datetime.strptime(entry['created'].split('.')[0], "%Y-%m-%dT%H:%M:%S")
            
            for item in entry.get('items', []):
                if item['field'] == 'status':
                    para = item['toString']
                    
                    if "doing" in para.lower() and not em_doing:
                        em_doing = True
                        entrou_em = data
                    elif "doing" not in para.lower() and em_doing:
                        tempo_doing += (data - entrou_em).total_seconds()
                        em_doing = False
        
        if em_doing and entrou_em:
            tempo_doing += (datetime.now() - entrou_em).total_seconds()
        
        return (tempo_doing / 3600) > limite_horas
    
    @staticmethod
    def contar_por_status(issues: List[Dict], status_lista: List[str]) -> int:
        """Conta quantas issues estão em um dos status da lista"""
        count = 0
        for issue in issues:
            status = issue["fields"].get("status", {}).get("name", "")
            if status in status_lista:
                count += 1
        return count