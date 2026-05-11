from datetime import datetime
from pathlib import Path
from config.settings import Settings
from config.variables import Variables


class RelatorioHandler:
    def __init__(self):
        self.conteudo = []
        self.ativo = False
    
    def ativar(self):
        self.ativo = True
        print("   📄 Sistema de relatório ativado")
    
    def desativar(self):
        self.ativo = False
    
    def adicionar_secao(self, titulo: str):
        if not self.ativo:
            return
        self.conteudo.append(f"\n{'='*80}")
        self.conteudo.append(f"📊 {titulo}")
        self.conteudo.append(f"{'='*80}")
    
    def adicionar_linha(self, texto: str, indent: int = 0):
        if not self.ativo:
            return
        espaco = "  " * indent
        self.conteudo.append(f"{espaco}{texto}")
    
    def adicionar_okr_resumo(self, nome: str, valor, descricao: str = ""):
        if not self.ativo:
            return
        self.conteudo.append(f"\n📌 {nome}: {valor}")
        if descricao:
            self.conteudo.append(f"   {descricao}")
        self.conteudo.append(f"{'-'*40}")
    
    def salvar(self, nome_sprint: str = ""):
        if not self.ativo or not self.conteudo:
            return
        data_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_arquivo = f"relatorio_{data_str}.txt"
        caminho = Settings.DATA_DIR / nome_arquivo
        Settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        cabecalho = [
            "="*80,
            f"RELATÓRIO DE OKRs - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Sprint: {nome_sprint}",
            "="*80
        ]
        try:
            with open(caminho, 'w', encoding='utf-8') as f:
                f.write("\n".join(cabecalho))
                f.write("\n".join(self.conteudo))
                f.write(f"\n{'='*80}\n")
            print(f"   ✅ Relatório salvo: {caminho}")
            self.conteudo = []
        except Exception as e:
            print(f"   ❌ Erro ao salvar relatório: {e}")

relatorio = RelatorioHandler()