import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PortaoAcesso } from './PortaoAcesso';
import { EVENTO_AUTORIZACAO, lerToken } from '../lib/auth';

const fetchMock = vi.fn();

/** Resposta mínima do `/api/auth/status`. */
const resposta = (corpo: unknown) => ({ ok: true, json: async () => corpo });

const TOKEN = 'token-de-teste-1234567890';

const Painel = () => <p>painel liberado</p>;

const renderizar = () =>
  render(
    <PortaoAcesso>
      <Painel />
    </PortaoAcesso>
  );

beforeEach(() => {
  window.sessionStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
});

describe('PortaoAcesso · descoberta do estado', () => {
  it('sem autenticação no servidor, monta o painel direto', async () => {
    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: false, autenticado: true })
    );

    renderizar();

    expect(await screen.findByText('painel liberado')).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith('/api/auth/status', {
      headers: {},
      cache: 'no-store',
    });
  });

  it('com autenticação ativa, pede o token antes de montar o painel', async () => {
    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: true, autenticado: false })
    );

    renderizar();

    expect(await screen.findByLabelText('Token de acesso')).toBeInTheDocument();
    expect(screen.queryByText('painel liberado')).not.toBeInTheDocument();
  });

  it('rede sem senha configurada explica o bloqueio e não mostra formulário', async () => {
    fetchMock.mockResolvedValue(
      resposta({
        autenticacao_ativa: false,
        autenticado: false,
        erro: 'Acesso pela rede bloqueado: Milla está sem senha.',
      })
    );

    renderizar();

    expect(await screen.findByText('Rede sem senha configurada')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Milla está sem senha');
    expect(screen.queryByLabelText('Token de acesso')).not.toBeInTheDocument();
  });

  it('backend fora do ar permite tentar de novo', async () => {
    const user = userEvent.setup();
    fetchMock.mockRejectedValueOnce(new Error('offline'));

    renderizar();

    expect(await screen.findByText('Núcleo inacessível')).toBeInTheDocument();

    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: false, autenticado: true })
    );
    await user.click(screen.getByRole('button', { name: /tentar novamente/i }));

    expect(await screen.findByText('painel liberado')).toBeInTheDocument();
  });
});

describe('PortaoAcesso · login', () => {
  it('token aceito libera o painel e fica guardado na sessão', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(
      resposta({ autenticacao_ativa: true, autenticado: false })
    );

    renderizar();
    await user.type(await screen.findByLabelText('Token de acesso'), TOKEN);

    fetchMock.mockResolvedValueOnce(
      resposta({ autenticacao_ativa: true, autenticado: true })
    );
    await user.click(screen.getByRole('button', { name: /autenticar/i }));

    expect(await screen.findByText('painel liberado')).toBeInTheDocument();
    expect(lerToken()).toBe(TOKEN);
  });

  it('token recusado mantém o portão e apaga a credencial', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValueOnce(
      resposta({ autenticacao_ativa: true, autenticado: false })
    );

    renderizar();
    await user.type(await screen.findByLabelText('Token de acesso'), 'token-errado-1234567890');

    fetchMock.mockResolvedValueOnce(
      resposta({
        autenticacao_ativa: true,
        autenticado: false,
        erro: 'Token de acesso ausente ou inválido.',
      })
    );
    await user.click(screen.getByRole('button', { name: /autenticar/i }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Token de acesso ausente ou inválido.');
    expect(screen.queryByText('painel liberado')).not.toBeInTheDocument();
    expect(lerToken()).toBeNull();
  });

  it('o botão só habilita com algum token digitado', async () => {
    const user = userEvent.setup();
    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: true, autenticado: false })
    );

    renderizar();

    const botao = await screen.findByRole('button', { name: /autenticar/i });
    expect(botao).toBeDisabled();

    await user.type(screen.getByLabelText('Token de acesso'), TOKEN);
    expect(botao).toBeEnabled();
  });
});

describe('PortaoAcesso · perda de autorização', () => {
  it('volta ao login quando o WebSocket recusa a credencial (1008)', async () => {
    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: false, autenticado: true })
    );

    renderizar();
    expect(await screen.findByText('painel liberado')).toBeInTheDocument();

    fetchMock.mockResolvedValue(
      resposta({ autenticacao_ativa: true, autenticado: false })
    );
    act(() => {
      window.dispatchEvent(new Event(EVENTO_AUTORIZACAO));
    });

    expect(await screen.findByLabelText('Token de acesso')).toBeInTheDocument();
    expect(screen.queryByText('painel liberado')).not.toBeInTheDocument();
  });
});
