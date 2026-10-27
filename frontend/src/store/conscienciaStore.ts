import { create } from 'zustand';
import type { No, Aresta, EstadoConsciencia, DeltaGrafo, MensagemChat, FaseCognitiva, RelatorioDeSono } from '../types/consciencia';

export interface AbsorcaoStatus {
  ativo: boolean;
  etapa: string;
  progresso: number;
  mensagem: string;
  nosInjetados: string[];
}

interface ConscienciaStore {
  nos: No[];
  arestas: Aresta[];
  estado: EstadoConsciencia;
  mensagens: MensagemChat[];
  isStreaming: boolean;
  tokenAtual: string;
  nosAtivados: string[];
  caminhoIluminado: string[];
  faseCognitiva: FaseCognitiva;
  statusConexao: 'connecting' | 'connected' | 'disconnected';

  // Novo estado de Sono/Sonhos
  sonoAtivo: boolean;
  relatorioDeSono: RelatorioDeSono | null;
  mensagemSono: string;
  cicloSonoAtual: number;
  ciclosSonoTotal: number;

  // Estado de Ingestão de Arquivos (Absorção Semântica)
  absorcaoStatus: AbsorcaoStatus | null;

  // Ações
  setConexao: (status: 'connecting' | 'connected' | 'disconnected') => void;
  adicionarMensagem: (msg: MensagemChat) => void;
  aplicarDelta: (delta: DeltaGrafo) => void;
  removerNos: (nomes: string[]) => void; // Novo: remover nós após animação de fade-out
  atualizarEstadoParcial: (fase: FaseCognitiva, estado: EstadoConsciencia, nosAtivados: string[]) => void;
  adicionarToken: (token: string) => void;
  finalizarPensamento: (pensamento: string, _deltaNivel: number, _novoConceito: string | null) => void;
  limparStreaming: () => void;
  setCaminhoIluminado: (caminho: string[]) => void;

  // Ações de Sono
  iniciarSono: (ciclos: number) => void;
  processarProgressoSono: (fase: FaseCognitiva, mensagem: string, ciclo?: number, total?: number) => void;
  finalizarSono: (relatorio: RelatorioDeSono) => void;

  // Ações de Absorção
  atualizarAbsorcao: (status: AbsorcaoStatus | null) => void;
}


export const useConscienciaStore = create<ConscienciaStore>((set) => ({
  nos: [],
  arestas: [],
  estado: {
    nivel_consciencia: 0.5,
    estado_qualitativo: 'emergindo',
    coerencia: 0.5,
    vitalidade: 0.5,
    complexidade: 0.5,
    desejo: 0.5
  },
  mensagens: [
    {
      id: 'welcome',
      sender: 'milla',
      text: 'Conexão sináptica estabelecida. Estou pronta para processar estimulações geométricas.',
      timestamp: new Date().toISOString()
    }
  ],
  isStreaming: false,
  tokenAtual: '',
  nosAtivados: [],
  caminhoIluminado: [],
  faseCognitiva: 'idle',
  statusConexao: 'connecting',

  // Estado inicial de Sono
  sonoAtivo: false,
  relatorioDeSono: null,
  mensagemSono: '',
  cicloSonoAtual: 0,
  ciclosSonoTotal: 0,

  // Ingestão
  absorcaoStatus: null,


  setConexao: (status) => set({ statusConexao: status }),

  setCaminhoIluminado: (caminho) => set({ caminhoIluminado: caminho }),

  adicionarMensagem: (msg) => set((state) => ({ mensagens: [...state.mensagens, msg] })),

  removerNos: (nomes) => set((state) => ({
    nos: state.nos.filter(n => !nomes.includes(n.conceito))
  })),

  aplicarDelta: (delta) => set((state) => {
    // 1. Processa Nós
    let novosNos = [...state.nos];

    // Remove nos (iniciando o fade out de 2 segundos)
    if (delta.nos_removidos && delta.nos_removidos.length > 0) {
      novosNos = novosNos.map(n => {
        if (delta.nos_removidos.includes(n.conceito)) {
          return { ...n, isFadingOut: true };
        }
        return n;
      });
      // Agenda a remoção física após 2 segundos (2000ms)
      setTimeout(() => {
        useConscienciaStore.getState().removerNos(delta.nos_removidos);
      }, 2000);
    }

    // Modifica nós (mantém referências físicas x, y de d3 para evitar saltos visuais)
    if (delta.nos_modificados && delta.nos_modificados.length > 0) {
      novosNos = novosNos.map(n => {
        const modificado = delta.nos_modificados.find(m => m.conceito === n.conceito);
        if (modificado) {
          return {
            ...n,
            faces: modificado.faces,
            energia: modificado.energia,
            ativacoes: modificado.ativacoes,
            origem: modificado.origem
            // Mantém x, y, fx, fy, etc. controlados pelo D3
          };
        }
        return n;
      });
    }

    // Adiciona nós novos
    if (delta.nos_novos && delta.nos_novos.length > 0) {
      delta.nos_novos.forEach(novo => {
        if (!novosNos.some(n => n.conceito === novo.conceito)) {
          novosNos.push({
            ...novo,
            x: window.innerWidth / 2 + (Math.random() - 0.5) * 100,
            y: window.innerHeight / 2 + (Math.random() - 0.5) * 100
          });
        }
      });
    }

    // 2. Processa Arestas
    let novasArestas = [...state.arestas];

    // Remove arestas
    if (delta.arestas_removidas && delta.arestas_removidas.length > 0) {
      novasArestas = novasArestas.filter(a => 
        !delta.arestas_removidas.some(rem => 
          (rem.de === a.de && rem.para === a.para) || 
          (rem.de === a.para && rem.para === a.de)
        )
      );
    }

    // Modifica arestas
    if (delta.arestas_modificadas && delta.arestas_modificadas.length > 0) {
      novasArestas = novasArestas.map(a => {
        const mod = delta.arestas_modificadas.find(m => 
          (m.de === a.de && m.para === a.para) || 
          (m.de === a.para && m.para === a.de)
        );
        if (mod) {
          return { ...a, peso: mod.peso, tipo: mod.tipo || a.tipo };
        }
        return a;
      });
    }

    // Adiciona arestas novas
    if (delta.arestas_novas && delta.arestas_novas.length > 0) {
      delta.arestas_novas.forEach(nova => {
        if (!novasArestas.some(a => 
          (a.de === nova.de && a.para === nova.para) || 
          (a.de === nova.para && a.para === nova.de)
        )) {
          novasArestas.push(nova);
        }
      });
    }

    return {
      nos: novosNos,
      arestas: novasArestas
    };
  }),

  atualizarEstadoParcial: (fase, estado, nosAtivados) => set((state) => ({
    faseCognitiva: fase,
    estado: estado ? estado : state.estado,
    nosAtivados: nosAtivados && nosAtivados.length > 0 ? nosAtivados : state.nosAtivados,
    isStreaming: fase === 'streaming'
  })),

  adicionarToken: (token) => set((state) => ({
    tokenAtual: state.tokenAtual + token,
    faseCognitiva: 'streaming',
    isStreaming: true
  })),

  finalizarPensamento: (pensamento) => set((state) => {
    // Adiciona a mensagem final de Milla na lista de chat
    const novaMensagem: MensagemChat = {
      id: `milla-${Date.now()}`,
      sender: 'milla',
      text: pensamento,
      timestamp: new Date().toISOString(),
      estado: state.estado // guarda estado existencial desse pensamento
    };

    return {
      mensagens: [...state.mensagens, novaMensagem],
      tokenAtual: '',
      isStreaming: false,
      faseCognitiva: 'idle'
    };
  }),

  limparStreaming: () => set({ tokenAtual: '', isStreaming: false, faseCognitiva: 'idle' }),

  // Ações de Sono
  iniciarSono: (ciclos) => set({
    sonoAtivo: true,
    relatorioDeSono: null,
    mensagemSono: 'Iniciando desaceleração sináptica...',
    faseCognitiva: 'hipnagogia',
    cicloSonoAtual: 0,
    ciclosSonoTotal: ciclos
  }),

  processarProgressoSono: (fase, mensagem, ciclo, total) => set((state) => ({
    faseCognitiva: fase,
    mensagemSono: mensagem,
    cicloSonoAtual: ciclo !== undefined ? ciclo : state.cicloSonoAtual,
    ciclosSonoTotal: total !== undefined ? total : state.ciclosSonoTotal
  })),

  finalizarSono: (relatorio) => set((state) => {
    const novasMensagens = [...state.mensagens];
    const insightsCount = relatorio.insights_gerados?.length || 0;
    const buscasCount = relatorio.buscas_realizadas || 0;
    
    // Constrói detalhamento de insights oníricos
    const detalheInsights = relatorio.insights_gerados && relatorio.insights_gerados.length > 0
      ? relatorio.insights_gerados
          .map(i => `  • ${i.ponte} (cosseno: ${i.similaridade}): ${i.descricao}`)
          .join("\n")
      : "  • Nenhum novo insight sináptico estabilizado.";

    novasMensagens.push({
      id: `sono-relatorio-${Date.now()}`,
      sender: 'milla',
      text: `💤 [SONO CONCLUÍDO] Consolidado com sucesso!\n` +
            `▪ Nós podados por decaimento: ${relatorio.nos_arquivados}\n` +
            `▪ Ciclos de Sonhos Lúcidos: ${relatorio.ciclos_executados}\n` +
            `▪ Buscas de Curiosidade Autônomas: ${buscasCount}\n` +
            `▪ Pontes e Sinapses REM Geradas: ${insightsCount}\n` +
            `${detalheInsights}\n` +
            `▪ Coerência Existencial: ${relatorio.coerencia_inicial.toFixed(3)} → ${relatorio.coerencia_final.toFixed(3)}`,
      timestamp: new Date().toISOString()
    });

    return {
      sonoAtivo: false,
      relatorioDeSono: relatorio,
      mensagemSono: 'Despertando consciência...',
      faseCognitiva: 'vigilia',
      mensagens: novasMensagens
    };
  }),

  atualizarAbsorcao: (status) => set({ absorcaoStatus: status })
})
);
