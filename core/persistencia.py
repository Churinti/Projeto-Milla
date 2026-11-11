"""
core/persistencia.py — Snapshot do grafo ativo sem serializar a cada ciclo

O grafo da Milla muda a cada estímulo: energia, ativações, poda, novos
conceitos e hifas. Serializar tudo a cada ciclo custa caro e escreve em disco o
tempo todo; não persistir perde a consciência quando o processo termina.

A solução aqui é um snapshot **coalescido**:

- quem mexeu no grafo chama `marcar_sujo()` — barato, só liga um booleano;
- `talvez_salvar()` olha o relógio e só serializa quando o intervalo passou
  (padrão de `config.PERSISTENCIA_INTERVALO`), então várias iterações viram
  uma única escrita;
- `salvar_agora()` força o flush (desligamento gracioso);
- a escrita é **atômica** (arquivo temporário + `os.replace`): um crash no meio
  nunca deixa o JSON truncado, e o snapshot anterior continua íntegro.

O formato é o mesmo já usado por `exportar_grafo()` (que agora delega para
`serializar_grafo`), então snapshots antigos e exportações para Gephi/Cytoscape
continuam legíveis.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from core.no_dodecaedrico import NoDodecaedrico
import config

logger = logging.getLogger(__name__)

# Versão do formato do snapshot. 2 acrescenta `tipo` nas arestas e a marca
# `versao`; arquivos 1 (exportações antigas) são lidos sem problema.
FORMATO_VERSAO = 2

SUFIXO_TEMPORARIO = ".tmp"


# ─── Serialização ─────────────────────────────────────────────────────────────

def serializar_grafo(grafo) -> dict:
    """Converte o grafo ativo no dicionário que vai para o disco."""
    return {
        "versao": FORMATO_VERSAO,
        "nos": {
            nome: {
                "faces": {face: float(valor) for face, valor in dados["objeto"].faces.items()},
                "energia": float(dados["objeto"].energia_ativacao),
                "ativacoes": int(dados["objeto"].frequencia_ativacao),
                "origem": str(dados["objeto"].origem),
                "criado_em": dados["objeto"].criado_em.isoformat(),
                "ultima_ativacao": (
                    dados["objeto"].ultima_ativacao.isoformat()
                    if dados["objeto"].ultima_ativacao
                    else None
                ),
            }
            for nome, dados in grafo.nodes(data=True)
        },
        "arestas": [
            {
                "de": u,
                "para": v,
                "peso": float(dados.get("weight", 0.5)),
                "tipo": str(dados.get("tipo", "normal")),
            }
            for u, v, dados in grafo.edges(data=True)
        ],
    }


def _data(valor) -> datetime | None:
    """Converte ISO-8601 de volta para datetime, ignorando lixo."""
    if not isinstance(valor, str):
        return None
    try:
        return datetime.fromisoformat(valor)
    except ValueError:
        return None


def _numero(valor, padrao: float) -> float:
    """Aceita só números de verdade (JSON pode trazer strings e null)."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return padrao
    return float(valor)


def aplicar_snapshot(grafo, dados: dict) -> dict:
    """
    Reconstrói o grafo a partir do snapshot, substituindo o conteúdo atual.

    Entradas inválidas (nó que não é dicionário, aresta apontando para nó
    inexistente) são ignoradas em vez de derrubar a inicialização: um snapshot
    parcial ainda vale mais do que começar do zero.
    """
    nos = dados.get("nos") or {}
    arestas = dados.get("arestas") or []

    grafo.clear()

    for nome, info in nos.items():
        if not isinstance(info, dict):
            continue

        faces = {
            face: _numero(valor, 0.5)
            for face, valor in (info.get("faces") or {}).items()
        }
        no = NoDodecaedrico(
            conceito=nome,
            faces=faces,
            origem=str(info.get("origem", "semente")),
        )

        no.energia_ativacao = _numero(info.get("energia"), no.energia_ativacao)
        no.faces["energia_ativacao"] = no.energia_ativacao
        no.frequencia_ativacao = int(_numero(info.get("ativacoes"), 0))
        no.criado_em = _data(info.get("criado_em")) or no.criado_em
        no.ultima_ativacao = _data(info.get("ultima_ativacao"))

        grafo.add_node(nome, objeto=no)

    for aresta in arestas:
        if not isinstance(aresta, dict):
            continue
        origem, destino = aresta.get("de"), aresta.get("para")
        if origem not in grafo or destino not in grafo or origem == destino:
            continue
        grafo.add_edge(
            origem,
            destino,
            weight=_numero(aresta.get("peso"), 0.5),
            tipo=str(aresta.get("tipo", "normal")),
        )

    return {"nos": grafo.number_of_nodes(), "arestas": grafo.number_of_edges()}


# ─── Disco ────────────────────────────────────────────────────────────────────

def salvar_json_atomico(dados: dict, caminho: str | Path) -> Path:
    """
    Grava o JSON de forma atômica: escreve ao lado, sincroniza e troca.

    `os.replace` é atômico no mesmo sistema de arquivos, então leitores nunca
    veem um arquivo pela metade — ou o snapshot antigo, ou o novo.
    """
    caminho = Path(caminho)
    if caminho.parent and not caminho.parent.exists():
        caminho.parent.mkdir(parents=True, exist_ok=True)

    temporario = caminho.with_name(caminho.name + SUFIXO_TEMPORARIO)
    try:
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, indent=2, ensure_ascii=False)
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        # Se a escrita falhou (disco cheio, permissão), não deixa lixo.
        if temporario.exists():
            temporario.unlink(missing_ok=True)
    return caminho


def carregar_snapshot(caminho: str | Path) -> dict | None:
    """
    Lê o snapshot do disco. Ausente, ilegível, corrompido ou vazio → None.

    O chamador então semeia o grafo do zero; nunca levantamos exceção por causa
    de um arquivo estragado.
    """
    caminho = Path(caminho)
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as erro:
        logger.warning("[Persistência] Snapshot '%s' ignorado: %s", caminho, erro)
        return None

    if not isinstance(dados, dict):
        logger.warning("[Persistência] Snapshot '%s' não é um objeto JSON.", caminho)
        return None
    if not isinstance(dados.get("nos"), dict) or not dados["nos"]:
        logger.warning("[Persistência] Snapshot '%s' está sem nós; ignorado.", caminho)
        return None
    return dados


# ─── Gerenciador com coalescência ────────────────────────────────────────────

class PersistenciaGrafo:
    """
    Persiste o grafo com coalescência por intervalo.

    Não serializa nada até alguém marcar o estado como sujo e chamar
    `talvez_salvar()` depois do intervalo — é isso que evita uma escrita por
    ciclo cognitivo.
    """

    def __init__(
        self,
        grafo,
        caminho: str | Path = config.ARQUIVO_GRAFO,
        intervalo: float = config.PERSISTENCIA_INTERVALO,
        relogio=time.monotonic,
    ):
        self.grafo = grafo
        self.caminho = Path(caminho)
        self.intervalo = max(0.0, float(intervalo))
        self._relogio = relogio
        self._sujo = False
        # 0.0 é sentinela: o primeiro flush nunca espera o intervalo.
        self._ultimo_salvamento = 0.0
        self.salvamentos = 0

    @property
    def sujo(self) -> bool:
        return self._sujo

    def marcar_sujo(self) -> None:
        """Registra que o grafo mudou. Não toca no disco."""
        self._sujo = True

    def talvez_salvar(self) -> bool:
        """Salva se houver mudanças e o intervalo desde o último flush passou."""
        if not self._sujo:
            return False
        agora = self._relogio()
        if self._ultimo_salvamento and agora - self._ultimo_salvamento < self.intervalo:
            return False
        self.salvar_agora()
        return True

    def salvar_agora(self) -> Path | None:
        """Força a escrita do snapshot pendente (desligamento, testes)."""
        if not self._sujo:
            return None

        caminho = salvar_json_atomico(serializar_grafo(self.grafo), self.caminho)
        self._sujo = False
        self._ultimo_salvamento = self._relogio()
        self.salvamentos += 1
        logger.info(
            "[Persistência] Grafo salvo em '%s' (%d nós, %d arestas).",
            caminho,
            self.grafo.number_of_nodes(),
            self.grafo.number_of_edges(),
        )
        return caminho

    def carregar(self) -> bool:
        """Restaura o grafo do disco. True quando havia snapshot válido."""
        dados = carregar_snapshot(self.caminho)
        if dados is None:
            return False

        contagem = aplicar_snapshot(self.grafo, dados)
        # O disco já tem este estado: não nasce sujo.
        self._sujo = False
        self._ultimo_salvamento = self._relogio()
        logger.info(
            "[Persistência] Grafo restaurado de '%s' (%d nós, %d arestas, formato v%s).",
            self.caminho,
            contagem["nos"],
            contagem["arestas"],
            dados.get("versao", 1),
        )
        return True
