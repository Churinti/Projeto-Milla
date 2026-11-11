import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import type { ForceLink, ForceManyBody } from 'd3-force';
import { useGrafoFisica } from './useGrafoFisica';
import type { ArestaFisica, NoFisico } from './useGrafoFisica';
import type { Aresta, FaseCognitiva, No } from '../types/consciencia';

const no = (conceito: string): No => ({
  conceito,
  faces: { logica: 0.5 },
  energia: 0.6,
  ativacoes: 1,
  origem: 'teste',
});

const NOS: No[] = [no('A'), no('B')];

const ARESTAS: Aresta[] = [
  { de: 'A', para: 'B', peso: 0.5, tipo: 'normal' },
  // Órfã: 'Z' não existe entre os nós, precisa ser descartada antes do d3.
  { de: 'A', para: 'Z', peso: 0.9 },
];

const onTick = vi.fn();

interface Props {
  fase: FaseCognitiva;
  ativados: string[];
  largura?: number;
  altura?: number;
}

const montar = (inicial: Props = { fase: 'idle', ativados: [] }) =>
  renderHook(
    ({ fase, ativados, largura = 800, altura = 600 }: Props) =>
      useGrafoFisica(NOS, ARESTAS, largura, altura, fase, ativados, onTick),
    { initialProps: inicial }
  );

describe('useGrafoFisica · sincronização dos dados', () => {
  it('cria os nós físicos com posição inicial dentro do canvas', () => {
    const { result } = montar();

    act(() => result.current.lerSimulacao()?.stop());

    const fisicos = result.current.lerNosFisica();
    expect(fisicos.map((n) => n.conceito)).toEqual(['A', 'B']);
    for (const n of fisicos) {
      expect(n.x).toBeGreaterThan(325);
      expect(n.x).toBeLessThan(475);
      expect(n.y).toBeGreaterThan(225);
      expect(n.y).toBeLessThan(375);
    }
  });

  it('descarta arestas órfãs, que fariam o d3 estourar', () => {
    const { result } = montar();

    act(() => result.current.lerSimulacao()?.stop());

    const arestas = result.current.lerArestasFisica();
    expect(arestas).toHaveLength(1);
    expect(arestas[0]).toMatchObject({ de: 'A', para: 'B', peso: 0.5 });
    // O forceLink troca as strings pelos próprios nós ao resolver os links.
    expect(arestas[0].source).toMatchObject({ conceito: 'A' });
    expect(arestas[0].target).toMatchObject({ conceito: 'B' });
  });

  it('usa um canvas de 600×400 quando a largura/altura chegam inválidas', () => {
    const { result } = montar({ fase: 'idle', ativados: [], largura: 0, altura: Number.NaN });

    act(() => result.current.lerSimulacao()?.stop());

    const [primeiro] = result.current.lerNosFisica();
    expect(primeiro.x).toBeGreaterThan(225);
    expect(primeiro.x).toBeLessThan(375);
    expect(primeiro.y).toBeGreaterThan(125);
    expect(primeiro.y).toBeLessThan(275);
  });

  it('preserva posição e velocidade dos nós entre atualizações', () => {
    const { result, rerender } = montar();

    act(() => result.current.lerSimulacao()?.stop());

    const [antes] = result.current.lerNosFisica();
    act(() => {
      antes.x = 42;
      antes.y = 24;
    });

    rerender({ fase: 'streaming', ativados: [] });

    const [depois] = result.current.lerNosFisica();
    expect(depois.x).toBe(42);
    expect(depois.y).toBe(24);
  });
});

describe('useGrafoFisica · física adaptativa por fase', () => {
  const forcaCarga = (result: { current: ReturnType<typeof useGrafoFisica> }) => {
    const carga = result.current.lerSimulacao()?.force('charge') as ForceManyBody<NoFisico>;
    return carga.strength()({} as NoFisico, 0, []);
  };

  const distanciaLink = (result: { current: ReturnType<typeof useGrafoFisica> }) => {
    const link = result.current.lerSimulacao()?.force('link') as ForceLink<NoFisico, ArestaFisica>;
    return link.distance()(result.current.lerArestasFisica()[0], 0, []);
  };

  it.each([
    ['streaming', -350, 150],
    ['hipnagogia', -80, 90],
    ['sonho', -120, 110],
    ['idle', -180, 130],
  ] as const)('a fase %s ajusta repulsão para %s e distância para %s', (fase, carga, distancia) => {
    const { result } = montar({ fase, ativados: [] });

    expect(forcaCarga(result)).toBe(carga);
    expect(distanciaLink(result)).toBe(distancia);

    act(() => result.current.lerSimulacao()?.stop());
  });

  it('reforça a conexão de nós ativados', () => {
    const { result, rerender } = montar({ fase: 'idle', ativados: [] });

    const link = () => {
      const forca = result.current.lerSimulacao()?.force('link') as ForceLink<NoFisico, ArestaFisica>;
      return forca.strength()(result.current.lerArestasFisica()[0], 0, []);
    };

    // peso 0.5 * 0.45 = 0.225 sem ativação
    expect(link()).toBeCloseTo(0.225, 5);

    rerender({ fase: 'idle', ativados: ['A'] });
    // ativação multiplica por 2.2 (respeitando o teto de 1.0)
    expect(link()).toBeCloseTo(0.495, 5);

    act(() => result.current.lerSimulacao()?.stop());
  });
});
