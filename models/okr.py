from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime

class FrequenciaOKR(Enum):
    SEMANAL = "semanal"

class JanelaAnalise(Enum):
    ULTIMOS_7_DIAS = "7d"
    ULTIMOS_15_DIAS = "15d"
    ULTIMOS_30_DIAS = "30d"
    SPRINT_ATUAL = "sprint_atual"

class OKR:
    def __init__(self, nome: str, janela: JanelaAnalise,
                 metodo_calculo: Callable, linha_destino: int, coluna_destino: str):
        self.nome = nome
        self.frequencia = FrequenciaOKR.SEMANAL
        self.janela = janela
        self.metodo_calculo = metodo_calculo
        self.linha_destino = linha_destino
        self.coluna_destino = coluna_destino
        self.ultimo_valor: Optional[Any] = None
        self.ultima_execucao: Optional[datetime] = None
    
    def calcular(self) -> Any:
        try:
            resultado = self.metodo_calculo()
            self.ultimo_valor = resultado if resultado is not None else 0
            self.ultima_execucao = datetime.now()
            return self.ultimo_valor
        except Exception as e:
            print(f"❌ Erro no OKR '{self.nome}': {e}")
            return 0
    
    def deve_executar(self) -> bool:
        if not self.ultima_execucao:
            return True
        dias_desde = (datetime.now() - self.ultima_execucao).days
        return dias_desde >= 7