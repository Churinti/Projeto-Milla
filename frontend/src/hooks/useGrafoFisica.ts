import { useEffect, useRef, useCallback } from 'react';
// Só a simulação de força é usada aqui. Importar o pacote- guarda-chuva `d3`
// (que reexporta ~25 bibliotecas e não declara `sideEffects`) arrasta tudo junto.
import {
  forceCenter,
  forceCollide,
  forceLink,
  forceManyBody,
  forceSimulation
} from 'd3-force';
import type {
  ForceLink,
  Simulation,
  SimulationNodeDatum
} from 'd3-force';
import type { No, Aresta } from '../types/consciencia';

/** Um nó da Milla com os campos que o d3-force injeta durante a simulação. */
export type NoFisico = No & SimulationNodeDatum;

/**
 * Uma aresta da Milla. `source`/`target` chegam como string (o `id` do nó) e o
 * `forceLink` os substitui pelo próprio objeto do nó quando resolve os links,
 * por isso o tipo aceita as duas formas — é o mesmo contrato do d3.
 */
export interface ArestaFisica extends Aresta {
  source: string | NoFisico;
  target: string | NoFisico;
}

export const useGrafoFisica = (
  nos: No[] = [],
  arestas: Aresta[] = [],
  width: number,
  height: number,
  faseCognitiva: string,
  nosAtivados: string[] = [],
  onTick: () => void
) => {
  const simulationRef = useRef<Simulation<NoFisico, ArestaFisica> | null>(null);

  // Guardamos referências persistentes dos nós para o D3 poder gerenciar a inércia física
  const nosRef = useRef<NoFisico[]>([]);
  const arestasRef = useRef<ArestaFisica[]>([]);

  // Os arrays nos/arestas vivem dentro dos refs, que são mutáveis: entregar
  // `ref.current` em vez do próprio ref evita que o consumidor coloque o valor
  // nas dependências de um efeito (o valor muda a cada frame da simulação).
  const lerNosFisica = useCallback(() => nosRef.current, []);
  const lerArestasFisica = useCallback(() => arestasRef.current, []);
  const lerSimulacao = useCallback(() => simulationRef.current, []);

  useEffect(() => {
    try {
      const safeNos = nos || [];
      const safeArestas = arestas || [];
      const safeNosAtivados = nosAtivados || [];

      // 1. Sincronização inteligente de nós
      const nosExistentes = new Map(nosRef.current.map((n) => [n.conceito, n] as const));

      nosRef.current = safeNos.map((n) => {
        const existente = nosExistentes.get(n.conceito);
        if (existente) {
          return {
            ...n,
            x: existente.x,
            y: existente.y,
            vx: existente.vx,
            vy: existente.vy,
            index: existente.index
          };
        }

        const safeWidth = typeof width === 'number' && !isNaN(width) && width > 0 ? width : 600;
        const safeHeight = typeof height === 'number' && !isNaN(height) && height > 0 ? height : 400;
        return {
          ...n,
          x: safeWidth / 2 + (Math.random() - 0.5) * 150,
          y: safeHeight / 2 + (Math.random() - 0.5) * 150
        };
      });

      // 2. Sincronização inteligente de arestas (Filtra arestas órfãs para imunidade absoluta contra crashes do D3)
      const nosConceitos = new Set(safeNos.map((n) => n.conceito));

      arestasRef.current = safeArestas
        .filter((a) => a && a.de && a.para && nosConceitos.has(a.de) && nosConceitos.has(a.para))
        .map((a) => {
          return {
            de: a.de,
            para: a.para,
            peso: a.peso,
            tipo: a.tipo,
            source: a.de,
            target: a.para
          };
        });

      // 3. Determina parâmetros dinâmicos de física com base na Fase Cognitiva
      let chargeStrength = -180;
      let linkDistance = 130;
      let collideRadius = 35;

      switch (faseCognitiva) {
        case 'streaming':
          chargeStrength = -350;
          linkDistance = 150;
          break;
        case 'hipnagogia':
        case 'consolidacao':
        case 'sono_profundo':
          chargeStrength = -80;
          linkDistance = 90;
          collideRadius = 25;
          break;
        case 'sonho':
          chargeStrength = -120;
          linkDistance = 110;
          break;
        default:
          chargeStrength = -180;
          linkDistance = 130;
      }

      // 4. Inicializa ou Atualiza a Simulação
      if (!simulationRef.current) {
        simulationRef.current = forceSimulation<NoFisico, ArestaFisica>()
          .force('link', forceLink<NoFisico, ArestaFisica>().id((d) => d.conceito))
          .force('charge', forceManyBody<NoFisico>())
          .force('center', forceCenter<NoFisico>(width / 2, height / 2))
          .force('collide', forceCollide<NoFisico>())
          .on('tick', onTick);
      }

      const sim = simulationRef.current;

      // Atualiza dinamicamente as forças reativas
      sim.force('charge', forceManyBody<NoFisico>().strength(chargeStrength));
      sim.force('collide', forceCollide<NoFisico>().radius(collideRadius));

      // 1. ATUALIZA OS NÓS PRIMEIRO (Para que o D3 tenha o registro de nós pronto ao resolver os links!)
      sim.nodes(nosRef.current);

      // 2. CONFIGURA E ATUALIZA OS LINKS
      const linkForce = sim.force<ForceLink<NoFisico, ArestaFisica>>('link');
      if (linkForce) {
        linkForce
          .distance(linkDistance)
          .strength((d) => {
            const sourceConceito =
              d.source && typeof d.source === 'object' ? d.source.conceito : d.source;
            const targetConceito =
              d.target && typeof d.target === 'object' ? d.target.conceito : d.target;

            const isAtivo =
              safeNosAtivados &&
              (safeNosAtivados.includes(sourceConceito) || safeNosAtivados.includes(targetConceito));
            const baseStrength = d.tipo === 'hifa' ? 0.2 : (d.peso || 0.5) * 0.45;
            return isAtivo ? Math.min(1.0, baseStrength * 2.2) : baseStrength;
          })
          .links(arestasRef.current);
      }

      // Re-aquece levemente
      sim.alpha(0.3).restart();
    } catch (err) {
      console.error('[useGrafoFisica] Falha crítica ao inicializar simulação D3:', err);
    }

  }, [nos, arestas, width, height, faseCognitiva, nosAtivados, onTick]);

  // Limpa a simulação ao desmontar
  useEffect(() => {
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, []);

  return {
    lerNosFisica,
    lerArestasFisica,
    lerSimulacao
  };
};