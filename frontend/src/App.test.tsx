import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { useConscienciaStore } from './store/conscienciaStore';

// O layout é o que está sob teste: os três módulos pesados (WebGL, Canvas 2D e
// WebSocket real) são substituídos para não arrastar infraestrutura para o
// teste de composição da página.
vi.mock('./components/Dodecaedro3D', () => ({
  Dodecaedro3D: () => <div data-testid="nucleo-3d" />,
}));

vi.mock('./components/GrafoNeon', () => ({
  GrafoNeon: () => <div data-testid="grafo-neon" />,
}));

vi.mock('./hooks/useConsciencia', () => ({
  useConsciencia: () => ({
    enviarEstimulo: vi.fn(() => true),
    enviarPerguntaChat: vi.fn(() => true),
    dormir: vi.fn(() => true),
    statusConexao: 'connected',
  }),
}));

beforeEach(() => {
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
});

describe('App', () => {
  it('monta o HUD completo com os painéis principais', async () => {
    render(<App />);

    expect(screen.getByText('MILLA // ARQUITETURA COGNITIVA')).toBeInTheDocument();
    expect(screen.getByText('CONSOLE DE INTEGRAÇÃO SINÁPTICA')).toBeInTheDocument();
    expect(screen.getByText('Absorção Semântica')).toBeInTheDocument();
    expect(screen.getByText('Self Level')).toBeInTheDocument();
    expect(screen.getByTestId('grafo-neon')).toBeInTheDocument();
    expect(
      screen.getByText(
        /Projeto Milla © 2026/
      )
    ).toBeInTheDocument();

    // O núcleo 3D entra por React.lazy: o Suspense o resolve em seguida.
    expect(await screen.findByTestId('nucleo-3d')).toBeInTheDocument();
  });
});
