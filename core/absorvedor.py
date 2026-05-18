import io
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from core.no_dodecaedrico import NoDodecaedrico

logger = logging.getLogger(__name__)

class FacesCognitivas(BaseModel):
    logica: float = Field(default=0.5, ge=0.0, le=1.0)
    emocao_simulada: float = Field(default=0.5, ge=0.0, le=1.0)
    temporalidade: float = Field(default=0.5, ge=0.0, le=1.0)
    abstracao: float = Field(default=0.5, ge=0.0, le=1.0)
    camada_origem: float = Field(default=1.0, ge=0.0, le=5.0)
    urgencia: float = Field(default=0.3, ge=0.0, le=1.0)
    certeza: float = Field(default=0.5, ge=0.0, le=1.0)
    valencia: float = Field(default=0.5, ge=0.0, le=1.0)
    novidade: float = Field(default=0.8, ge=0.0, le=1.0)
    relevancia: float = Field(default=0.5, ge=0.0, le=1.0)
    coerencia_local: float = Field(default=0.5, ge=0.0, le=1.0)
    energia_ativacao: float = Field(default=1.0, ge=0.0, le=1.0)

class ConceitoExtraido(BaseModel):
    nome: str
    descricao: str
    faces: FacesCognitivas
    relevancia: float = Field(default=0.5, ge=0.0, le=1.0)

PROMPT_DODECAEDRICO = """Você é o sistema de aprendizado cognitivo da IA Milla.
Analise o trecho abaixo e identifique conceitos fundamentais.

TRECHO:
{chunk}

INSTRUÇÃO:
Extraia de 2 a 5 conceitos abstratos, técnicos ou filosóficos presentes no texto.
Evite conceitos genéricos como "informação", "sistema", "processo", "documento".
Para cada conceito, defina seus parâmetros cognitivos dodecaédricos (valores de 0.0 a 1.0).

RESPONDA APENAS com este formato JSON, sem nenhum texto introdutório ou explicativo:
{{
  "conceitos": [
    {{
      "nome": "Nome curto do conceito",
      "descricao": "Uma frase resumida sobre o conceito neste contexto.",
      "relevancia": 0.85,
      "faces": {{
        "logica": 0.7,
        "emocao_simulada": 0.2,
        "temporalidade": 0.5,
        "abstracao": 0.9,
        "camada_origem": 2.0,
        "urgencia": 0.3,
        "certeza": 0.8,
        "valencia": 0.5,
        "novidade": 0.8,
        "relevancia": 0.7,
        "coerencia_local": 0.6,
        "energia_ativacao": 1.0
      }}
    }}
  ]
}}"""

class AbsorvedorCognitivo:
    EXTENSOES_SUPORTADAS = {".pdf", ".docx", ".txt", ".md"}
    MAX_CHARS = 50_000  # ~30 páginas de texto - limite seguro
    
    def extrair_texto(self, file_bytes: bytes, filename: str) -> str:
        """
        Extrai texto bruto do arquivo de acordo com a extensão.
        Retorna string vazia ou levanta ValueError.
        """
        extensao = Path(filename).suffix.lower()
        
        if extensao not in self.EXTENSOES_SUPORTADAS:
            raise ValueError(f"Formato não suportado: {extensao}. Use PDF, DOCX, TXT ou MD.")
        
        try:
            if extensao == ".pdf":
                return self._extrair_pdf(file_bytes)
            elif extensao == ".docx":
                return self._extrair_docx(file_bytes)
            else:  # .txt, .md
                return self._extrair_texto_plano(file_bytes)
        except Exception as e:
            logger.error(f"[Absorvedor] Falha ao extrair texto do arquivo {filename}: {e}", exc_info=True)
            raise
            
    def _extrair_pdf(self, file_bytes: bytes) -> str:
        from pypdf import PdfReader
        
        reader = PdfReader(io.BytesIO(file_bytes))
        paginas = []
        
        for i, pagina in enumerate(reader.pages):
            try:
                texto = pagina.extract_text()
                if texto and texto.strip():
                    paginas.append(texto)
                else:
                    logger.warning(f"[Absorvedor] Página {i+1} sem texto extraível (pode ser imagem)")
            except Exception as e:
                logger.warning(f"[Absorvedor] Falha ao ler página {i+1}: {e}")
                continue
                
        if not paginas:
            raise ValueError(
                "Nenhum texto extraível encontrado no PDF. "
                "O arquivo pode ser um PDF escaneado (imagem pura). "
                "Converta-o ou use um leitor OCR antes de alimentar a Milla."
            )
            
        texto_completo = "\n\n".join(paginas)
        return texto_completo[:self.MAX_CHARS]
        
    def _extrair_docx(self, file_bytes: bytes) -> str:
        from docx import Document
        
        doc = Document(io.BytesIO(file_bytes))
        paragrafos = [
            p.text.strip()
            for p in doc.paragraphs
            if p.text.strip()
        ]
        
        if not paragrafos:
            raise ValueError("O documento DOCX não possui conteúdo de texto legível.")
            
        return "\n\n".join(paragrafos)[:self.MAX_CHARS]
        
    def _extrair_texto_plano(self, file_bytes: bytes) -> str:
        # Tenta UTF-8, Latin-1 e Windows CP1252
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                texto = file_bytes.decode(encoding)
                return texto[:self.MAX_CHARS]
            except UnicodeDecodeError:
                continue
                
        raise ValueError("Não foi possível decodificar o arquivo de texto plano nos encodings comuns.")

    def quebrar_chunks(self, texto: str, tamanho: int = 1200, overlap: int = 200) -> List[str]:
        """
        Divide o texto em blocos semânticos com overlap para não perder o contexto das bordas.
        Tenta respeitar limites de parágrafo.
        """
        # Divide por parágrafos primeiro
        paragrafos = re.split(r'\n\s*\n', texto.strip())
        paragrafos = [p.strip() for p in paragrafos if len(p.strip()) > 30]
        
        chunks = []
        buffer = ""
        
        for paragrafo in paragrafos:
            if len(buffer) + len(paragrafo) <= tamanho:
                buffer += "\n\n" + paragrafo if buffer else paragrafo
            else:
                if buffer:
                    chunks.append(buffer.strip())
                    # Overlap: insere o final do buffer anterior
                    buffer = buffer[-overlap:] + "\n\n" + paragrafo
                else:
                    # Parágrafo único maior que o tamanho máximo permitido
                    chunks.append(paragrafo[:tamanho])
                    buffer = paragrafo[-overlap:]
                    
        if buffer.strip():
            chunks.append(buffer.strip())
            
        return chunks

    async def extrair_conceitos_dodecaedricos(
        self,
        chunk: str,
        nucleo_fusao
    ) -> List[dict]:
        """
        Substitui a extração por chamada única de prompt pelo Pipeline Multi-Agente.
        Mantém compatibilidade estrita de assinatura no absorvedor.
        """
        from engine.fusao_multi_agente import PipelineMultiAgente
        
        pipeline = PipelineMultiAgente(nucleo_fusao)
        resultado = await pipeline.processar_texto(chunk)
        
        return resultado["conceitos"]

    def _deduplicar(self, conceitos: List[dict]) -> List[dict]:
        """Remove redundâncias de conceitos com nomes idênticos."""
        vistos = {}
        for c in conceitos:
            nome = c["nome"].strip().lower()
            if nome and nome not in vistos:
                vistos[nome] = c
        return list(vistos.values())

    async def extrair_texto_url(self, url: str) -> str:
        """
        Extrai texto limpo de uma URL, removendo ruído estrutural.
        Prioriza conteúdo semântico sobre navegação e UI.
        """
        import httpx
        from bs4 import BeautifulSoup
        
        # Validação básica de URL
        if not url.startswith(("http://", "https://")):
            raise ValueError("URL deve começar com http:// ou https://")
        
        headers = {
            "User-Agent": "MillaBot/2.0 (IA Architecture PoC; +https://github.com/seu-repo)",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml"
        }
        
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.TimeoutException:
                raise ValueError(f"Timeout ao acessar {url}. Site muito lento ou inacessível.")
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Erro HTTP {e.response.status_code} ao acessar {url}")
            except httpx.RequestError as e:
                raise ValueError(f"Erro de conexão: {str(e)}")
        
        # Verificar se é HTML
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            raise ValueError(
                f"Tipo de conteúdo não suportado: {content_type}. "
                "Apenas páginas HTML são aceitas."
            )
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove ruído estrutural antes de extrair texto
        TAGS_RUIDO = [
            "script", "style", "nav", "header", "footer",
            "aside", "advertisement", "cookie", "banner",
            "iframe", "form", "button", "input", "select",
            "[document]", "noscript", "meta", "link"
        ]
        for tag in soup(TAGS_RUIDO):
            tag.decompose()
        
        # Remove elementos por atributos comuns de UI/nav
        CLASSES_RUIDO = [
            "nav", "menu", "sidebar", "footer", "header",
            "cookie", "banner", "ad", "advertisement",
            "related", "share", "social", "comment",
            "vector-header", "vector-menu", "mw-jump-link"
        ]
        for classe in CLASSES_RUIDO:
            for elem in soup.find_all(class_=lambda c: c and classe in (" ".join(c) if isinstance(c, list) else c).lower()):
                # Se já foi decomposto (por um pai), pula
                if getattr(elem, "attrs", None) is None:
                    continue
                    
                # Proteção essencial: não deletar a raiz ou o miolo do artigo se a classe
                # der 'match' acidental (ex: <html class="...header-enabled..."> na Wikipedia)
                if getattr(elem, "name", "") in ["html", "body", "main", "article"]:
                    continue
                    
                # Se o elemento for o próprio contêiner de conteúdo, não decompõe
                classes_elem = elem.get("class", [])
                if isinstance(classes_elem, list):
                    classes_str = " ".join(classes_elem).lower()
                else:
                    classes_str = str(classes_elem).lower()
                
                if "mw-parser-output" in classes_str or "post-content" in classes_str:
                    continue
                
                elem.decompose()
        
        # Estratégia de extração em ordem de prioridade
        texto = ""
        
        # 1. Tenta encontrar o elemento principal de conteúdo
        SELETORES_CONTEUDO = [
            "article",
            "main",
            "[role='main']",
            ".mw-parser-output", "#bodyContent",
            ".content", ".post-content", ".entry-content",
            ".article-body", ".post-body",
            "#content", "#main", "#article"
        ]
        
        for seletor in SELETORES_CONTEUDO:
            elemento = soup.select_one(seletor)
            if elemento:
                texto = elemento.get_text(separator="\n\n", strip=True)
                if len(texto) > 500:  # conteúdo substancial encontrado
                    break
        
        # 2. Fallback: extrai todos os parágrafos e headers
        if len(texto) < 500:
            elementos = soup.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"])
            partes = [e.get_text(strip=True) for e in elementos if len(e.get_text(strip=True)) > 30]
            texto = "\n\n".join(partes)
        
        # 3. Fallback total
        if len(texto) < 200:
            texto = soup.get_text(separator="\n", strip=True)
        
        if len(texto) < 100:
            raise ValueError(
                "Não foi possível extrair conteúdo textual suficiente desta URL. "
                "O site pode exigir JavaScript ou autenticação."
            )
        
        # Limpa espaços excessivos
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        texto = re.sub(r' {2,}', ' ', texto)
        
        return texto[:self.MAX_CHARS]

    def _detectar_site_problematico(self, url: str, texto_extraido: str) -> str | None:
        """
        Detecta se o site provavelmente bloqueou ou precisa de JS.
        Retorna mensagem de aviso ou None se ok.
        """
        url_lower = url.lower()
        
        # Sites conhecidos que bloqueiam scraping
        SITES_BLOQUEADOS = ["medium.com", "wsj.com", "ft.com", "economist.com"]
        for site in SITES_BLOQUEADOS:
            if site in url_lower:
                return f"⚠️ {site} pode bloquear leitura direta. Use o artigo em versão para impressão ou copie o texto manualmente."
        
        # Texto muito curto pode indicar JS-only
        if len(texto_extraido) < 300:
            return (
                "⚠️ Pouco conteúdo extraído. O site pode exigir JavaScript. "
                "Tente copiar o texto e usar a aba 'Texto Direto'."
            )
        
        return None

    async def absorver_url(
        self,
        milla,
        url: str,
        progress_callback=None,
        max_nos_grafo: int = 3
    ) -> dict:
        """Absorve conhecimento de uma URL."""
        
        if progress_callback:
            await progress_callback({
                "etapa": "fetch",
                "mensagem": f"Acessando {url}...",
                "progresso": 5
            })
        
        try:
            texto = await self.extrair_texto_url(url)
        except ValueError as e:
            if progress_callback:
                await progress_callback({
                    "etapa": "erro",
                    "mensagem": str(e),
                    "progresso": 0
                })
            return {"erro": str(e), "url": url}
        
        # Detecta problemas de extração
        aviso = self._detectar_site_problematico(url, texto)
        if aviso and progress_callback:
            await progress_callback({
                "etapa": "aviso",
                "mensagem": aviso,
                "progresso": 10
            })
        
        # Extrai nome amigável da URL para usar como "filename"
        from urllib.parse import urlparse
        parsed = urlparse(url)
        nome_origem = parsed.netloc + parsed.path.rstrip('/')
        nome_origem = nome_origem[-60:]  # limita tamanho
        
        # Reutiliza o pipeline completo
        return await self._processar_texto_absorcao(
            milla=milla,
            texto=texto,
            origem_nome=nome_origem,
            progress_callback=progress_callback,
            max_nos_grafo=max_nos_grafo
        )

    async def absorver(
        self,
        milla,
        file_bytes: bytes,
        filename: str,
        progress_callback = None,
        max_nos_grafo: int = 3
    ) -> dict:
        """
        Orquestra a pipeline de absorção conceitual a partir de um arquivo.
        """
        if progress_callback:
            await progress_callback({
                "etapa": "extracao",
                "mensagem": f"Extraindo conteúdo textual de '{filename}'...",
                "progresso": 5
            })
            
        try:
            texto = self.extrair_texto(file_bytes, filename)
        except Exception as e:
            if progress_callback:
                await progress_callback({
                    "etapa": "erro",
                    "mensagem": f"Erro de extração: {e}",
                    "progresso": 0
                })
            return {"erros": [str(e)], "filename": filename}
            
        return await self._processar_texto_absorcao(
            milla=milla,
            texto=texto,
            origem_nome=filename,
            progress_callback=progress_callback,
            max_nos_grafo=max_nos_grafo
        )

    async def _processar_texto_absorcao(
        self,
        milla,
        texto: str,
        origem_nome: str,
        progress_callback=None,
        max_nos_grafo: int = 3
    ) -> dict:
        """
        Pipeline compartilhado: chunking → ollama → grafo → subconsciente.
        Usado tanto por absorver() (arquivo) quanto absorver_url().
        """
        resultado = {
            "origem": origem_nome,
            "chunks_processados": 0,
            "total_chunks": 0,
            "todos_conceitos": [],
            "nos_injetados_no_grafo": [],
            "nos_no_subconsciente": [],
            "erros": []
        }
        
        chunks = self.quebrar_chunks(texto)
        total_chunks = len(chunks)
        resultado["total_chunks"] = total_chunks
        
        if total_chunks == 0:
            msg_erro = "Nenhum bloco de texto útil pôde ser gerado para processamento."
            resultado["erros"].append(msg_erro)
            if progress_callback:
                await progress_callback({
                    "etapa": "erro",
                    "mensagem": msg_erro,
                    "progresso": 0
                })
            return resultado
        
        if progress_callback:
            await progress_callback({
                "etapa": "chunking",
                "mensagem": f"{total_chunks} blocos semânticos identificados",
                "progresso": 15
            })
        
        todos_conceitos = []
        
        for i, chunk in enumerate(chunks):
            progresso = 15 + int((i / total_chunks) * 65)
            
            if progress_callback:
                await progress_callback({
                    "etapa": "extracao_conceitos",
                    "mensagem": f"Analisando bloco {i+1}/{total_chunks}...",
                    "progresso": progresso
                })
            
            try:
                conceitos = await self.extrair_conceitos_dodecaedricos(
                    chunk, milla.nucleo
                )
                todos_conceitos.extend(conceitos)
                resultado["chunks_processados"] += 1
            except Exception as e:
                logger.error(f"[Absorvedor] Erro no bloco {i+1}: {e}")
                resultado["erros"].append(f"Bloco {i+1}: {str(e)}")
            
            await asyncio.sleep(0)
        
        if not todos_conceitos:
            msg_erro = "A Milla leu o documento, mas não conseguiu abstrair conceitos úteis."
            resultado["erros"].append(msg_erro)
            if progress_callback:
                await progress_callback({
                    "etapa": "erro",
                    "mensagem": msg_erro,
                    "progresso": 0
                })
            return resultado
        
        # Deduplica e ordena
        todos_conceitos = self._deduplicar(todos_conceitos)
        todos_conceitos.sort(
            key=lambda c: c.get("relevancia", 0.5),
            reverse=True
        )
        resultado["todos_conceitos"] = [c["nome"] for c in todos_conceitos]
        
        if progress_callback:
            await progress_callback({
                "etapa": "integracao",
                "mensagem": f"{len(todos_conceitos)} conceitos extraídos. Integrando...",
                "progresso": 85
            })
        
        # Distribui entre grafo ativo e subconsciente
        for i, conceito_dados in enumerate(todos_conceitos):
            nome = conceito_dados.get("nome", "").strip()
            if not nome:
                continue
            
            no = NoDodecaedrico(
                conceito=nome,
                faces=conceito_dados.get("faces", {}),
                origem="absorcao"
            )
            no.historico_local.append(
                f"Absorvido de '{origem_nome}': "
                f"{conceito_dados.get('descricao', '')[:100]}"
            )
            
            if i < max_nos_grafo and nome not in milla.grafo.nodes:
                milla.instanciar_conceito(
                    conceito=nome,
                    dados_faces=conceito_dados.get("faces", {}),
                    origem="absorcao"
                )
                resultado["nos_injetados_no_grafo"].append(nome)
            else:
                milla.subconsciente.arquivar_no(no)
                resultado["nos_no_subconsciente"].append(nome)
        
        if progress_callback:
            await progress_callback({
                "etapa": "concluido",
                "mensagem": (
                    f"Absorção concluída: "
                    f"{len(resultado['nos_injetados_no_grafo'])} nós no grafo, "
                    f"{len(resultado['nos_no_subconsciente'])} no subconsciente"
                ),
                "progresso": 100,
                "nos_injetados": resultado["nos_injetados_no_grafo"]
            })
        
        return resultado
