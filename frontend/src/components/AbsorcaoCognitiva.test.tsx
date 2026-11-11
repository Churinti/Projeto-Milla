import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AbsorcaoCognitiva } from './AbsorcaoCognitiva';
import { useConscienciaStore } from '../store/conscienciaStore';
import { salvarToken } from '../lib/auth';

const fetchMock = vi.fn();

const respostaOk = { ok: true, status: 200, json: async () => ({ status: 'absorcao_iniciada' }) };

const selecionarArquivo = (nome: string) => {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  fireEvent.change(input, { target: { files: [new File(['conteúdo'], nome)] } });
};

beforeEach(() => {
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
  window.sessionStorage.clear();
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(respostaOk);
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
});

describe('AbsorcaoCognitiva · upload de arquivo', () => {
  it('exibe o estado ocioso com formatos aceitos e campo de URL', () => {
    render(<AbsorcaoCognitiva />);

    expect(screen.getByText('Arraste PDF, DOCX, TXT ou MD')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('https://wikipedia.org/wiki/...')).toBeInTheDocument();
    expect(screen.getByText('pdf')).toBeInTheDocument();
    expect(screen.getByText('docx')).toBeInTheDocument();
    expect(screen.getByText('txt')).toBeInTheDocument();
    expect(screen.getByText('md')).toBeInTheDocument();
  });

  it('recusa formato não suportado antes de chamar a API', () => {
    render(<AbsorcaoCognitiva />);

    selecionarArquivo('planilha.xlsx');

    expect(screen.getByText('Falha de Ingestão')).toBeInTheDocument();
    expect(screen.getByText(/Formato incompatível: "\.xlsx"/)).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('envia o arquivo aceito como multipart e entra em processamento', async () => {
    render(<AbsorcaoCognitiva />);

    selecionarArquivo('filosofia.md');

    expect(await screen.findByText('Sincronização Ativa')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [rota, opcoes] = fetchMock.mock.calls[0];
    expect(rota).toBe('/api/absorver-conhecimento');
    expect(opcoes.method).toBe('POST');
    const corpo = opcoes.body as FormData;
    expect(corpo).toBeInstanceOf(FormData);
    expect((corpo.get('file') as File).name).toBe('filosofia.md');
    expect(useConscienciaStore.getState().absorcaoStatus?.etapa).toBe('upload');
  });

  it('mostra a mensagem de erro devolvida pela API', async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ erro: 'PDF sem camada de texto' }),
    });

    render(<AbsorcaoCognitiva />);
    selecionarArquivo('escaneado.pdf');

    expect(await screen.findByText('Falha de Ingestão')).toBeInTheDocument();
    expect(screen.getByText('PDF sem camada de texto')).toBeInTheDocument();
    expect(useConscienciaStore.getState().absorcaoStatus).toBeNull();
  });

  it('avisa quando a rede falha', async () => {
    fetchMock.mockRejectedValue(new Error('offline'));

    render(<AbsorcaoCognitiva />);
    selecionarArquivo('notas.txt');

    expect(await screen.findByText('offline')).toBeInTheDocument();
  });

  it('adapta a frase do loader quando a vitalidade está baixa', async () => {
    useConscienciaStore.setState({
      estado: { ...useConscienciaStore.getState().estado, vitalidade: 0.3 },
    });

    render(<AbsorcaoCognitiva />);
    selecionarArquivo('notas.txt');

    expect(
      await screen.findByText('Milla está exausta, metabolizando o documento lentamente...')
    ).toBeInTheDocument();
  });

  it('anexa o token de acesso ao upload quando há credencial', async () => {
    salvarToken('token-de-teste-1234567890');
    render(<AbsorcaoCognitiva />);

    selecionarArquivo('filosofia.md');

    expect(await screen.findByText('Sincronização Ativa')).toBeInTheDocument();
    const [, opcoes] = fetchMock.mock.calls[0];
    expect(opcoes.headers).toEqual({
      Authorization: 'Bearer token-de-teste-1234567890',
    });
  });
});

describe('AbsorcaoCognitiva · absorção de URL', () => {
  it('valida o esquema antes de qualquer requisição', async () => {
    const user = userEvent.setup();
    render(<AbsorcaoCognitiva />);

    await user.type(screen.getByPlaceholderText('https://wikipedia.org/wiki/...'), 'wikipedia.org/wiki/Entropia');
    await user.click(screen.getByText('Absorver'));

    expect(screen.getByText('URL deve começar com http:// ou https://')).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('envia a URL validada em JSON para a API', async () => {
    const user = userEvent.setup();
    render(<AbsorcaoCognitiva />);

    await user.type(
      screen.getByPlaceholderText('https://wikipedia.org/wiki/...'),
      'https://pt.wikipedia.org/wiki/Entropia'
    );
    await user.click(screen.getByText('Absorver'));

    expect(await screen.findByText('Verificando URL...')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/absorver-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://pt.wikipedia.org/wiki/Entropia' }),
    });
  });

  it('exibe o bloqueio anti-SSRF devolvido pelo backend', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ erro: 'URL bloqueada: endereço interno.' }),
    });

    render(<AbsorcaoCognitiva />);
    await user.type(
      screen.getByPlaceholderText('https://wikipedia.org/wiki/...'),
      'http://169.254.169.254/latest/meta-data'
    );
    await user.click(screen.getByText('Absorver'));

    expect(await screen.findByText('URL bloqueada: endereço interno.')).toBeInTheDocument();
  });
});

describe('AbsorcaoCognitiva · progresso via WebSocket', () => {
  it('conclui com os conceitos injetados e permite reiniciar', async () => {
    const user = userEvent.setup();
    render(<AbsorcaoCognitiva />);

    act(() =>
      useConscienciaStore.getState().atualizarAbsorcao({
        ativo: false,
        etapa: 'concluido',
        progresso: 100,
        mensagem: 'Ingestão finalizada',
        nosInjetados: ['Causalidade', 'Entropia'],
      })
    );

    expect(screen.getByText('Absorção Concluída')).toBeInTheDocument();
    expect(screen.getByText('Causalidade')).toBeInTheDocument();
    expect(screen.getByText('Entropia')).toBeInTheDocument();

    await user.click(screen.getByText('Absorção Concluída'));

    expect(screen.getByText('Arraste PDF, DOCX, TXT ou MD')).toBeInTheDocument();
    expect(useConscienciaStore.getState().absorcaoStatus).toBeNull();
  });

  it('mostra a falha relatada pelo pipeline e permite redefinir', async () => {
    const user = userEvent.setup();
    render(<AbsorcaoCognitiva />);

    act(() =>
      useConscienciaStore.getState().atualizarAbsorcao({
        ativo: false,
        etapa: 'erro',
        progresso: 0,
        mensagem: 'Modelo local não respondeu',
        nosInjetados: [],
      })
    );

    expect(screen.getByText('Falha de Ingestão')).toBeInTheDocument();
    expect(screen.getByText('Modelo local não respondeu')).toBeInTheDocument();

    await user.click(screen.getByText('Clique para redefinir'));

    expect(screen.getByText('Arraste PDF, DOCX, TXT ou MD')).toBeInTheDocument();
  });
});
