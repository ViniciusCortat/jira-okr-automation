from typing import Dict, List
from datetime import datetime
from collections import defaultdict
from models.okr import OKR
from services.jql_service import JQLService
from services.metrics_calculator import MetricsCalculator
from utils.relatorio_handler import relatorio


class OKRService:
    def __init__(self, jql_service: JQLService):
        self.jql = jql_service
        self.calc = MetricsCalculator()
        self.okrs: Dict[str, OKR] = {}
        self._metricas_base = {}
        self._relatorio_gerado = False
        self._inicializar_okrs()
    
    def _carregar_metricas_base(self):
        if self._metricas_base:
            return
        issues = self.jql.get_issues_from_sprints()
        self._metricas_base = self.calc.calcular_taxa_conclusao(issues)
    
    def _formatar_lead_time(self, resultado: Dict) -> str:
        media = resultado.get("media", 0)
        mediana = resultado.get("mediana", 0)
        if media == 0 and mediana == 0:
            return "0 - 0"
        return f"{media} - {mediana}"
    
    def _inicializar_okrs(self):
        self.okrs["total_tarefas"] = OKR(
            nome="Total de Tarefas",
            metodo_calculo=lambda: self._metricas_base["total_tarefas"],
            nome_coluna="total_tarefas",
            responsavel="Bruno"
        )
        self.okrs["taxa_conclusao"] = OKR(
            nome="Taxa de Conclusão",
            metodo_calculo=lambda: self._metricas_base["taxa_conclusao"],
            nome_coluna="taxa_conclusao",
            responsavel="Bruno"
        )
        self.okrs["tarefas_nao_aprovadas"] = OKR(
            nome="Tarefas Não Aprovadas na Sprint",
            metodo_calculo=self.jql.get_rejected_tasks_count,
            nome_coluna="tarefas_nao_aprovadas",
            responsavel="Bruno"
        )
        self.okrs["bugs_proatividade"] = OKR(
            nome="Bugs Registrados Proatividade",
            metodo_calculo=self.jql.get_bugs_proatividade_count,
            nome_coluna="bugs_proatividade",
            responsavel="Bruno"
        )
        self.okrs["bugs_reprovados_qa"] = OKR(
            nome="Bugs Reprovados QA",
            metodo_calculo=self.jql.get_bugs_reprovados_qa_count,
            nome_coluna="bugs_reprovados_qa",
            responsavel="Cassano"
        )
        self.okrs["bugs_abertos_infra"] = OKR(
            nome="Bugs Abertos - Infra",
            metodo_calculo=lambda: self.jql.contar_hotfix_por_funcionalidade("Infra"),
            nome_coluna="bugs_abertos_infra",
            responsavel="Cassano"
        )
        self.okrs["quantidade_deploy"] = OKR(
            nome="Quantidade de Deploys",
            metodo_calculo=self.jql.get_quantidade_deploy,
            nome_coluna="quantidade_deploy",
            responsavel="Cassano"
        )
        self.okrs["bugs_abertos_sync"] = OKR(
            nome="Bugs Abertos - Sincronizações",
            metodo_calculo=lambda: self.jql.contar_hotfix_por_funcionalidade_com_status("Integração Principal")["abertos"],
            nome_coluna="bugs_abertos_sync",
            responsavel="Cassano"
        )
        self.okrs["tickets_nova_integracao"] = OKR(
            nome="Tickets de Novas Integrações",
            metodo_calculo=self.jql.get_tickets_nova_integracao,
            nome_coluna="tickets_nova_integracao",
            responsavel="Cassano"
        )
        self.okrs["bugs_dentro_sla"] = OKR(
            nome="Hotfix Dentro do SLA",
            metodo_calculo=self.jql.get_bugs_dentro_sla,
            nome_coluna="bugs_dentro_sla",
            responsavel="Cassano"
        )
        self.okrs["lead_resolucao_bugs"] = OKR(
            nome="Lead Time - Bugs",
            metodo_calculo=lambda: self._formatar_lead_time(self.jql.get_lead_time_bugs()),
            nome_coluna="lead_resolucao_bugs",
            responsavel="Cassano"
        )
        self.okrs["lead_resolucao_nao_critico"] = OKR(
            nome="Lead Time - Bugs Não Críticos",
            metodo_calculo=lambda: self._formatar_lead_time(self.jql.get_lead_time_bugs_nao_critico()),
            nome_coluna="lead_resolucao_nao_critico",
            responsavel="Cassano"
        )
        self.okrs["lead_resolucao_critico"] = OKR(
            nome="Lead Time - Bugs Críticos",
            metodo_calculo=lambda: self._formatar_lead_time(self.jql.get_lead_time_bugs_critico()),
            nome_coluna="lead_resolucao_critico",
            responsavel="Cassano"
        )
        self.okrs["taxa_bug_reaberto"] = OKR(
            nome="Taxa de Bugs Reabertos",
            metodo_calculo=self.jql.get_taxa_bug_reaberto,
            nome_coluna="taxa_bug_reaberto",
            responsavel="Cassano"
        )
        self.okrs["bugs_por_quinzena"] = OKR(
            nome="Bugs da Quinzena",
            metodo_calculo=self.jql.get_bugs_por_quinzena,
            nome_coluna="bugs_por_quinzena",
            responsavel="Cassano"
        )
        self.okrs["bugs_cancelados_quinzena"] = OKR(
            nome="Bugs Cancelados na Quinzena",
            metodo_calculo=self.jql.get_bugs_cancelados_quinzena,
            nome_coluna="bugs_cancelados_quinzena",
            responsavel="Cassano"
        )
        self.okrs["total_bugs_48h_15"] = OKR(
            nome="Total de Hotfix (15 dias)",
            metodo_calculo=self.jql.get_total_bugs_48h_15,
            nome_coluna="total_bugs_48h_15",
            responsavel="Cassano"
        )
        self.okrs["bugs_subidos_nova_func"] = OKR(
            nome="Hotfix de Novas Funcionalidades",
            metodo_calculo=self.jql.get_bugs_subidos_nova_func,
            nome_coluna="bugs_subidos_nova_func",
            responsavel="Cassano"
        )
        self.okrs["bugs_escalados_complexidade"] = OKR(
            nome="Hotfix Escalados do QA",
            metodo_calculo=self.jql.get_bugs_escalados_complexidade,
            nome_coluna="bugs_escalados_complexidade",
            responsavel="Cassano"
        )
        self.okrs["bugs_escalados_prazo"] = OKR(
            nome="Hotfix Fora do Prazo (2 dias)",
            metodo_calculo=self.jql.get_bugs_escalados_prazo,
            nome_coluna="bugs_escalados_prazo",
            responsavel="Cassano"
        )
        self.okrs["taxa_bugs_com_tag"] = OKR(
            nome="Taxa de Hotfix com Tag",
            metodo_calculo=self.jql.get_taxa_bugs_com_tag,
            nome_coluna="taxa_bugs_com_tag",
            responsavel="Cassano"
        )
        self.okrs["bugs_subidos_nova_func_vs_total"] = OKR(
            nome="Novas Funcionalidades vs Total",
            metodo_calculo=self.jql.get_bugs_subidos_nova_func_vs_total,
            nome_coluna="bugs_subidos_nova_func_vs_total",
            responsavel="Cassano"
        )
    
    def _get_okr_descricao(self, nome: str) -> str:
        descricoes = {
            "total_tarefas": "Total de tarefas na sprint",
            "taxa_conclusao": "Percentual de tarefas concluídas",
            "tarefas_nao_aprovadas": "Tarefas rejeitadas na validação",
            "bugs_proatividade": "Bugs de proatividade (últimos 7 dias)",
            "bugs_reprovados_qa": "Bugs reprovados pelo QA no mês",
            "bugs_abertos_infra": "Hotfix abertos com tag 'Infra'",
            "quantidade_deploy": "Releases na semana atual",
            "bugs_abertos_sync": "Hotfix abertos com tag 'Integração Principal'",
            "tickets_nova_integracao": "Hotfix de novas integrações",
            "bugs_dentro_sla": "% de hotfix que ficaram <48h em Doing",
            "lead_resolucao_bugs": "Média e mediana de resolução de bugs",
            "lead_resolucao_nao_critico": "Média e mediana de bugs não críticos",
            "lead_resolucao_critico": "Média e mediana de bugs críticos",
            "taxa_bug_reaberto": "% de bugs reabertos na semana",
            "bugs_por_quinzena": "Bugs criados no período (excluindo cancelados)",
            "bugs_cancelados_quinzena": "Bugs cancelados no período",
            "total_bugs_48h_15": "Total de hotfix nos últimos 15 dias",
            "bugs_subidos_nova_func": "Hotfix de novas funcionalidades",
            "bugs_escalados_complexidade": "Hotfix escalados do time de QA",
            "bugs_escalados_prazo": "Hotfix com >48h em Doing nas releases",
            "taxa_bugs_com_tag": "% de hotfix com funcionalidade preenchida",
            "bugs_subidos_nova_func_vs_total": "Novas funcionalidades vs Total"
        }
        return descricoes.get(nome, "")
    
    def _adicionar_detalhamento_okr(self, nome_okr: str):
        mapeamento = {
            "Bugs da Quinzena": self.jql.detalhar_bugs_por_quinzena,
            "Bugs Cancelados na Quinzena": self.jql.detalhar_bugs_cancelados_quinzena,
            "Bugs Abertos - Infra": lambda: self.jql.detalhar_hotfix_por_funcionalidade("Infra"),
            "Bugs Abertos - Sincronizações": lambda: self.jql.detalhar_hotfix_por_funcionalidade("Integração Principal"),
            "Tickets de Novas Integrações": self.jql.detalhar_novas_integracoes,
            "Hotfix de Novas Funcionalidades": self.jql.detalhar_hotfix_novas_funcionalidades,
            "Total de Hotfix (15 dias)": self.jql.detalhar_hotfix_15_dias,
            "Taxa de Bugs Reabertos": self.jql.detalhar_bugs_reabertos,
            "Taxa de Hotfix com Tag": self.jql.detalhar_bugs_sem_tag,
            "Lead Time - Bugs": lambda: self.jql.detalhar_lead_time_por_criticidade("nao_criticos"),
            "Lead Time - Bugs Críticos": lambda: self.jql.detalhar_lead_time_por_criticidade("criticos"),
        }
        if nome_okr in mapeamento:
            mapeamento[nome_okr]()
    
    def _gerar_relatorio(self, okrs_por_responsavel: Dict[str, List[tuple]]):
        relatorio.adicionar_linha("")
        relatorio.adicionar_linha("MÉTRICAS BASE")
        relatorio.adicionar_linha("-" * 40)
        relatorio.adicionar_linha(f"Total de Tarefas: {self._metricas_base['total_tarefas']}")
        relatorio.adicionar_linha(f"Taxa de Conclusão: {self._metricas_base['taxa_conclusao']}%")
        
        for responsavel in sorted(okrs_por_responsavel.keys()):
            relatorio.adicionar_linha("")
            relatorio.adicionar_linha(f"OKRs - {responsavel}")
            relatorio.adicionar_linha("-" * 40)
            for nome, valor in okrs_por_responsavel[responsavel]:
                descricao = self._get_okr_descricao(nome)
                relatorio.adicionar_linha(f"{nome}: {valor}")
                if descricao:
                    relatorio.adicionar_linha(f"  {descricao}")
                self._adicionar_detalhamento_okr(nome)
                relatorio.adicionar_linha("")
    
    def executar_okrs(self) -> Dict[str, Dict]:
        self._carregar_metricas_base()
        resultados = {}
        okrs_por_responsavel = defaultdict(list)
        for nome, okr in self.okrs.items():
            try:
                valor = okr.calcular()
                resultados[nome] = {
                    "valor": valor,
                    "nome_coluna": okr.nome_coluna,
                    "responsavel": okr.responsavel
                }
                okrs_por_responsavel[okr.responsavel].append((okr.nome, valor))
            except Exception as e:
                print(f"   ⚠️ Erro no OKR '{nome}': {e}")
                resultados[nome] = {
                    "valor": 0 if isinstance(okr.metodo_calculo(), (int, float)) else "0 - 0",
                    "nome_coluna": okr.nome_coluna,
                    "responsavel": okr.responsavel
                }
        if relatorio.ativo and not self._relatorio_gerado:
            self._gerar_relatorio(okrs_por_responsavel)
            self._relatorio_gerado = True
        return resultados
    
    def get_dados_por_responsavel(self) -> Dict[str, Dict]:
        resultados = self.executar_okrs()
        dados_por_responsavel = {}
        metricas_base = {"total_tarefas": self._metricas_base["total_tarefas"]}
        sprint_nome = self.jql.get_primeiro_nome_sprint()
        ciclo = self.calc.extrair_ciclo(sprint_nome) if sprint_nome else "Sprint Atual"
        for dados in resultados.values():
            resp = dados["responsavel"]
            if resp not in dados_por_responsavel:
                dados_por_responsavel[resp] = {
                    "data_coleta": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "sprint": ciclo,
                    "valores": metricas_base.copy()
                }
            dados_por_responsavel[resp]["valores"][dados["nome_coluna"]] = dados["valor"]
        if "Bruno" in dados_por_responsavel:
            dados_por_responsavel["Bruno"]["valores"]["taxa_conclusao"] = self._metricas_base["taxa_conclusao"]
        return dados_por_responsavel