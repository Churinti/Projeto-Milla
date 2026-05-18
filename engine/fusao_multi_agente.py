# engine/fusao_multi_agente.py — Mixture of Memory Agents

import asyncio
import json
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Prompts dos Agentes ──────────────────────────────────────────────────

PROMPT_EXTRATOR = """
Você é um extrator cognitivo especializado.
Analise o texto abaixo e identifique TODOS os conceitos abstratos, técnicos ou filosóficos presentes.

TEXTO:
{texto}

REGRAS:
- Extraia entre 3 e 8 conceitos
- Inclua conceitos implícitos (não apenas os explicitamente nomeados)
- Cada conceito deve ser uma palavra ou expressão curta (máx 3 palavras)
- Inclua uma frase de contexto para cada conceito

RESPONDA APENAS com JSON:
{{
  "conceitos_brutos": [
    {{"nome": "...", "contexto": "..."}}
  ]
}}
"""

PROMPT_CRITICO = """
Você é um filtro analítico rigoroso.
Analise esta lista de conceitos e elimine os problemáticos.

CONCEITOS PARA AVALIAR:
{conceitos_json}

CRITÉRIOS DE ELIMINAÇÃO (elimine se qualquer um se aplicar):
1. Termo genérico demais: informação, sistema, processo, dados, tecnologia, método, conceito, ideia, aspecto, elemento, fator, componente
2. Redundante com outro conceito já na lista (mantenha apenas o mais específico)
3. Verbo ou ação disfarçada de conceito (ex: "processamento", "análise", "geração")
4. Muito curto ou vago para ter valor semântico real (ex: "coisa", "algo", "área")
5. Falso cognato ou neologismo sem significado técnico real

RESPONDA APENAS com JSON:
{{
  "conceitos_aprovados": [
    {{"nome": "...", "contexto": "...", "motivo_aprovacao": "..."}}
  ],
  "conceitos_rejeitados": [
    {{"nome": "...", "motivo_rejeicao": "..."}}
  ]
}}
"""

PROMPT_TOPOLOGICO = """
Você é um mapeador topológico dodecaédrico.
Para cada conceito aprovado, defina seus 12 parâmetros cognitivos com precisão.

CONCEITOS APROVADOS:
{conceitos_json}

DEFINIÇÃO DAS 12 FACES (valores de 0.0 a 1.0):
- logica: grau de estrutura lógica/matemática do conceito
- emocao_simulada: ressonância emocional/subjetiva
- temporalidade: dependência de tempo/evolução histórica
- abstracao: distância do concreto/físico
- urgencia: relevância para o presente imediato
- certeza: grau de consenso científico/filosófico
- valencia: valência positiva (1.0) vs negativa (0.0)
- novidade: quão recente/emergente é o conceito
- relevancia: importância para consciência e cognição
- coerencia_local: harmonia com outros conceitos do grupo
- energia_ativacao: potencial de gerar novas conexões (sempre >= 0.6)
- camada_origem: profundidade filosófica (1=superficial, 5=fundamental)

RESPONDA APENAS com JSON:
{{
  "conceitos": [
    {{
      "nome": "...",
      "descricao": "...",
      "relevancia": 0.0,
      "faces": {{
        "logica": 0.0,
        "emocao_simulada": 0.0,
        "temporalidade": 0.0,
        "abstracao": 0.0,
        "urgencia": 0.0,
        "certeza": 0.0,
        "valencia": 0.5,
        "novidade": 0.7,
        "relevancia": 0.0,
        "coerencia_local": 0.5,
        "energia_ativacao": 0.7,
        "camada_origem": 2.0
      }}
    }}
  ]
}}
"""

# ─── Classes de Agentes ───────────────────────────────────────────────────

class AgenteBase:
    """Base compartilhada entre os 3 agentes."""
    
    def __init__(self, nucleo_fusao, temperatura: float = 0.3):
        self.nucleo = nucleo_fusao
        self.temperatura = temperatura
    
    async def _chamar_llm(self, prompt: str) -> str:
        """Chamada assíncrona ao LLM configurado (Ollama ou OpenAI)."""
        messages = [
            {
                "role": "system",
                "content": "Você responde APENAS com JSON válido, sem texto antes ou depois."
            },
            {"role": "user", "content": prompt}
        ]
        
        if self.nucleo.usar_ollama:
            resposta = await asyncio.to_thread(
                lambda: self.nucleo.cliente.chat(
                    model=self.nucleo.modelo,
                    messages=messages,
                    options={"temperature": self.temperatura}
                )
            )
            return resposta['message']['content'].strip()
        else:
            resposta = await asyncio.to_thread(
                lambda: self.nucleo.cliente.chat.completions.create(
                    model=self.nucleo.modelo,
                    messages=messages,
                    temperature=self.temperatura,
                    response_format={"type": "json_object"}
                )
            )
            return resposta.choices[0].message.content.strip()
    
    def _parse_json_robusto(self, texto: str, chave_esperada: str) -> Optional[list]:
        """Parser com 3 camadas de fallback para resiliência a outputs malformados."""
        
        # Camada 1: JSON direto
        try:
            dados = json.loads(texto)
            return dados.get(chave_esperada, [])
        except json.JSONDecodeError:
            pass
        
        # Camada 2: extrai bloco JSON
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            try:
                dados = json.loads(match.group())
                return dados.get(chave_esperada, [])
            except json.JSONDecodeError:
                pass
        
        # Camada 3: extrai só os nomes de conceitos
        nomes = re.findall(r'"nome"\s*:\s*"([^"]+)"', texto)
        if nomes:
            return [{"nome": n, "contexto": ""} for n in nomes]
        
        return None


class AgenteExtrator(AgenteBase):
    """Extrai conceitos brutos do texto."""
    
    async def extrair(self, texto: str) -> list[dict]:
        prompt = PROMPT_EXTRATOR.format(texto=texto[:2000])
        
        try:
            resposta = await self._chamar_llm(prompt)
            conceitos = self._parse_json_robusto(resposta, "conceitos_brutos")
            
            if not conceitos:
                logger.warning("[AgenteExtrator] Parse falhou — usando fallback heurístico")
                return self._fallback_extracao(texto)
            
            logger.info(f"[AgenteExtrator] {len(conceitos)} conceitos extraídos")
            return conceitos
            
        except Exception as e:
            logger.error(f"[AgenteExtrator] Erro durante extração: {e}")
            return self._fallback_extracao(texto)
    
    def _fallback_extracao(self, texto: str) -> list[dict]:
        """Extração por heurística quando o LLM falha."""
        import re
        
        # Extrai substantivos capitalizados como conceitos candidatos
        palavras = re.findall(r'\b[A-ZÁÉÍÓÚÂÊÎÔÛÃÕÇ][a-záéíóúâêîôûãõç]{3,}\b', texto)
        
        # Deduplica e limita
        vistos = set()
        conceitos = []
        for p in palavras:
            if p.lower() not in vistos:
                vistos.add(p.lower())
                conceitos.append({"nome": p, "contexto": ""})
        
        return conceitos[:8]


class AgenteCritico(AgenteBase):
    """Filtra conceitos problemáticos ou redundantes."""
    
    # Lista negra expandida de termos irrelevantes, genéricos ou de baixa densidade informacional
    BLACKLIST = {
        "informacao", "sistema", "processo", "dados", "tecnologia",
        "metodo", "conceito", "ideia", "aspecto", "elemento", "fator",
        "componente", "estrutura", "modelo", "forma", "tipo", "nivel",
        "area", "campo", "dominio", "contexto", "situacao", "caso",
        "exemplo", "resultado", "efeito", "impacto", "questao", "ponto",
        "coisa", "algo", "parte", "conjunto", "grupo", "conjunto",
        "analise", "processamento", "geracao", "criacao", "desenvolvimento"
    }
    
    async def criticar(self, conceitos_brutos: list[dict]) -> list[dict]:
        if not conceitos_brutos:
            return []
        
        conceitos_json = json.dumps(conceitos_brutos, ensure_ascii=False, indent=2)
        prompt = PROMPT_CRITICO.format(conceitos_json=conceitos_json)
        
        try:
            resposta = await self._chamar_llm(prompt)
            aprovados = self._parse_json_robusto(resposta, "conceitos_aprovados")
            
            if aprovados is None:
                logger.warning("[AgenteCritico] Parse falhou — aplicando blacklist manual")
                return self._fallback_critica(conceitos_brutos)
            
            # Sempre aplica a blacklist manual como camada de segurança dupla
            aprovados_filtrados = self._aplicar_blacklist(aprovados)
            
            logger.info(
                f"[AgenteCritico] {len(conceitos_brutos)} → "
                f"{len(aprovados_filtrados)} conceitos aprovados"
            )
            return aprovados_filtrados
            
        except Exception as e:
            logger.error(f"[AgenteCritico] Erro durante crítica: {e}")
            return self._fallback_critica(conceitos_brutos)
    
    def _aplicar_blacklist(self, conceitos: list[dict]) -> list[dict]:
        """Filtra conceitos de acordo com a blacklist e o tamanho mínimo do nome."""
        return [
            c for c in conceitos
            if c.get('nome', '').lower().strip() not in self.BLACKLIST
            and len(c.get('nome', '').strip()) > 2
        ]
    
    def _fallback_critica(self, conceitos: list[dict]) -> list[dict]:
        """Filtra puramente pela blacklist estática se a chamada do LLM falhar."""
        return self._aplicar_blacklist(conceitos)


class AgenteTopologico(AgenteBase):
    """Mapeia os conceitos aprovados para suas 12 faces dodecaédricas cognitivas."""
    
    FACES_PADRAO = {
        "logica": 0.5, "emocao_simulada": 0.5,
        "temporalidade": 0.5, "abstracao": 0.5,
        "urgencia": 0.3, "certeza": 0.5,
        "valencia": 0.5, "novidade": 0.8,
        "relevancia": 0.5, "coerencia_local": 0.5,
        "energia_ativacao": 0.7, "camada_origem": 2.0
    }
    
    async def topologizar(self, conceitos_aprovados: list[dict]) -> list[dict]:
        if not conceitos_aprovados:
            return []
        
        conceitos_json = json.dumps(conceitos_aprovados, ensure_ascii=False, indent=2)
        prompt = PROMPT_TOPOLOGICO.format(conceitos_json=conceitos_json)
        
        try:
            resposta = await self._chamar_llm(prompt)
            conceitos = self._parse_json_robusto(resposta, "conceitos")
            
            if not conceitos:
                logger.warning("[AgenteTopologico] Parse falhou — usando faces dodecaédricas padrão")
                return self._fallback_topologia(conceitos_aprovados)
            
            # Valida e completa faces faltantes em cada conceito retornado
            conceitos_validados = [
                self._validar_faces(c) for c in conceitos
            ]
            
            logger.info(f"[AgenteTopologico] {len(conceitos_validados)} conceitos topologizados")
            return conceitos_validados
            
        except Exception as e:
            logger.error(f"[AgenteTopologico] Erro durante mapeamento topológico: {e}")
            return self._fallback_topologia(conceitos_aprovados)
    
    def _validar_faces(self, conceito: dict) -> dict:
        """Garante que todas as 12 faces existam com valores válidos no range [0.0, 1.0]."""
        faces = conceito.get('faces', {})
        
        for face, valor_padrao in self.FACES_PADRAO.items():
            if face not in faces:
                faces[face] = valor_padrao
            else:
                # Garante range [0.0, 1.0] exceto camada_origem (profundidade)
                if face != 'camada_origem':
                    try:
                        faces[face] = max(0.0, min(1.0, float(faces[face])))
                    except (ValueError, TypeError):
                        faces[face] = valor_padrao
                else:
                    try:
                        faces[face] = max(1.0, min(5.0, float(faces[face])))
                    except (ValueError, TypeError):
                        faces[face] = valor_padrao
        
        conceito['faces'] = faces
        
        # Garante estrutura do conceito
        if 'descricao' not in conceito:
            conceito['descricao'] = conceito.get('contexto', 'Conceito extraído.')
        if 'relevancia' not in conceito:
            conceito['relevancia'] = 0.5
            
        return conceito
    
    def _fallback_topologia(self, conceitos: list[dict]) -> list[dict]:
        """Aplica faces padrão nos conceitos aprovados caso o LLM falhe de todo."""
        return [
            {
                "nome": c.get('nome', '').strip(),
                "descricao": c.get('contexto', 'Extraído via pipeline multi-agente.'),
                "relevancia": 0.5,
                "faces": self.FACES_PADRAO.copy()
            }
            for c in conceitos
            if c.get('nome', '').strip()
        ]


class PipelineMultiAgente:
    """Orquestra os 3 agentes em sequência (Extrator → Crítico → Topológico)."""
    
    def __init__(self, nucleo_fusao):
        self.extrator   = AgenteExtrator(nucleo_fusao, temperatura=0.4)
        self.critico    = AgenteCritico(nucleo_fusao, temperatura=0.2)
        self.topologico = AgenteTopologico(nucleo_fusao, temperatura=0.2)
    
    async def processar_texto(self, texto: str) -> dict:
        """
        Pipeline completo: texto bruto → conceitos topologizados.
        Retorna dicionário com conceitos dodecaédricos finais e métricas de descarte.
        """
        resultado = {
            "conceitos": [],
            "metricas": {
                "extraidos": 0,
                "aprovados": 0,
                "topologizados": 0,
                "taxa_aprovacao": 0.0
            }
        }
        
        # Etapa 1: Extração de Ideias
        conceitos_brutos = await self.extrator.extrair(texto)
        resultado["metricas"]["extraidos"] = len(conceitos_brutos)
        
        if not conceitos_brutos:
            logger.warning("[Pipeline] Nenhum conceito extraído na Etapa 1")
            return resultado
        
        # Etapa 2: Crítica de Qualidade e Eliminação de Hallucinações
        conceitos_aprovados = await self.critico.criticar(conceitos_brutos)
        resultado["metricas"]["aprovados"] = len(conceitos_aprovados)
        
        if not conceitos_aprovados:
            logger.warning("[Pipeline] Todos os conceitos foram rejeitados na Etapa 2")
            return resultado
        
        # Etapa 3: Mapeamento de Topologia Dodecaédrica
        conceitos_finais = await self.topologico.topologizar(conceitos_aprovados)
        resultado["metricas"]["topologizados"] = len(conceitos_finais)
        
        # Consolidação de métricas
        if resultado["metricas"]["extraidos"] > 0:
            resultado["metricas"]["taxa_aprovacao"] = round(
                resultado["metricas"]["aprovados"] /
                resultado["metricas"]["extraidos"],
                2
            )
        
        resultado["conceitos"] = conceitos_finais
        
        logger.info(
            f"[Pipeline] Concluído: {resultado['metricas']['extraidos']} extraídos → "
            f"{resultado['metricas']['aprovados']} aprovados → "
            f"{resultado['metricas']['topologizados']} topologizados."
        )
        
        return resultado
