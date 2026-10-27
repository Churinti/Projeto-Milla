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
  fadeStartTime?: number; // Carimbo de tempo da animação de fade-out (só a UI lê/escreve)
}

export interface Aresta {
  de: string;
  para: string;
  peso: number;
  tipo?: string; // normal | hifa
  // O d3-force resolve estes campos: `string` antes da resolução, o próprio nó depois.
  source?: string | No;
  target?: string | No;
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

/** Campos comuns a toda mensagem do WebSocket. */
interface EnvelopeWS {
  timestamp?: string;
  iteracao?: number;
}

/**
 * Mensagem do WebSocket, discriminada por `type`.
 *
 * Cada variante declara exatamente os campos que o backend envia naquele tipo,
 * o que permite ao `switch` do consumidor verificar os tipos de cada payload
 * sem recorrer a `any`. Payloads agrupados (ex.: `absorcao_progresso` e as
 * `ingestao_*`) compartilham o mesmo formato porque vêm do mesmo pipeline.
 */
export type WSMessage = EnvelopeWS & (
  // ── Core ────────────────────────────────────────────────────────────────
  | { type: 'ping'; payload?: Record<string, never> }
  | { type: 'estimulo'; payload: { entrada: string } }
  | { type: 'estado_parcial'; payload: { fase: FaseCognitiva; estado: EstadoConsciencia; nos_ativados?: string[]; token?: string } }
  | { type: 'grafo_update'; payload: DeltaGrafo }
  | { type: 'pensamento'; payload: { pensamento: string; delta: number; novo_conceito: string | null } }
  | { type: 'erro'; payload: { mensagem: string } }

  // ── Absorção de arquivos e URLs ─────────────────────────────────────────
  | { type: 'absorcao_progresso' | 'ingestao_inicio' | 'ingestao_progresso' | 'ingestao_fim'
      payload: { etapa: string; progresso: number; mensagem?: string; nos_injetados?: string[] } }

  // ── Sono REM ────────────────────────────────────────────────────────────
  | { type: 'sono_inicio'; payload: { ciclos: number } }
  | { type: 'sono_fase'; payload: { fase: FaseCognitiva } }
  | { type: 'sono_progresso'; payload: { fase: FaseCognitiva; mensagem: string; ciclo?: number; total?: number } }
  | { type: 'sono_insight'; payload: { ponte: string; descricao: string } }
  | { type: 'sono_fim'; payload: RelatorioDeSono }

  // ── Curiosidade autônoma ────────────────────────────────────────────────
  | { type: 'curiosidade_detectada'; payload: { lacunas: string[]; prioridade: string } }
  | { type: 'curiosidade_buscando'; payload: { query: string } }
  | { type: 'curiosidade_ingerida'; payload: { url: string; conceitos: string[] } }

  // ── Chat com Dijkstra (Fase 1) ──────────────────────────────────────────
  | { type: 'chat_caminho'; payload: { caminho: string[] } }
  | { type: 'chat_stream'; payload: { token: string } }
  | { type: 'chat_fim'; payload: { resposta: string } }
);
