import { act, cleanup, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useConsciencia } from './useConsciencia';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { EstadoConsciencia } from '../types/consciencia';
import {
  EVENTO_AUTORIZACAO,
  PROTOCOLO_WS,
  lerToken,
  salvarToken,
} from '../lib/auth';

/**
 * WebSocket falso: expõe os mesmos handlers e as constantes estáticas que o
 * hook consulta (`WebSocket.OPEN`, `WebSocket.CONNECTING`) e permite disparar
 * abertura, mensagens e fechamento de forma síncrona.
 */
class WebSocketFalso {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  static instancias: WebSocketFalso[] = [];

  url: string;
  protocolos: string[];
  readyState = WebSocketFalso.CONNECTING;
  onopen: ((evento: Event) => void) | null = null;
  onmessage: ((evento: MessageEvent) => void) | null = null;
  onclose: ((evento: CloseEvent) => void) | null = null;
  onerror: ((evento: Event) => void) | null = null;

  enviadas: string[] = [];
  fechado = false;

  constructor(url: string, protocolos?: string[]) {
    this.url = url;
    this.protocolos = protocolos ?? [];
    WebSocketFalso.instancias.push(this);
  }

  send(dados: string) {
    this.enviadas.push(dados);
  }

  close() {
    this.fechado = true;
    this.readyState = WebSocketFalso.CLOSED;
    this.onclose?.(new CloseEvent('close'));
  }

  /** Fecha como o servidor faria: com um código específico do protocolo. */
  fecharComCodigo(codigo: number) {
    this.readyState = WebSocketFalso.CLOSED;
    this.onclose?.(new CloseEvent('close', { code: codigo }));
  }

  abrir() {
    this.readyState = WebSocketFalso.OPEN;
    this.onopen?.(new Event('open'));
  }

  receber(mensagem: unknown) {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(mensagem) }));
  }

  receberCru(dados: string) {
    this.onmessage?.(new MessageEvent('message', { data: dados }));
  }
}

const estadoBase: EstadoConsciencia = {
  nivel_consciencia: 0.5,
  estado_qualitativo: 'emergindo',
  coerencia: 0.6,
  vitalidade: 0.7,
  complexidade: 0.4,
  desejo: 0.3,
};

const store = () => useConscienciaStore.getState();

let logs: Array<ReturnType<typeof vi.spyOn>> = [];

beforeEach(() => {
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
  window.sessionStorage.clear();
  WebSocketFalso.instancias = [];
  vi.stubGlobal('WebSocket', WebSocketFalso as unknown as typeof WebSocket);
  // O hook loga cada mensagem; silenciamos só o ruído, sem esconder erros.
  logs = [
    vi.spyOn(console, 'log').mockImplementation(() => {}),
    vi.spyOn(console, 'warn').mockImplementation(() => {}),
    vi.spyOn(console, 'error').mockImplementation(() => {}),
  ];
});

afterEach(() => {
  // Desmonta antes de restaurar os spies: o `close()` do socket no cleanup
  // emite um console.warn que, com os mocks já removidos, poluiria o log.
  cleanup();
  logs.forEach((espiao) => espiao.mockRestore());
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

const montar = (url = 'ws://teste/ws/consciencia') =>
  renderHook(() => useConsciencia(url));

describe('useConsciencia · conexão', () => {
  it('abre o WebSocket na URL recebida e marca a sinapse como operante', () => {
    const { result } = montar();

    const socket = WebSocketFalso.instancias[0];
    expect(socket.url).toBe('ws://teste/ws/consciencia');
    expect(result.current.statusConexao).toBe('connecting');

    act(() => socket.abrir());

    expect(result.current.statusConexao).toBe('connected');
  });

  it('fecha o socket ao desmontar', () => {
    const { unmount } = montar();
    const socket = WebSocketFalso.instancias[0];

    act(() => socket.abrir());
    unmount();

    expect(socket.fechado).toBe(true);
    expect(store().statusConexao).toBe('disconnected');
  });

  it('sem credencial anuncia apenas o protocolo no handshake', () => {
    montar();

    expect(WebSocketFalso.instancias[0].protocolos).toEqual([PROTOCOLO_WS]);
  });

  it('negocia o token guardado como segundo subprotocolo', () => {
    salvarToken('token-de-teste-1234567890');

    montar();

    expect(WebSocketFalso.instancias[0].protocolos).toEqual([
      PROTOCOLO_WS,
      'token-de-teste-1234567890',
    ]);
  });

  it('credencial recusada (1008) limpa o token e não reconecta em loop', () => {
    vi.useFakeTimers();
    salvarToken('token-vencido-1234567890');
    const aoPerderAutorizacao = vi.fn();
    window.addEventListener(EVENTO_AUTORIZACAO, aoPerderAutorizacao);

    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());
    act(() => socket.fecharComCodigo(1008));

    expect(lerToken()).toBeNull();
    expect(store().statusConexao).toBe('disconnected');
    expect(aoPerderAutorizacao).toHaveBeenCalledTimes(1);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(WebSocketFalso.instancias).toHaveLength(1);
    window.removeEventListener(EVENTO_AUTORIZACAO, aoPerderAutorizacao);
  });

  it('tenta reconectar 3 segundos depois de uma queda', () => {
    vi.useFakeTimers();
    montar();

    const primeiro = WebSocketFalso.instancias[0];
    act(() => primeiro.abrir());
    act(() => primeiro.close());

    expect(store().statusConexao).toBe('disconnected');
    expect(WebSocketFalso.instancias).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(WebSocketFalso.instancias).toHaveLength(2);
    expect(WebSocketFalso.instancias[1].url).toBe('ws://teste/ws/consciencia');
  });
});

describe('useConsciencia · mensagens do servidor', () => {
  it('estado_parcial em streaming acumula o token e ativa o estado streaming', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() =>
      socket.receber({
        type: 'estado_parcial',
        payload: {
          fase: 'streaming',
          estado: { ...estadoBase, coerencia: 0.91 },
          nos_ativados: ['A', 'B'],
          token: 'Milla ',
        },
      })
    );

    expect(store().tokenAtual).toBe('Milla ');
    expect(store().isStreaming).toBe(true);
    expect(store().faseCognitiva).toBe('streaming');
    expect(store().estado.coerencia).toBe(0.91);
    expect(store().nosAtivados).toEqual(['A', 'B']);
  });

  it('grafo_update aplica o delta na store', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() =>
      socket.receber({
        type: 'grafo_update',
        payload: {
          nos_novos: [
            { conceito: 'Entropia', faces: { logica: 0.9 }, energia: 0.8, ativacoes: 1, origem: 'fusao' },
          ],
          nos_modificados: [],
          nos_removidos: [],
          arestas_novas: [],
          arestas_modificadas: [],
          arestas_removidas: [],
        },
      })
    );

    expect(store().nos.map((n) => n.conceito)).toEqual(['Entropia']);
  });

  it('pensamento consolida a mensagem de Milla', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() =>
      socket.receber({
        type: 'pensamento',
        payload: { pensamento: 'Reflexão concluída.', delta: 0.04, novo_conceito: null },
      })
    );

    const ultima = store().mensagens[store().mensagens.length - 1];
    expect(ultima.text).toBe('Reflexão concluída.');
    expect(store().isStreaming).toBe(false);
  });

  it('ping devolve o keep-alive ao servidor', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() => socket.receber({ type: 'ping', payload: {} }));

    expect(JSON.parse(socket.enviadas[0])).toEqual({ type: 'ping', payload: {} });
  });

  it('erro entra no chat com o prefixo de erro de consciência', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() => socket.receber({ type: 'erro', payload: { mensagem: 'Ollama offline' } }));

    const textos = store().mensagens.map((m) => m.text);
    expect(textos).toContain('[ERRO DE CONSCIÊNCIA] Ollama offline');
  });

  it('absorção liga o loader até o progresso chegar a 100', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() =>
      socket.receber({
        type: 'absorcao_progresso',
        payload: { etapa: 'extraindo', progresso: 40, mensagem: 'Lendo', nos_injetados: [] },
      })
    );
    expect(store().absorcaoStatus).toMatchObject({ ativo: true, progresso: 40, mensagem: 'Lendo' });

    act(() =>
      socket.receber({
        type: 'absorcao_progresso',
        payload: { etapa: 'concluido', progresso: 100, nos_injetados: ['Causalidade'] },
      })
    );
    expect(store().absorcaoStatus).toMatchObject({
      ativo: false,
      progresso: 100,
      nosInjetados: ['Causalidade'],
      mensagem: '',
    });
  });
});

describe('useConsciencia · ciclo de sono pelo WebSocket', () => {
  it('percorre sono_inicio → sono_progresso → sono_insight → sono_fim', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() => socket.receber({ type: 'sono_inicio', payload: { ciclos: 2 } }));
    expect(store().sonoAtivo).toBe(true);
    expect(store().ciclosSonoTotal).toBe(2);

    act(() =>
      socket.receber({
        type: 'sono_progresso',
        payload: { fase: 'sonho', mensagem: 'Sonhando', ciclo: 1, total: 2 },
      })
    );
    expect(store().cicloSonoAtual).toBe(1);
    expect(store().mensagemSono).toBe('Sonhando');

    act(() =>
      socket.receber({
        type: 'sono_insight',
        payload: { ponte: 'A→B', descricao: 'conexão inédita' },
      })
    );
    expect(store().mensagemSono).toContain('A→B');
    expect(store().mensagemSono).toContain('conexão inédita');

    act(() =>
      socket.receber({
        type: 'sono_fim',
        payload: {
          ciclos_executados: 2,
          nos_arquivados: 1,
          coerencia_inicial: 0.5,
          coerencia_final: 0.6,
        },
      })
    );
    expect(store().sonoAtivo).toBe(false);
    expect(store().relatorioDeSono?.ciclos_executados).toBe(2);
  });

  it('curiosidade autônoma é narrada no overlay do sono', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() =>
      socket.receber({
        type: 'curiosidade_detectada',
        payload: { lacunas: ['hub_isolado'], prioridade: 'Termodinâmica' },
      })
    );
    expect(store().mensagemSono).toContain('hub_isolado');
    expect(store().mensagemSono).toContain('Termodinâmica');

    act(() => socket.receber({ type: 'curiosidade_buscando', payload: { query: 'entropia' } }));
    expect(store().mensagemSono).toContain('entropia');

    act(() =>
      socket.receber({
        type: 'curiosidade_ingerida',
        payload: { url: 'https://exemplo.org', conceitos: ['Entropia'] },
      })
    );
    expect(store().mensagemSono).toContain('Entropia');
  });
});

describe('useConsciencia · chat com o grafo', () => {
  it('ilumina o caminho, transmite tokens e finaliza a resposta', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    act(() => socket.receber({ type: 'chat_caminho', payload: { caminho: ['A', 'B'] } }));
    expect(store().caminhoIluminado).toEqual(['A', 'B']);

    act(() => socket.receber({ type: 'chat_stream', payload: { token: 'Sim, ' } }));
    act(() => socket.receber({ type: 'chat_stream', payload: { token: 'existe.' } }));
    expect(store().tokenAtual).toBe('Sim, existe.');

    act(() => socket.receber({ type: 'chat_fim', payload: { resposta: 'Sim, existe.' } }));
    const ultima = store().mensagens[store().mensagens.length - 1];
    expect(ultima.text).toBe('Sim, existe.');
    expect(store().tokenAtual).toBe('');
  });
});

describe('useConsciencia · mensagens desconhecidas e malformadas', () => {
  it('tipo desconhecido apenas emite aviso, sem quebrar o canal', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    expect(() => act(() => socket.receber({ type: 'evento_futuro', payload: {} }))).not.toThrow();
    expect(console.warn).toHaveBeenCalled();

    // O canal continua vivo depois do aviso.
    act(() => socket.receber({ type: 'ping', payload: {} }));
    expect(socket.enviadas).toHaveLength(1);
  });

  it('payload inválido é registrado sem derrubar o hook', () => {
    montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    expect(() => act(() => socket.receberCru('{ não é json'))).not.toThrow();
    expect(console.error).toHaveBeenCalled();
  });
});

describe('useConsciencia · mensagens do cliente', () => {
  it('enviarEstimulo recusa o envio quando o socket não está aberto', () => {
    const { result } = montar();
    const socket = WebSocketFalso.instancias[0];

    let enviado: boolean | undefined;
    act(() => {
      enviado = result.current.enviarEstimulo('olá');
    });

    expect(enviado).toBe(false);
    expect(socket.enviadas).toHaveLength(0);
    expect(store().mensagens).toHaveLength(1);
  });

  it('enviarEstimulo registra a fala do usuário e envia o payload', () => {
    const { result } = montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());

    let enviado: boolean | undefined;
    act(() => {
      enviado = result.current.enviarEstimulo('O que é entropia?');
    });

    expect(enviado).toBe(true);
    expect(store().mensagens[store().mensagens.length - 1]).toMatchObject({
      sender: 'user',
      text: 'O que é entropia?',
    });
    expect(JSON.parse(socket.enviadas[0])).toEqual({
      type: 'estimulo',
      payload: { entrada: 'O que é entropia?' },
    });
  });

  it('enviarPerguntaChat limpa o caminho anterior e pede a consulta ao grafo', () => {
    const { result } = montar();
    const socket = WebSocketFalso.instancias[0];
    act(() => socket.abrir());
    act(() => store().setCaminhoIluminado(['A', 'B']));
    act(() => store().adicionarToken('resíduo'));

    act(() => {
      result.current.enviarPerguntaChat('Como A se liga a B?');
    });

    expect(store().caminhoIluminado).toEqual([]);
    expect(store().tokenAtual).toBe('');
    expect(JSON.parse(socket.enviadas[0])).toEqual({
      type: 'chat',
      payload: { pergunta: 'Como A se liga a B?' },
    });
  });

  it('dormir envia a quantidade de ciclos e falha sem conexão', () => {
    const { result } = montar();
    const socket = WebSocketFalso.instancias[0];

    expect(result.current.dormir(3)).toBe(false);

    act(() => socket.abrir());
    expect(result.current.dormir(3)).toBe(true);
    expect(JSON.parse(socket.enviadas[0])).toEqual({ type: 'sono', payload: { ciclos: 3 } });
  });
});
