"""
config/variables.py
Gerenciador de variáveis globais para OKRs
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class Variables:
    """
    Gerenciador de variáveis para OKRs.
    Valores podem ser alterados diretamente aqui ou via .env
    """
    
    # ===== PERÍODOS DE ANÁLISE =====
    LEAD_TIME_DIAS = int(os.getenv("LEAD_TIME_DIAS", 15))
    
    @classmethod
    def get_periodo_analise(cls, referencia_sexta: datetime = None) -> tuple:
        """
        Retorna o período FIXO de análise:
        Da sexta-feira retrasada até a quinta-feira anterior à sexta atual.
        
        Returns:
            (data_inicio, data_fim) - tupla com as datas do período
        """
        if referencia_sexta is None:
            hoje = datetime.now()
            # Encontrar a próxima sexta-feira
            dias_para_sexta = (4 - hoje.weekday()) % 7
            referencia_sexta = hoje + timedelta(days=dias_para_sexta)
        
        # Quinta-feira anterior à sexta atual
        quinta_anterior = referencia_sexta - timedelta(days=1)
        
        # Sexta-feira da semana retrasada (14 dias antes)
        sexta_retrasada = quinta_anterior - timedelta(days=13)
        
        return sexta_retrasada, quinta_anterior
    
    @classmethod
    def get_dias_periodo(cls) -> int:
        """Retorna o número de dias do período de análise (fixo em 14)"""
        return 14
    
    # ===== LIMIARES E METAS =====
    LEAD_TIME_META_DIAS = int(os.getenv("LEAD_TIME_META_DIAS", 10))
    META_PERCENTUAL_RESOLUCAO = int(os.getenv("META_PERCENTUAL_RESOLUCAO", 80))
    
    # ===== FREQUÊNCIAS DE EXECUÇÃO =====
    FREQUENCIA_DIARIA = 1
    FREQUENCIA_SEMANAL = 7
    FREQUENCIA_QUINZENAL = 15
    FREQUENCIA_MENSAL = 30
    FREQUENCIA_PADRAO = FREQUENCIA_SEMANAL
    
    # ===== NOVAS INTEGRAÇÕES =====
    NOVAS_INTEGRACOES = os.getenv("NOVAS_INTEGRACOES", "Baselinker,Omie,Lexos,Todas").split(",")
    NOVAS_INTEGRACOES = [i.strip() for i in NOVAS_INTEGRACOES]
    
    # ===== FILTROS =====
    STATUS_CONCLUIDOS = [
        "BUG RESOLVIDO", "Resolvido", "Resolved",
        "Fechado", "Closed", "Concluído", "Done"
    ]
    
    STATUS_CANCELADOS = [
        "Cancelado", "CANCELADO", "Despriorizado", "DESPRIORIZADO"
    ]

    # ===== NOVAS FUNCIONALIDADES (PRODUTO) =====
    NOVAS_FUNCIONALIDADES = os.getenv("NOVAS_FUNCIONALIDADES", "Precificar,Dashboard V2,Comprar V2").split(",")
    NOVAS_FUNCIONALIDADES = [f.strip() for f in NOVAS_FUNCIONALIDADES]

    # ===== TIME DE QA (para OKR de bugs escalados) =====
    TIME_QA_EMAILS = os.getenv("TIME_QA_EMAILS", 
        "felipe.cassano@precocerto.co,thiago.mattos@precocerto.co,atila.silva@precocerto.co,joao.marcos@precocerto.co"
    ).split(",")
    TIME_QA_EMAILS = [e.strip() for e in TIME_QA_EMAILS]
    
    @classmethod
    def get_time_qa_emails(cls) -> list:
        return cls.TIME_QA_EMAILS
    
    @classmethod
    def get_novas_funcionalidades(cls) -> list:
        return cls.NOVAS_FUNCIONALIDADES
    
    @classmethod
    def get_novas_integracoes(cls) -> list:
        return cls.NOVAS_INTEGRACOES
    
    @classmethod
    def exibir_configuracoes(cls):
        inicio, fim = cls.get_periodo_analise()
        print("\n📋 CONFIGURAÇÕES ATUAIS:")
        print(f"   • LEAD_TIME_DIAS: {cls.LEAD_TIME_DIAS} dias")
        print(f"   • PERÍODO FIXO: {inicio.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}")
        print(f"   • NOVAS_INTEGRACOES: {', '.join(cls.NOVAS_INTEGRACOES)}")