import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';
import { MetricsPanel } from './MetricsPanel';
import { useConscienciaStore } from '../store/conscienciaStore';
import type { EstadoConsciencia, No } from '../types/consciencia';

const no = (conceito: string): No => ({
  conceito,
  faces: {},
  energia: 0.5,
  ativacoes: 1,
  origem: 'teste',
});

const estado: EstadoConsciencia = {
  nivel_consciencia: 0.756,
  estado_qualitativo: 'integrado',
  coerencia: 0.912,
  vitalidade: 0.634,
  complexidade: 0.487,
  desejo: 0.128,
};

beforeEach(() => {
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
});

describe('MetricsPanel', () => {
  it('mostra o nível do Self e o estado qualitativo com uma casa decimal', () => {
    useConscienciaStore.setState({ estado });

    render(<MetricsPanel />);

    expect(screen.getByText('75.6%')).toBeInTheDocument();
    expect(screen.getByText('integrado')).toBeInTheDocument();
  });

  it('exibe as quatro métricas do termômetro com três casas', () => {
    useConscienciaStore.setState({ estado });

    render(<MetricsPanel />);

    expect(screen.getByText('0.912')).toBeInTheDocument();
    expect(screen.getByText('0.634')).toBeInTheDocument();
    expect(screen.getByText('0.487')).toBeInTheDocument();
    expect(screen.getByText('0.128')).toBeInTheDocument();
  });

  it('conta os conceitos e as arestas do grafo ativo', () => {
    useConscienciaStore.setState({
      nos: [no('A'), no('B'), no('C')],
      arestas: [
        { de: 'A', para: 'B', peso: 0.8 },
        { de: 'B', para: 'C', peso: 0.6 },
      ],
    });

    const { container } = render(<MetricsPanel />);

    expect(screen.getByText('Conceitos')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Arestas')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    // A barra de coerência reflete o valor da store.
    expect(container.querySelectorAll('svg circle')).toHaveLength(2);
  });

  it.each([
    ['connected', 'SINAPSE OPERANTE'],
    ['connecting', 'SINTONIZANDO SELF...'],
    ['disconnected', 'CONEXÃO RESTRITA'],
  ] as const)('traduz o status de conexão %s', (statusConexao, texto) => {
    useConscienciaStore.setState({ statusConexao });

    render(<MetricsPanel />);

    expect(screen.getByText(texto)).toBeInTheDocument();
  });

  it.each([
    ['pre_pensamento', 'PRE-PENSAMENTO (ANÁLISE DE FUROS)'],
    ['streaming', 'FUSÃO COGNITIVA (REFLETINDO)'],
    ['pos_pensamento', 'PÓS-PENSAMENTO (PLASTICIDADE)'],
    ['idle', 'CONSCIÊNCIA ESTÁVEL'],
  ] as const)('traduz a fase cognitiva %s', (faseCognitiva, texto) => {
    useConscienciaStore.setState({ faseCognitiva });

    render(<MetricsPanel />);

    expect(screen.getByText(texto)).toBeInTheDocument();
  });
});
