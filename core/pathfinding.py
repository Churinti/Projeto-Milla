import networkx as nx
from typing import List, Optional

class PathfinderCognitivo:
    """Encontra caminhos de raciocínio no grafo de consciência."""
    
    def __init__(self, grafo: nx.Graph, subconsciente):
        self.grafo = grafo
        self.subconsciente = subconsciente
    
    def extrair_conceitos_da_pergunta(self, pergunta: str) -> List[str]:
        """Extrai conceitos do grafo que estão semanticamente próximos da pergunta usando ChromaDB."""
        if not self.grafo.nodes:
            return []
            
        # Usa o próprio ChromaDB para calcular similaridade cosseno automaticamente!
        # Como passamos a pergunta no query_texts, o ChromaDB a converte em embedding
        # e retorna os documentos mais próximos.
        try:
            resultados = self.subconsciente.colecao.query(
                query_texts=[pergunta],
                n_results=10, # busca os 10 mais relevantes no banco todo
                where={"schema_version": {"$eq": self.subconsciente.SCHEMA_VERSION}}
            )
            
            conceitos_encontrados = []
            if resultados and resultados.get('metadatas') and resultados['metadatas'][0]:
                for i, meta in enumerate(resultados['metadatas'][0]):
                    distancia = resultados['distances'][0][i]
                    similaridade = 1.0 - distancia
                    
                    conceito = meta.get('conceito')
                    # Filtra: deve ter similaridade > 0.4 e ESTAR NO GRAFO ATIVO
                    if similaridade > 0.4 and conceito in self.grafo.nodes:
                        conceitos_encontrados.append(conceito)
                        
            return conceitos_encontrados[:3] # Retorna no máximo os top 3
        except Exception as e:
            print(f"[Pathfinder] Erro na extração semântica: {e}")
            return []

    def encontrar_caminho(
        self,
        conceito_a: str,
        conceito_b: str,
        max_hops: int = 5
    ) -> Optional[List[str]]:
        """
        Encontra o caminho mais curto entre dois conceitos.
        Retorna lista de nomes dos nós no caminho, ou None se não houver conexão.
        """
        if conceito_a not in self.grafo.nodes or conceito_b not in self.grafo.nodes:
            return None
        if conceito_a == conceito_b:
            return [conceito_a]
        
        try:
            # Dijkstra com peso inverso da energia (nós mais energéticos = "mais curtos")
            # Mas wait, em networkx path finding, menor weight é o caminho escolhido.
            # O peso padrão da aresta já representa "distância" ou "força"?
            # Na Milla, weight = força da conexão (0.1 a 1.0). Quanto maior, MAIS FORTE.
            # Dijkstra procura o MENOR custo. Então devemos inverter o peso.
            
            grafo_inv = nx.Graph()
            for u, v, data in self.grafo.edges(data=True):
                peso = data.get('weight', 0.5)
                # Inverte o peso: conexões fortes (1.0) têm custo baixo (1.0).
                # Conexões fracas (0.1) têm custo alto (10.0).
                custo = 1.0 / (peso + 0.01)
                grafo_inv.add_edge(u, v, weight=custo)
            
            caminho = nx.shortest_path(
                grafo_inv,
                source=conceito_a,
                target=conceito_b,
                weight='weight',
                method='dijkstra'
            )
            
            # Limita hops para não trazer caminho infinito (excesso de delírio)
            if len(caminho) > max_hops + 1:
                return None
            
            return caminho
            
        # NodeNotFound: nó isolado não é copiado para grafo_inv (que só nasce
        # das arestas), então o Dijkstra nem o encontra. Sem esta captura, uma
        # pergunta sobre um conceito isolado propagava a exceção em vez de
        # responder "sem caminho".
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
            
    def extrair_contexto_caminho(self, caminho: List[str]) -> str:
        """
        Extrai metadados textuais de todos os nós e arestas do caminho.
        Retorna texto rico para o prompt do Ollama.
        """
        if not caminho:
            return ""
        
        partes = []
        for i, no_id in enumerate(caminho):
            no = self.grafo.nodes[no_id]['objeto']
            partes.append(
                f"Conceito {i+1}: {no.conceito} "
                f"(Lógica:{no.faces.get('logica',0):.2f} "
                f"| Emoção:{no.faces.get('emocao_simulada',0):.2f} "
                f"| Abstração:{no.faces.get('abstracao',0):.2f})"
            )
            
            if i < len(caminho) - 1:
                proximo = caminho[i + 1]
                peso = self.grafo[no_id][proximo].get('weight', 0.5)
                partes.append(
                    f"  → Conectado a '{proximo}' com Força Sináptica de {peso:.2f}"
                )
        
        return "\n".join(partes)
