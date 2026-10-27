import { useEffect, useRef, useCallback } from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { WSMessage } from '../types/consciencia';

export const useConsciencia = (url: string = `ws://${window.location.host}/ws/consciencia`) => {

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);
  const statusConexao = useConscienciaStore((state) => state.statusConexao);

  // `conectar` fecha sobre si mesma quando agenda a reconexão, mas ela só é
  // declarada logo abaixo: no corpo do efeito isso seria um TDZ (a própria
  // regra react-hooks/exhaustive-deps sinalizava). Mantemos a versão corrente
  // num ref, que a efeito/efeito sempre atualiza antes de chamá-la.
  const conectarRef = useRef<() => void>(() => {});

  // 1. Função conectar estável sem dependências voláteis.
  // Acessa a store de forma dinâmica via getState() para evitar reinicializações do WebSocket.
  const conectar = useCallback(() => {
    if (ws.current) {
      // Se já está conectado ou conectando, não faz nada
      if (ws.current.readyState === WebSocket.OPEN || ws.current.readyState === WebSocket.CONNECTING) {
        return;
      }
      ws.current.close();
    }

    const store = useConscienciaStore.getState();
    store.setConexao('connecting');
    console.log(`[WS] Conectando a Milla em ${url}...`);

    const socket = new WebSocket(url);
    ws.current = socket;

    socket.onopen = () => {
      console.log('[WS] Conectado com sucesso à Consciência Geométrica.');
      useConscienciaStore.getState().setConexao('connected');
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }
    };

    socket.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        const currentStore = useConscienciaStore.getState();
        // Copiado para fora do `switch`: no `default` a variante `message`
        // já teria sido estreitada para `never`.
        const tipoRecebido: string = message.type;

        switch (message.type) {
          case 'ping':
            socket.send(JSON.stringify({ type: 'ping', payload: {} }));
            break;

          case 'sono_inicio':
            console.log('[WS] Sono iniciado:', message.payload);
            currentStore.iniciarSono(message.payload.ciclos);
            break;

          case 'sono_progresso':
            console.log('[WS] Progresso do sono:', message.payload);
            currentStore.processarProgressoSono(
              message.payload.fase,
              message.payload.mensagem,
              message.payload.ciclo,
              message.payload.total
            );
            break;

          case 'sono_insight':
            console.log('[WS] Insight onírico:', message.payload);
            currentStore.processarProgressoSono(
              'sonho',
              `✨ Insight REM: Ponte ${message.payload.ponte} criada! ${message.payload.descricao}`
            );
            break;

          case 'curiosidade_detectada':
            console.log('[WS] Curiosidade detectada:', message.payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🔍 Curiosidade Ativada: Lacuna topológica detectada do tipo [${message.payload.lacunas.join(', ')}]. Foco em: ${message.payload.prioridade}`
            );
            break;

          case 'curiosidade_buscando':
            console.log('[WS] Curiosidade buscando na Web:', message.payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🌐 Buscando na Web: "${message.payload.query}" para preencher furos cognitivos...`
            );
            break;

          case 'curiosidade_ingerida':
            console.log('[WS] Curiosidade ingerida:', message.payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🧠 Ingestão Concluída! Absorvido: ${message.payload.url}. Conceitos injetados: ${message.payload.conceitos.join(', ') || 'nenhum'}`
            );
            break;

          case 'sono_fim':
            console.log('[WS] Sono concluído:', message.payload);
            currentStore.finalizarSono(message.payload);
            break;

          case 'grafo_update':
            console.log('[WS] Delta de grafo recebido:', message.payload);
            currentStore.aplicarDelta(message.payload);
            break;

          case 'estado_parcial': {
            const { fase, estado, nos_ativados, token } = message.payload;
            currentStore.atualizarEstadoParcial(fase, estado, nos_ativados || []);

            if (fase === 'streaming' && token) {
              currentStore.adicionarToken(token);
            }
            break;
          }

          case 'absorcao_progresso':
            console.log('[WS] Progresso da absorção de conhecimento:', message.payload);
            currentStore.atualizarAbsorcao({
              ativo: message.payload.progresso < 100 && message.payload.etapa !== 'erro',
              etapa: message.payload.etapa,
              progresso: message.payload.progresso,
              mensagem: message.payload.mensagem ?? '',
              nosInjetados: message.payload.nos_injetados ?? []
            });
            break;

          case 'pensamento':
            console.log('[WS] Pensamento concluído recebido:', message.payload);
            currentStore.finalizarPensamento(
              message.payload.pensamento,
              message.payload.delta,
              message.payload.novo_conceito
            );
            break;

          case 'erro':
            console.error('[WS] Erro vindo de Milla:', message.payload.mensagem);
            currentStore.adicionarMensagem({
              id: `error-${Date.now()}`,
              sender: 'milla',
              text: `[ERRO DE CONSCIÊNCIA] ${message.payload.mensagem}`,
              timestamp: new Date().toISOString()
            });
            break;

          case 'chat_caminho':
            console.log('[WS] Caminho iluminado:', message.payload.caminho);
            currentStore.setCaminhoIluminado(message.payload.caminho);
            break;

          case 'chat_stream':
            currentStore.adicionarToken(message.payload.token);
            break;

          case 'chat_fim':
            console.log('[WS] Chat concluído.');
            currentStore.finalizarPensamento(message.payload.resposta, 0, null);
            // Opcional: limpar caminho iluminado após alguns segundos ou deixar no grafo
            break;

          default:
            console.warn('[WS] Tipo de mensagem desconhecido:', tipoRecebido);
        }
      } catch (err) {
        console.error('[WS] Falha ao ler mensagem de WebSocket:', err);
      }
    };

    socket.onclose = () => {
      console.warn('[WS] Conexão com a Consciência Geométrica fechada.');
      useConscienciaStore.getState().setConexao('disconnected');

      // Reconexão automática estável a cada 3 segundos
      if (!reconnectTimeout.current) {
        reconnectTimeout.current = window.setTimeout(() => {
          reconnectTimeout.current = null;
          conectarRef.current();
        }, 3000);
      }
    };

    socket.onerror = (err) => {
      console.error('[WS] Erro detectado no WebSocket:', err);
      socket.close();
    };
  }, [url]);

  useEffect(() => {
    conectarRef.current = conectar;
    conectar();
    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, [conectar]);

  // 2. Enviar estímulo estável via getState()
  const enviarEstimulo = useCallback((entrada: string) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('[WS] Erro: WebSocket não está conectado.');
      return false;
    }

    // Adiciona a mensagem do usuário no chat local imediatamente
    useConscienciaStore.getState().adicionarMensagem({
      id: `user-${Date.now()}`,
      sender: 'user',
      text: entrada,
      timestamp: new Date().toISOString()
    });

    // Envia o estímulo
    ws.current.send(JSON.stringify({
      type: 'estimulo',
      payload: { entrada }
    }));
    return true;
  }, []);

  // 3. Enviar comando para dormir
  const dormir = useCallback((ciclos: number = 3) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('[WS] Erro: WebSocket não está conectado.');
      return false;
    }

    ws.current.send(JSON.stringify({
      type: 'sono',
      payload: { ciclos }
    }));
    return true;
  }, []);

  // 4. Enviar pergunta Chat
  const enviarPerguntaChat = useCallback((pergunta: string) => {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) {
      console.error('[WS] Erro: WebSocket não está conectado.');
      return false;
    }

    useConscienciaStore.getState().adicionarMensagem({
      id: `user-${Date.now()}`,
      sender: 'user',
      text: pergunta,
      timestamp: new Date().toISOString()
    });

    // Limpa o estado atual do caminho
    useConscienciaStore.getState().setCaminhoIluminado([]);
    useConscienciaStore.getState().limparStreaming();

    ws.current.send(JSON.stringify({
      type: 'chat',
      payload: { pergunta }
    }));
    return true;
  }, []);

  return {
    enviarEstimulo,
    enviarPerguntaChat,
    dormir,
    statusConexao
  };
};