export interface No {
  conceito: string;
  faces: Record<string, number>;
  energia: number;
  ativacoes: number;
  origem: string;
  x?: number;  // Usado por d3-force
  y?: number;  // Usado por d3-force
  fx?: number | null;
  fy?: number | null;
  isFadingOut?: boolean; // Novo: suporte a fade-out na poda
}

export interface Aresta {
  de: string;
  para: string;
  peso: number;
  tipo?: string; // normal | hifa
  source?: any; // Usado por d3-force
  target?: any; // Usado por d3-force
}

export interface EstadoConsciencia {
  nivel_consciencia: number;
  estado_qualitativo: string;
  coerencia: number;
  vitalidade: number;
  complexidade: number;
  desejo: number;
}

export interface DeltaGrafo {
  nos_novos: No[];
  nos_modificados: No[];
  nos_removidos: string[];
  arestas_novas: Aresta[];
  arestas_modificadas: Aresta[];
  arestas_removidas: Array<{ de: string; para: string }>;
}

export interface PensamentoResultado {
  pensamento: string;
  estado_antes: number;
  estado_depois: number;
  delta: number;
  evoluiu: boolean;
  novo_conceito: string | null;
  nos_no_grafo: number;
  arestas_no_grafo: number;
}

export interface RelatorioDeSono {
  ciclos_executados: number;
  nos_arquivados: number;
  insights_gerados?: Array<{ ponte: string; descricao: string; similaridade: number }>;
  buscas_realizadas?: number;
  coerencia_inicial: number;
  coerencia_final: number;
}

export interface MensagemChat {
  id: string;
  sender: 'user' | 'milla';
  text: string;
  timestamp: string;
  isStreaming?: boolean;
  isThought?: boolean;
  estado?: EstadoConsciencia;
}

export type FaseCognitiva =
  | "vigilia"
  | "hipnagogia"      // transição para sono
  | "consolidacao"    // pruning de memórias
  | "sonho"           // sonho lúcido
  | "sono_profundo"   // entre sonhos
  | "despertando"     // transição para vigília
  | "desperto"        // vigília ativa
  | "pre_pensamento"
  | "streaming"
  | "pos_pensamento"
  | "idle";

export type MessageType =
  // Core
  | "estimulo"
  | "pensamento"
  | "estado_parcial"
  | "grafo_update"
  | "ping"
  | "erro"
  
  // Absorção (arquivo e URL)
  | "absorcao_progresso"
  | "ingestao_inicio"
  | "ingestao_progresso"
  | "ingestao_fim"
  
  // Sono REM
  | "sono_inicio"
  | "sono_fase"
  | "sono_progresso"
  | "sono_insight"
  | "sono_fim"
  
  // Curiosidade autônoma
  | "curiosidade_detectada"
  | "curiosidade_buscando"
  | "curiosidade_ingerida"
  
  // Chat com Dijkstra (Fase 1)
  | "chat_caminho"
  | "chat_stream"
  | "chat_fim";

export interface WSMessage {
  type: MessageType;
  payload: unknown;
  timestamp?: string;
  iteracao?: number;
}
