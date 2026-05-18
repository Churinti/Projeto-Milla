import { useEffect, useRef, useCallback } from 'react';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { WSMessage, MessageType } from '../types/consciencia';

export const useConsciencia = (url: string = `ws://${window.location.host}/ws/consciencia`) => {

  const ws = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<number | null>(null);
  const statusConexao = useConscienciaStore((state) => state.statusConexao);

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
        const { type, payload } = message as { type: MessageType; payload: any };
        const currentStore = useConscienciaStore.getState();

        switch (type) {
          case 'ping':
            socket.send(JSON.stringify({ type: 'ping', payload: {} }));
            break;

          case 'sono_inicio':
            console.log('[WS] Sono iniciado:', payload);
            currentStore.iniciarSono(payload.ciclos);
            break;

          case 'sono_progresso':
            console.log('[WS] Progresso do sono:', payload);
            currentStore.processarProgressoSono(
              payload.fase,
              payload.mensagem,
              payload.ciclo,
              payload.total
            );
            break;

          case 'sono_insight':
            console.log('[WS] Insight onírico:', payload);
            currentStore.processarProgressoSono(
              'sonho',
              `✨ Insight REM: Ponte ${payload.ponte} criada! ${payload.descricao}`
            );
            break;

          case 'curiosidade_detectada':
            console.log('[WS] Curiosidade detectada:', payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🔍 Curiosidade Ativada: Lacuna topológica detectada do tipo [${payload.lacunas.join(', ')}]. Foco em: ${payload.prioridade}`
            );
            break;

          case 'curiosidade_buscando':
            console.log('[WS] Curiosidade buscando na Web:', payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🌐 Buscando na Web: "${payload.query}" para preencher furos cognitivos...`
            );
            break;

          case 'curiosidade_ingerida':
            console.log('[WS] Curiosidade ingerida:', payload);
            currentStore.processarProgressoSono(
              'sonho',
              `🧠 Ingestão Concluída! Absorvido: ${payload.url}. Conceitos injetados: ${payload.conceitos.join(', ') || 'nenhum'}`
            );
            break;

          case 'sono_fim':
            console.log('[WS] Sono concluído:', payload);
            currentStore.finalizarSono(payload);
            break;

          case 'grafo_update':
            console.log('[WS] Delta de grafo recebido:', payload);
            currentStore.aplicarDelta(payload);
            break;

          case 'estado_parcial':
            const { fase, estado, nos_ativados, token } = payload;
            currentStore.atualizarEstadoParcial(fase, estado, nos_ativados || []);
            
            if (fase === 'streaming' && token) {
              currentStore.adicionarToken(token);
            }
            break;

          case 'absorcao_progresso':
            console.log('[WS] Progresso da absorção de conhecimento:', payload);
            currentStore.atualizarAbsorcao({
              ativo: payload.progresso < 100 && payload.etapa !== 'erro',
              etapa: payload.etapa,
              progresso: payload.progresso,
              mensagem: payload.mensagem,
              nosInjetados: payload.nos_injetados ?? []
            });
            break;

          case 'pensamento':

            console.log('[WS] Pensamento concluído recebido:', payload);
            currentStore.finalizarPensamento(payload.pensamento, payload.delta, payload.novo_conceito);
            break;

          case 'erro':
            console.error('[WS] Erro vindo de Milla:', payload.mensagem);
            currentStore.adicionarMensagem({
              id: `error-${Date.now()}`,
              sender: 'milla',
              text: `[ERRO DE CONSCIÊNCIA] ${payload.mensagem}`,
              timestamp: new Date().toISOString()
            });
            break;

          case 'chat_caminho':
            console.log('[WS] Caminho iluminado:', payload.caminho);
            currentStore.setCaminhoIluminado(payload.caminho);
            break;

          case 'chat_stream':
            currentStore.adicionarToken(payload.token);
            break;

          case 'chat_fim':
            console.log('[WS] Chat concluído.');
            currentStore.finalizarPensamento(payload.resposta, 0, null);
            // Opcional: limpar caminho iluminado após alguns segundos ou deixar no grafo
            break;

          default:
            console.warn('[WS] Tipo de mensagem desconhecido:', type);
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
          conectar();
        }, 3000);
      }
    };

    socket.onerror = (err) => {
      console.error('[WS] Erro detectado no WebSocket:', err);
      socket.close();
    };
  }, [url]);

  useEffect(() => {
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
