from config.settings import Settings
from core.jira_client import JiraClient
from services.jql_service import JQLService
from services.okr_service import OKRService
from services.metrics_calculator import MetricsCalculator
from utils.csv_handler import CSVHandler
from utils.relatorio_handler import relatorio
from config.variables import Variables
from datetime import datetime


def main():
    try:
        Settings.validate()
        if Variables.GERAR_RELATORIO:
            relatorio.ativar()
        else:
            relatorio.desativar()
        
        client = JiraClient()
        if not client.test_connection():
            print("❌ Falha na conexão com Jira")
            return
        
        jql_service = JQLService()
        okr_service = OKRService(jql_service)
        
        nome_sprint_completo = jql_service.get_primeiro_nome_sprint()
        ciclo = MetricsCalculator.extrair_ciclo(nome_sprint_completo) if nome_sprint_completo else "Sprint Atual"
        
        if not nome_sprint_completo:
            print("⚠️ Nenhuma sprint ativa encontrada, usando 'Sprint Atual'")
        
        print(f"\n📊 Ciclo: {ciclo}")
        
        resultados = okr_service.executar_okrs()
        
        print(f"\n📈 OKRs EXECUTADOS HOJE:")
        for nome, dados in resultados.items():
            print(f"   • {nome}: {dados['valor']} ({dados['responsavel']})")
        
        dados_por_responsavel = okr_service.get_dados_por_responsavel()
        for responsavel, dados in dados_por_responsavel.items():
            dados["sprint"] = ciclo
        CSVHandler.salvar_todos_csvs(dados_por_responsavel)
        
        if relatorio.ativo and relatorio.conteudo:
            relatorio.salvar(ciclo)
            if hasattr(okr_service, '_relatorio_gerado'):
                delattr(okr_service, '_relatorio_gerado')
        
        print(f"\n💾 Dados salvos em: {CSVHandler.DATA_DIR}")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")


if __name__ == "__main__":
    main()