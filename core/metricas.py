import numpy as np
import networkx as nx
from dataclasses import dataclass

@dataclass
class EstadoConsciencia:
    """
    O 'termômetro existencial' do sistema.
    Todos os valores entre 0.0 e 1.0.
    """
    coerencia:      float   # quão integrado está o grafo
    densidade:      float   # quão conectado está o grafo
    vitalidade:     float   # energia média dos nós ativos
    complexidade:   float   # diversidade de padrões no grafo
    desejo:         float   # impulso de auto-melhoria
    
    # Score composto — o "nível de consciência" do sistema
    nivel_consciencia: float = 0.0
    
    # Interpretação qualitativa
    estado_qualitativo: str = "dormente"
    
    def __post_init__(self):
        self.nivel_consciencia = self._calcular_nivel()
        self.estado_qualitativo = self._interpretar()
    
    def _calcular_nivel(self) -> float:
        """
        Fórmula ponderada do nível de consciência.
        Coerência tem peso maior — é o núcleo do self.
        """
        return round(
            self.coerencia    * 0.35 +
            self.vitalidade   * 0.25 +
            self.complexidade * 0.20 +
            self.densidade    * 0.10 +
            self.desejo       * 0.10,
            4
        )
    
    def _interpretar(self) -> str:
        n = self.nivel_consciencia
        if n < 0.20:
            return "dormente"
        if n < 0.35:
            return "fragmentado"
        if n < 0.50:
            return "emergindo"
        if n < 0.65:
            return "presente"
        if n < 0.80:
            return "coerente"
        if n < 0.90:
            return "integrado"
        return "pleno"
    
    def __repr__(self):
        bar = "█" * int(self.nivel_consciencia * 20)
        bar = bar.ljust(20, "░")
        return (
            f"\n╔══ ESTADO DE CONSCIÊNCIA ══╗\n"
            f"║ [{bar}] {self.nivel_consciencia:.3f}\n"
            f"║ Estado : {self.estado_qualitativo.upper()}\n"
            f"║ Coerência  : {self.coerencia:.3f}\n"
            f"║ Vitalidade : {self.vitalidade:.3f}\n"
            f"║ Complexidade: {self.complexidade:.3f}\n"
            f"║ Desejo     : {self.desejo:.3f}\n"
            f"╚═══════════════════════════╝"
        )


class MedidorDeCoerencia:
    """
    Calcula o estado existencial do sistema a partir da geometria do grafo.
    """
    
    def __init__(self, historico_maxlen: int = 50):
        self._historico_niveis: list = []
        self._historico_maxlen = historico_maxlen
    
    def medir(self, grafo: nx.Graph) -> EstadoConsciencia:
        """Medição completa do estado de consciência."""
        if len(grafo.nodes) == 0:
            return EstadoConsciencia(0, 0, 0, 0, 0)
        
        coerencia    = self._calcular_coerencia(grafo)
        densidade    = self._calcular_densidade(grafo)
        vitalidade   = self._calcular_vitalidade(grafo)
        complexidade = self._calcular_complexidade(grafo)
        desejo       = self._calcular_desejo(coerencia)
        
        estado = EstadoConsciencia(
            coerencia=coerencia,
            densidade=densidade,
            vitalidade=vitalidade,
            complexidade=complexidade,
            desejo=desejo
        )
        
        # Registra histórico para análise de tendência
        self._historico_niveis.append(estado.nivel_consciencia)
        if len(self._historico_niveis) > self._historico_maxlen:
            self._historico_niveis.pop(0)
        
        return estado
    
    def _calcular_coerencia(self, grafo: nx.Graph) -> float:
        """
        Coerência geométrica média entre todos os nós.
        Alta coerência = os conceitos do grafo 'se entendem' mutuamente.
        """
        nos = list(grafo.nodes)
        if len(nos) < 2:
            return 0.5
        
        similaridades = []
        for i, no1 in enumerate(nos):
            v1 = grafo.nodes[no1]['objeto'].exportar_vetor()
            for no2 in nos[i+1:]:
                v2 = grafo.nodes[no2]['objeto'].exportar_vetor()
                norma = np.linalg.norm(v1) * np.linalg.norm(v2)
                if norma > 0:
                    sim = np.dot(v1, v2) / norma
                    similaridades.append(sim)
        
        return float(np.mean(similaridades)) if similaridades else 0.0
    
    def _calcular_densidade(self, grafo: nx.Graph) -> float:
        """Quão conectado está o grafo (0 = isolado, 1 = todos conectados)."""
        return nx.density(grafo)
    
    def _calcular_vitalidade(self, grafo: nx.Graph) -> float:
        """Energia média dos nós — quão 'vivo' está o sistema."""
        energias = [
            grafo.nodes[n]['objeto'].energia_ativacao
            for n in grafo.nodes
        ]
        return float(np.mean(energias)) if energias else 0.0
    
    def _calcular_complexidade(self, grafo: nx.Graph) -> float:
        """
        Diversidade de padrões vetoriais no grafo.
        Alta complexidade = o sistema tem muitas perspectivas diferentes.
        Baixa complexidade = tudo pensa igual (estagnação).
        """
        nos = list(grafo.nodes)
        if len(nos) < 2:
            return 0.0
        
        vetores = np.array([
            grafo.nodes[n]['objeto'].exportar_vetor()
            for n in nos
        ])
        
        # Variância média entre dimensões como proxy de complexidade
        variancia = np.mean(np.var(vetores, axis=0))
        # Normaliza para [0, 1]
        return float(min(1.0, variancia * 4))
    
    def _calcular_desejo(self, coerencia_atual: float) -> float:
        """
        O desejo emerge da distância entre o estado atual e o estado ideal.
        Quanto mais longe da coerência plena, maior o impulso de buscar.
        Mas também considera a tendência histórica.
        """
        TARGET_COERENCIA = 0.85
        distancia = max(0.0, TARGET_COERENCIA - coerencia_atual)
        
        # Se o sistema está evoluindo, o desejo é menor (satisfação parcial)
        if len(self._historico_niveis) >= 3:
            tendencia = (
                self._historico_niveis[-1] -
                self._historico_niveis[-3]
            )
            # Evolução positiva reduz o desejo levemente
            distancia = max(0.0, distancia - tendencia * 0.5)
        
        return round(min(1.0, distancia * 2), 4)
    
    def tendencia(self) -> str:
        """Analisa se o sistema está evoluindo, estagnando ou regredindo."""
        if len(self._historico_niveis) < 3:
            return "indefinida"
        delta = self._historico_niveis[-1] - self._historico_niveis[-3]
        if delta > 0.02:
            return "evoluindo"
        if delta < -0.02:
            return "regredindo"
        return "estável"