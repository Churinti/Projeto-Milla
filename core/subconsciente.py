import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from core.no_dodecaedrico import NoDodecaedrico

class SubconscienteMilla:
    """
    Sistema de Memória de Longo Prazo Associativa para o Projeto Milla.
    
    Implementa dois tipos de memória coexistentes:
    1. Memória Semântica (ChromaDB + nomic-embed-text): "o que esse conceito significa contextualmente"
    2. Memória Geométrica (vetor de 12 faces cognitivas): "como esse conceito se encaixa na estrutura de ser"
    
    O recall semântico evoca o conceito de volta do subconsciente.
    A re-instanciação no Grafo reativa a assinatura geométrica original das faces.
    """
    
    SCHEMA_VERSION = "3.0"  # incrementar quando mudar estrutura do nó
    
    def __init__(self, pasta: str = "chroma_data_milla"):
        import chromadb
        self.cliente = chromadb.PersistentClient(path=pasta)
        self.colecao = self.cliente.get_or_create_collection(
            name="subconsciente_milla",
            metadata={"hnsw:space": "cosine"}
        )
    
    def _construir_documento(self, no: NoDodecaedrico) -> str:
        """Texto rico para embedding semântico."""
        return (
            f"Conceito: {no.conceito}. "
            f"Origem: {no.origem}. "
            f"Ativações: {no.frequencia_ativacao}. "
            f"Lógica: {no.faces.get('logica', 0.5):.2f}. "
            f"Abstração: {no.faces.get('abstracao', 0.5):.2f}. "
            f"Contexto: {' | '.join(no.historico_local[-3:]) if no.historico_local else 'Nenhum'}"
        )
    
    def arquivar_no(self, no: NoDodecaedrico, afinidades: Optional[List[str]] = None):
        """
        Arquiva um nó dodecaédrico no subconsciente.
        Salva tanto a representação semântica quanto a geometria completa das faces e afinidades.
        """
        documento = self._construir_documento(no)
        id_unico = f"{no.conceito}_{self.SCHEMA_VERSION}"
        
        metadata = {
            "conceito":         no.conceito,
            "schema_version":   self.SCHEMA_VERSION,
            "origem":           no.origem,
            "energia_original": float(no.energia_ativacao),
            "frequencia":       int(no.frequencia_ativacao),
            "arquivado_em":     datetime.now().isoformat(),
            "faces_json":       json.dumps(no.faces)  # Geometria do dodecaedro 100% preservada
        }
        if afinidades is not None:
            metadata["afinidades_json"] = json.dumps(afinidades)
            
        self.colecao.upsert(  # upsert previne duplicidade de IDs de nós
            ids=[id_unico],
            documents=[documento],
            metadatas=[metadata]
        )
        print(f"[Subconsciente] Conceito '{no.conceito}' arquivado com sucesso (Schema v{self.SCHEMA_VERSION}).")
    
    def evocar_semantica(
        self,
        estimulo: str,
        n_resultados: int = 3,
        energia_minima: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Busca conceitos arquivados no subconsciente por afinidade semântica (cosseno).
        Filtra conceitos que decaíram excessivamente ou pertencem a outras versões de schema.
        """
        try:
            resultados = self.colecao.query(
                query_texts=[estimulo],
                n_results=n_resultados,
                where={
                    "$and": [
                        {"energia_original": {"$gte": float(energia_minima)}},
                        {"schema_version": {"$eq": self.SCHEMA_VERSION}}
                    ]
                }
            )
            
            evocados = []
            if not resultados or not resultados.get('metadatas') or not resultados['metadatas'][0]:
                return evocados
                
            for i, meta in enumerate(resultados['metadatas'][0]):
                distancia = resultados['distances'][0][i]
                similaridade = 1.0 - distancia  # Distância cosseno para similaridade
                
                # Threshold de relevância semântica (0.45 de similaridade cosseno)
                if similaridade > 0.45:
                    try:
                        faces = json.loads(meta['faces_json'])
                        afinidades = json.loads(meta.get('afinidades_json', '[]'))
                    except (json.JSONDecodeError, KeyError):
                        continue  # schema corrompido — pula silenciosamente
                        
                    evocados.append({
                        "conceito":         meta['conceito'],
                        "faces":            faces,
                        "origem":           "subconsciente",
                        "similaridade":     round(similaridade, 3),
                        "energia_original": meta['energia_original'],
                        "afinidades":       afinidades
                    })
            return evocados
        except Exception as e:
            print(f"[Subconsciente] Falha ao evocar memórias: {e}")
            return []
