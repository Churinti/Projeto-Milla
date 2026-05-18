# core/curiosidade.py — Motor de Curiosidade Autônomo e Circuit Breaker

import asyncio
import httpx
import logging
from datetime import datetime, date
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """Evita loop de falhas em buscas externas."""
    
    def __init__(self, max_falhas: int = 3, janela_minutos: int = 60):
        self.max_falhas = max_falhas
        self.janela_minutos = janela_minutos
        self._falhas: list[datetime] = []
        self._aberto = False
    
    def registrar_falha(self):
        agora = datetime.now()
        self._falhas.append(agora)
        # Limpa falhas fora da janela
        self._falhas = [
            f for f in self._falhas
            if (agora - f).total_seconds() < self.janela_minutos * 60
        ]
        if len(self._falhas) >= self.max_falhas:
            self._aberto = True
            logger.warning("[CircuitBreaker] Aberto — buscas suspensas por 1h")
    
    def registrar_sucesso(self):
        self._falhas.clear()
        self._aberto = False
    
    @property
    def bloqueado(self) -> bool:
        return self._aberto


class MotorCuriosidade:
    
    MAX_BUSCAS_POR_DIA = 5
    MAX_URLS_POR_BUSCA = 3
    MIN_NOS_PARA_CURIOSIDADE = 5  # não busca com grafo vazio
    
    def __init__(self, milla, absorvedor):
        self.milla = milla
        self.absorvedor = absorvedor
        self._buscas_hoje: int = 0
        self._data_reset: date = date.today()
        self._circuit_breaker = CircuitBreaker()
    
    def _reset_diario(self):
        """Reseta contador diário de buscas."""
        hoje = date.today()
        if hoje > self._data_reset:
            self._buscas_hoje = 0
            self._data_reset = hoje
    
    async def analisar_lacunas(self) -> list[dict]:
        """
        Detecta furos topológicos no grafo.
        Retorna lista de pares de conceitos sem conexão direta
        mas com alta energia acumulada.
        """
        import networkx as nx
        
        nos = list(self.milla.grafo.nodes)
        if len(nos) < self.MIN_NOS_PARA_CURIOSIDADE:
            return []
        
        lacunas = []
        
        # 1. Componentes desconectados com alta energia
        componentes = list(nx.connected_components(self.milla.grafo))
        if len(componentes) > 1:
            for comp_a, comp_b in zip(componentes, componentes[1:]):
                no_a = max(
                    comp_a,
                    key=lambda n: self.milla.grafo.nodes[n]['objeto'].energia_ativacao
                )
                no_b = max(
                    comp_b,
                    key=lambda n: self.milla.grafo.nodes[n]['objeto'].energia_ativacao
                )
                lacunas.append({
                    "tipo": "componentes_desconectados",
                    "no_a": no_a,
                    "no_b": no_b,
                    "prioridade": (
                        self.milla.grafo.nodes[no_a]['objeto'].energia_ativacao +
                        self.milla.grafo.nodes[no_b]['objeto'].energia_ativacao
                    )
                })
        
        # 2. Hubs de alta centralidade sem vizinhos suficientes
        centralidade = nx.degree_centrality(self.milla.grafo)
        for no_id, centr in centralidade.items():
            grau = self.milla.grafo.degree(no_id)
            energia = self.milla.grafo.nodes[no_id]['objeto'].energia_ativacao
            
            if centr > 0.4 and grau < 3 and energia > 0.6:
                # Hub importante mas pouco conectado
                lacunas.append({
                    "tipo": "hub_isolado",
                    "no_a": no_id,
                    "no_b": None,
                    "prioridade": energia * centr
                })
        
        # 3. Pares com distância >= 3 e alta energia somada
        nos_alta_energia = [
            n for n in nos
            if self.milla.grafo.nodes[n]['objeto'].energia_ativacao > 0.7
        ]
        
        for i, no_a in enumerate(nos_alta_energia):
            for no_b in nos_alta_energia[i+1:]:
                try:
                    dist = nx.shortest_path_length(
                        self.milla.grafo, no_a, no_b
                    )
                    if dist >= 3:
                        lacunas.append({
                            "tipo": "distancia_elevada",
                            "no_a": no_a,
                            "no_b": no_b,
                            "distancia": dist,
                            "prioridade": dist * (
                                self.milla.grafo.nodes[no_a]['objeto'].energia_ativacao +
                                self.milla.grafo.nodes[no_b]['objeto'].energia_ativacao
                            )
                        })
                except nx.NetworkXNoPath:
                    pass
        
        # Ordena por prioridade e retorna top 3
        lacunas.sort(key=lambda l: l['prioridade'], reverse=True)
        return lacunas[:3]
    
    def _formular_query(self, lacuna: dict) -> str:
        """Gera query de busca baseada na lacuna detectada."""
        no_a = lacuna['no_a']
        no_b = lacuna.get('no_b')
        tipo = lacuna['tipo']
        
        if tipo == "hub_isolado":
            return f"{no_a} teoria aplicações ciência"
        elif no_b:
            return f"relação entre {no_a} e {no_b} conceito científico"
        else:
            return f"{no_a} conexões interdisciplinares"
    
    async def pesquisar(
        self,
        lacuna: dict,
        progress_callback=None
    ) -> dict:
        """Pesquisa na web para preencher uma lacuna cognitiva."""
        
        self._reset_diario()
        
        # Verificações de segurança
        if self._buscas_hoje >= self.MAX_BUSCAS_POR_DIA:
            return {"status": "limite_diario_atingido"}
        
        if self._circuit_breaker.bloqueado:
            return {"status": "circuit_breaker_aberto"}
        
        query = self._formular_query(lacuna)
        
        if progress_callback:
            await progress_callback({
                "type": "curiosidade_buscando",
                "payload": {
                    "query": query,
                    "lacuna": lacuna['tipo'],
                    "conceitos": [lacuna['no_a'], lacuna.get('no_b')]
                }
            })
        
        # Busca no DuckDuckGo
        try:
            urls = await self._buscar_duckduckgo(query)
        except Exception as e:
            self._circuit_breaker.registrar_falha()
            logger.error(f"[Curiosidade] Falha na busca: {e}")
            return {"status": "erro_busca", "erro": str(e)}
        
        if not urls:
            self._circuit_breaker.registrar_falha()
            return {"status": "sem_resultados"}
        
        self._circuit_breaker.registrar_sucesso()
        self._buscas_hoje += 1
        
        # Ingere as URLs encontradas
        conceitos_absorvidos = []
        for url in urls[:self.MAX_URLS_POR_BUSCA]:
            try:
                resultado = await self.absorvedor.absorver_url(
                    milla=self.milla,
                    url=url,
                    max_nos_grafo=2  # conservador durante sono
                )
                conceitos_absorvidos.extend(
                    resultado.get("nos_injetados_no_grafo", [])
                )
                
                if progress_callback:
                    await progress_callback({
                        "type": "curiosidade_ingerida",
                        "payload": {
                            "url": url,
                            "conceitos": resultado.get("nos_injetados_no_grafo", [])
                        }
                    })
                
            except Exception as e:
                logger.warning(f"[Curiosidade] Falha ao ingerir {url}: {e}")
                continue
            
            await asyncio.sleep(1)  # respeita rate limit
        
        return {
            "status": "sucesso",
            "query": query,
            "urls_ingeridas": len(urls[:self.MAX_URLS_POR_BUSCA]),
            "conceitos_absorvidos": conceitos_absorvidos
        }
    
    async def _buscar_duckduckgo(self, query: str) -> list[str]:
        """
        Extrai URLs dos resultados do DuckDuckGo HTML.
        Sem API key necessária.
        """
        url_busca = (
            f"https://html.duckduckgo.com/html/"
            f"?q={query.replace(' ', '+')}&kl=br-pt"
        )
        
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/115.0.0.0 Safari/537.36"
            )
        }
        
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            resp = await client.get(url_busca)
            resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        urls = []
        for resultado in soup.select(".result__a"):
            href = resultado.get("href", "")
            # DuckDuckGo usa redirects — extrai URL real
            if "uddg=" in href:
                from urllib.parse import unquote, parse_qs, urlparse
                params = parse_qs(urlparse(href).query)
                url_real = params.get("uddg", [None])[0]
                if url_real:
                    url_real = unquote(url_real)
                    if url_real.startswith("http"):
                        urls.append(url_real)
        
        # Filtra domínios problemáticos
        DOMINIOS_BLOQUEADOS = [
            "reddit.com", "twitter.com", "facebook.com",
            "instagram.com", "youtube.com", "tiktok.com"
        ]
        urls_filtradas = [
            u for u in urls
            if not any(d in u for d in DOMINIOS_BLOQUEADOS)
        ]
        
        return urls_filtradas[:5]
