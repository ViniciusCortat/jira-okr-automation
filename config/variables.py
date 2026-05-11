import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class Variables:
    LEAD_TIME_DIAS = int(os.getenv("LEAD_TIME_DIAS", 15))
    
    @classmethod
    def get_periodo_analise(cls, referencia_sexta: datetime = None) -> tuple:
        if referencia_sexta is None:
            hoje = datetime.now()
            dias_para_sexta = (4 - hoje.weekday()) % 7
            referencia_sexta = hoje + timedelta(days=dias_para_sexta)
        quinta_anterior = referencia_sexta - timedelta(days=1)
        sexta_retrasada = quinta_anterior - timedelta(days=13)
        return sexta_retrasada, quinta_anterior
    
    LEAD_TIME_META_DIAS = int(os.getenv("LEAD_TIME_META_DIAS", 10))
    META_PERCENTUAL_RESOLUCAO = int(os.getenv("META_PERCENTUAL_RESOLUCAO", 80))
    
    FREQUENCIA_DIARIA = 1
    FREQUENCIA_SEMANAL = 7
    FREQUENCIA_QUINZENAL = 15
    FREQUENCIA_MENSAL = 30
    FREQUENCIA_PADRAO = FREQUENCIA_SEMANAL
    
    NOVAS_INTEGRACOES = os.getenv("NOVAS_INTEGRACOES", "Baselinker,Omie,Lexos,Todas").split(",")
    NOVAS_INTEGRACOES = [i.strip() for i in NOVAS_INTEGRACOES]
    
    NOVAS_FUNCIONALIDADES = os.getenv("NOVAS_FUNCIONALIDADES", "Precificar,Dashboard V2,Comprar V2").split(",")
    NOVAS_FUNCIONALIDADES = [f.strip() for f in NOVAS_FUNCIONALIDADES]
    
    TIME_QA_EMAILS = os.getenv("TIME_QA_EMAILS", 
        "felipe.cassano@precocerto.co,thiago.mattos@precocerto.co,atila.silva@precocerto.co,joao.marcos@precocerto.co"
    ).split(",")
    TIME_QA_EMAILS = [e.strip() for e in TIME_QA_EMAILS]
    
    STATUS_CONCLUIDOS = ["BUG RESOLVIDO", "Resolvido", "Resolved", "Fechado", "Closed", "Concluído", "Done"]
    STATUS_CANCELADOS = ["Cancelado", "CANCELADO", "Despriorizado", "DESPRIORIZADO"]
    
    GERAR_RELATORIO = os.getenv("GERAR_RELATORIO", "False").lower() == "true"
    
    @classmethod
    def get_novas_integracoes(cls) -> list:
        return cls.NOVAS_INTEGRACOES
    
    @classmethod
    def get_novas_funcionalidades(cls) -> list:
        return cls.NOVAS_FUNCIONALIDADES
    
    @classmethod
    def get_time_qa_emails(cls) -> list:
        return cls.TIME_QA_EMAILS
    
    @classmethod
    def exibir_configuracoes(cls):
        inicio, fim = cls.get_periodo_analise()
        print("\n📋 CONFIGURAÇÕES ATUAIS:")
        print(f"   • LEAD_TIME_DIAS: {cls.LEAD_TIME_DIAS} dias")
        print(f"   • PERÍODO FIXO: {inicio.strftime('%d/%m/%Y')} → {fim.strftime('%d/%m/%Y')}")
        print(f"   • NOVAS_INTEGRACOES: {', '.join(cls.NOVAS_INTEGRACOES)}")
        print(f"   • NOVAS_FUNCIONALIDADES: {', '.join(cls.NOVAS_FUNCIONALIDADES)}")
        print(f"   • GERAR_RELATORIO: {cls.GERAR_RELATORIO}")