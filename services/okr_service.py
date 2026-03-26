from typing import Dict, List
from datetime import datetime
from models.okr import OKR, JanelaAnalise
from services.jql_service import JQLService

class OKRService:
    def __init__(self, jql_service: JQLService):
        self.jql = jql_service
        self.okrs: Dict[str, OKR] = {}
        self._inicializar_okrs()
    
    def _inicializar_okrs(self):
        self.okrs["taxa_conclusao"] = OKR(
            nome="Taxa de Conclusão",
            janela=JanelaAnalise.SPRINT_ATUAL,
            metodo_calculo=lambda: self.jql.get_consolidated_metrics()["taxa_conclusao"],
            linha_destino=5, coluna_destino="B"
        )
        
        self.okrs["tarefas_nao_aprovadas"] = OKR(
            nome="Tarefas Não Aprovadas na Sprint",
            janela=JanelaAnalise.SPRINT_ATUAL,
            metodo_calculo=self.jql.get_rejected_tasks_count,
            linha_destino=6, coluna_destino="B"
        )
        
        self.okrs["bugs_proatividade"] = OKR(
            nome="Bugs Registrados Proatividade por Produto",
            janela=JanelaAnalise.ULTIMOS_7_DIAS,
            metodo_calculo=self.jql.get_bugs_proatividade_count,
            linha_destino=7, coluna_destino="B"
        )
        
        self.okrs["bugs_reprovados_qa"] = OKR(
            nome="Bugs Reprovados QA",
            janela=JanelaAnalise.ULTIMOS_30_DIAS,
            metodo_calculo=self.jql.get_bugs_reprovados_qa_count,
            linha_destino=8, coluna_destino="B"
        )
        
        self.okrs["quantidade_deploy"] = OKR(
            nome="Quantidade de Deploys (Releases na Semana)",
            janela=JanelaAnalise.SPRINT_ATUAL,
            metodo_calculo=self.jql.get_quantidade_deploy,
            linha_destino=9, coluna_destino="B"
        )
        
        self.okrs["bugs_dentro_sla"] = OKR(
            nome="Hotfix Dentro do SLA (<48h em Doing)",
            janela=JanelaAnalise.SPRINT_ATUAL,
            metodo_calculo=self.jql.get_bugs_dentro_sla,
            linha_destino=10, coluna_destino="B"
        )
        
        self.okrs["total_bugs_48h_15"] = OKR(
            nome="Total de Hotfix (últimos 15 dias)",
            janela=JanelaAnalise.ULTIMOS_15_DIAS,
            metodo_calculo=self.jql.get_total_bugs_48h_15,
            linha_destino=11, coluna_destino="B"
        )
    
    def executar_okrs(self) -> Dict:
        todas_metricas = self.jql.get_sprint_metrics_dict()
        
        resultados = {}
        for nome, okr in self.okrs.items():
            try:
                valor = okr.calcular()
                resultados[nome] = {
                    "valor": valor,
                    "frequencia": "semanal",
                    "linha": okr.linha_destino,
                    "coluna": okr.coluna_destino
                }
            except Exception as e:
                print(f"   ⚠️ Erro no OKR '{nome}': {e}")
                resultados[nome] = {
                    "valor": 0,
                    "frequencia": "semanal",
                    "linha": okr.linha_destino,
                    "coluna": okr.coluna_destino
                }
        
        return resultados