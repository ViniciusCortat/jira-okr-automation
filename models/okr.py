from typing import Callable, Any
from datetime import datetime


class OKR:
    def __init__(self, 
                 nome: str,
                 metodo_calculo: Callable,
                 nome_coluna: str,
                 responsavel: str):
        
        self.nome = nome
        self.metodo_calculo = metodo_calculo
        self.nome_coluna = nome_coluna
        self.responsavel = responsavel
        
        self.ultimo_valor = None
        self.ultima_execucao = None
    
    def calcular(self) -> Any:
        try:
            self.ultimo_valor = self.metodo_calculo()
            self.ultima_execucao = datetime.now()
            return self.ultimo_valor
        except Exception as e:
            print(f"❌ Erro no OKR '{self.nome}': {e}")
            return 0 if isinstance(self.ultimo_valor, (int, float)) else "0 - 0"