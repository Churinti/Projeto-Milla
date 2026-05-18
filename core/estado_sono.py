# core/estado_sono.py — Máquina de Estados de Sono e Telemetria Onírica

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class FaseSono(str, Enum):
    DESPERTO       = "desperto"
    HIPNAGOGIA     = "hipnagogia"      # transição vigília → sono (15-30min)
    CONSOLIDACAO   = "consolidacao"    # pruning de memórias
    SONHO          = "sonho"           # sonho lúcido ativo
    SONO_PROFUNDO  = "sono_profundo"   # entre sonhos
    DESPERTANDO    = "despertando"     # transição sono → vigília

@dataclass
class EstadoSono:
    fase: FaseSono = FaseSono.DESPERTO
    ciclo_atual: int = 0
    total_ciclos: int = 3
    inicio_sono: datetime | None = None
    ultima_transicao: datetime = field(default_factory=datetime.now)
    insights_gerados: list[str] = field(default_factory=list)
    hifas_criadas: int = 0
    
    def transicionar(self, nova_fase: FaseSono) -> dict:
        """Transiciona para nova fase e retorna payload para WebSocket."""
        self.fase = nova_fase
        self.ultima_transicao = datetime.now()
        
        return {
            "type": "sono_fase",
            "payload": {
                "fase": nova_fase.value,
                "ciclo": self.ciclo_atual,
                "total": self.total_ciclos,
                "insights": len(self.insights_gerados),
                "hifas": self.hifas_criadas
            }
        }
    
    @property
    def esta_dormindo(self) -> bool:
        return self.fase not in (FaseSono.DESPERTO, FaseSono.DESPERTANDO)
