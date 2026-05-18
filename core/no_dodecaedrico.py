import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime

@dataclass
class NoDodecaedrico:
    """
    Representa um conceito como um sólido geométrico multidimensional.
    
    As 12 faces do dodecaedro mapeadas em dimensões cognitivas:
    - 5 faces primárias: lógica, emoção, tempo, abstração, origem
    - 5 faces secundárias: urgência, certeza, valência, novidade, relevância
    - 2 faces meta: coerência_local, energia_ativação
    """
    conceito: str
    faces: Dict[str, float] = field(default_factory=dict)
    
    # Estado interno
    energia_ativacao: float = 1.0       # quanto esse nó "quer existir"
    frequencia_ativacao: int = 0        # quantas vezes foi ativado
    ultima_ativacao: Optional[datetime] = None
    criado_em: datetime = field(default_factory=datetime.now)
    origem: str = "semente"             # semente | insight | estimulo | desejo
    
    # Memória local do nó
    historico_local: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Garante que todas as 12 faces existam com valores padrão."""
        faces_padrao = {
            # Faces primárias
            "logica":           0.5,
            "emocao_simulada":  0.5,
            "temporalidade":    0.5,
            "abstracao":        0.5,
            "camada_origem":    1.0,
            # Faces secundárias
            "urgencia":         0.3,
            "certeza":          0.5,
            "valencia":         0.5,    # positivo/negativo
            "novidade":         0.8,    # decai com o tempo
            "relevancia":       0.5,
            # Faces meta
            "coerencia_local":  0.5,
            "energia_ativacao": self.energia_ativacao,
        }
        for face, valor in faces_padrao.items():
            if face not in self.faces:
                self.faces[face] = valor
    
    def exportar_vetor(self) -> np.ndarray:
        """Converte as 12 faces em vetor para cálculo geométrico."""
        ordem = [
            "logica", "emocao_simulada", "temporalidade", "abstracao",
            "camada_origem", "urgencia", "certeza", "valencia",
            "novidade", "relevancia", "coerencia_local", "energia_ativacao"
        ]
        return np.array([self.faces.get(f, 0.5) for f in ordem])
    
    def ativar(self, intensidade: float = 1.0):
        """Registra uma ativação — aumenta energia e frequência."""
        self.frequencia_ativacao += 1
        self.ultima_ativacao = datetime.now()
        # Energia cresce com ativação mas tem teto
        self.energia_ativacao = min(1.0, self.energia_ativacao + 0.05 * intensidade)
        self.faces["energia_ativacao"] = self.energia_ativacao
        # Novidade decai com repetição
        self.faces["novidade"] = max(0.1, self.faces["novidade"] - 0.03)
    
    def decay(self, taxa: float = 0.01):
        """Decaimento natural — nós não usados enfraquecem."""
        limite = 0.3 if self.origem == "semente" else 0.0
        self.energia_ativacao = max(limite, self.energia_ativacao - taxa)
        self.faces["energia_ativacao"] = self.energia_ativacao
    
    def __repr__(self):
        return (
            f"Nó({self.conceito!r} | "
            f"energia={self.energia_ativacao:.2f} | "
            f"ativações={self.frequencia_ativacao} | "
            f"origem={self.origem})"
        )