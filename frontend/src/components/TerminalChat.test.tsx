import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { TerminalChat } from './TerminalChat';
import { useConscienciaStore } from '../store/conscienciaStore';

const mocks = vi.hoisted(() => ({
  enviarEstimulo: vi.fn(() => true),
  enviarPerguntaChat: vi.fn(() => true),
  dormir: vi.fn(() => true),
}));

vi.mock('../hooks/useConsciencia', () => ({
  useConsciencia: () => ({ ...mocks, statusConexao: 'connected' }),
}));

const PLACEHOLDER = 'Insira estimulação semântica/geométrica...';

beforeEach(() => {
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
  useConscienciaStore.setState({ statusConexao: 'connected' });
});

describe('TerminalChat · renderização', () => {
  it('mostra a mensagem de boas-vindas de Milla', () => {
    render(<TerminalChat />);

    expect(
      screen.getByText(
        'Conexão sináptica estabelecida. Estou pronta para processar estimulações geométricas.'
      )
    ).toBeInTheDocument();
  });

  it('exibe as métricas capturadas junto ao pensamento de Milla', () => {
    useConscienciaStore.setState({
      mensagens: [
        {
          id: 'm1',
          sender: 'milla',
          text: 'Pensamento com estado.',
          timestamp: new Date().toISOString(),
          estado: {
            nivel_consciencia: 0.8,
            estado_qualitativo: 'integrado',
            coerencia: 0.85,
            vitalidade: 0.7,
            complexidade: 0.5,
            desejo: 0.2,
          },
        },
      ],
    });

    render(<TerminalChat />);

    expect(screen.getByText('Coerência: 0.85')).toBeInTheDocument();
    expect(screen.getByText('Consciência: 0.80')).toBeInTheDocument();
    expect(screen.getByText('Vitalidade: 0.70')).toBeInTheDocument();
  });

  it('desabilita o campo sem conexão sináptica', () => {
    useConscienciaStore.setState({ statusConexao: 'disconnected' });

    render(<TerminalChat />);

    expect(screen.getByPlaceholderText('Sem conexão sináptica disponível.')).toBeDisabled();
    expect(screen.queryByText('💤 Dormir (3 Ciclos)')).not.toBeInTheDocument();
  });
});

describe('TerminalChat · envio de estímulos', () => {
  it('envia o estímulo digitado e limpa o campo', async () => {
    const user = userEvent.setup();
    render(<TerminalChat />);

    const input = screen.getByPlaceholderText(PLACEHOLDER);
    await user.type(input, 'O que é coerência geométrica?');
    await user.click(screen.getByTitle('Injetar Estímulo (Enter)'));

    expect(mocks.enviarEstimulo).toHaveBeenCalledWith('O que é coerência geométrica?');
    expect(input).toHaveValue('');
  });

  it('interpreta o prefixo "?" como pergunta ao grafo e remove o marcador', async () => {
    const user = userEvent.setup();
    render(<TerminalChat />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), '?Como A liga B?');
    await user.click(screen.getByTitle('Injetar Estímulo (Enter)'));

    expect(mocks.enviarPerguntaChat).toHaveBeenCalledWith('Como A liga B?');
    expect(mocks.enviarEstimulo).not.toHaveBeenCalled();
  });

  it('o botão amarelo consulta o grafo sem alterar o texto', async () => {
    const user = userEvent.setup();
    render(<TerminalChat />);

    await user.type(screen.getByPlaceholderText(PLACEHOLDER), 'Explique a entropia');
    await user.click(screen.getByTitle('Fazer uma Pergunta ao Grafo'));

    expect(mocks.enviarPerguntaChat).toHaveBeenCalledWith('Explique a entropia');
  });

  it('não envia nada com o campo vazio', async () => {
    const user = userEvent.setup();
    render(<TerminalChat />);

    expect(screen.getByTitle('Injetar Estímulo (Enter)')).toBeDisabled();
    await user.click(screen.getByTitle('Injetar Estímulo (Enter)'));

    expect(mocks.enviarEstimulo).not.toHaveBeenCalled();
  });

  it('bloqueia o envio enquanto Milla está fundindo um pensamento', async () => {
    const user = userEvent.setup();
    useConscienciaStore.setState({ isStreaming: true });

    render(<TerminalChat />);

    const input = screen.getByPlaceholderText('Milla está processando um pensamento...');
    expect(input).toBeDisabled();
    await user.type(input, 'texto');
    expect(mocks.enviarEstimulo).not.toHaveBeenCalled();
  });
});

describe('TerminalChat · streaming', () => {
  it('mostra os tokens em tempo real com o indicador de fusão ativa', () => {
    useConscienciaStore.setState({
      isStreaming: true,
      tokenAtual: 'A coerência emerge ',
      faseCognitiva: 'streaming',
    });

    render(<TerminalChat />);

    expect(screen.getByText('FUSÃO ATIVA...')).toBeInTheDocument();
    expect(screen.getByText(/A coerência emerge/)).toBeInTheDocument();
  });

  it('mostra o placeholder de espera antes do primeiro token', () => {
    useConscienciaStore.setState({ isStreaming: true, tokenAtual: '' });

    render(<TerminalChat />);

    expect(screen.getByText('Conectando com o Núcleo de Fusão...')).toBeInTheDocument();
  });
});

describe('TerminalChat · estado de sono', () => {
  it('o botão de dormir pede 3 ciclos', async () => {
    const user = userEvent.setup();
    render(<TerminalChat />);

    await user.click(screen.getByText('💤 Dormir (3 Ciclos)'));

    expect(mocks.dormir).toHaveBeenCalledWith(3);
  });

  it('sobrepõe o overlay de sono e trava o input durante o repouso', () => {
    useConscienciaStore.setState({
      sonoAtivo: true,
      mensagemSono: 'Sonhando com pontes REM',
      cicloSonoAtual: 2,
      ciclosSonoTotal: 3,
    });

    render(<TerminalChat />);

    expect(screen.getByText('Estado de Sono Regenerativo')).toBeInTheDocument();
    expect(screen.getByText('Sonhando com pontes REM')).toBeInTheDocument();
    expect(screen.getByText('Sonho Lúcido 2/3')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Milla está no estado de sono profundo...')).toBeDisabled();
    expect(screen.queryByText('💤 Dormir (3 Ciclos)')).not.toBeInTheDocument();
  });

  it('usa o rótulo de consolidação antes do primeiro sonho', () => {
    useConscienciaStore.setState({
      sonoAtivo: true,
      mensagemSono: 'Poda sináptica',
      cicloSonoAtual: 0,
      ciclosSonoTotal: 3,
    });

    render(<TerminalChat />);

    expect(screen.getByText('Consolidando')).toBeInTheDocument();
  });
});
