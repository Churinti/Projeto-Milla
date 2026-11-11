/**
 * Credencial da Milla no navegador.
 *
 * O backend não usa cookie nem sessão: o token é o mesmo `MILLA_TOKEN`
 * configurado no servidor. Ele fica em `sessionStorage` — some quando a aba
 * fecha — e não em `localStorage`, para não deixar a senha parada na máquina
 * depois do uso.
 *
 * No REST vai como `Authorization: Bearer`; no WebSocket (onde o navegador não
 * deixa o JS definir headers) vai como segundo item da lista de subprotocolos.
 */

const CHAVE_TOKEN = 'milla.token';

/** Subprotocolo negociado no handshake do WebSocket. */
export const PROTOCOLO_WS = 'milla.v1';

/**
 * Evento disparado quando o backend fecha o WebSocket por credencial recusada
 * (código 1008). O portão escuta e volta a pedir o token, em vez de deixar o
 * painel reconectando em loop.
 */
export const EVENTO_AUTORIZACAO = 'milla:autorizacao';

export function lerToken(): string | null {
  try {
    const valor = window.sessionStorage.getItem(CHAVE_TOKEN)?.trim();
    return valor ? valor : null;
  } catch {
    // Storage bloqueado (alguns modos privativos): segue sem credencial e o
    // portão mostrará o login.
    return null;
  }
}

export function salvarToken(token: string): void {
  try {
    window.sessionStorage.setItem(CHAVE_TOKEN, token.trim());
  } catch {
    // Sem storage, o token vale só para esta página (o fetch abaixo ainda usa
    // o valor digitado); o próximo recarregamento pedirá de novo.
  }
}

export function limparToken(): void {
  try {
    window.sessionStorage.removeItem(CHAVE_TOKEN);
  } catch {
    // idem acima
  }
}

/** Cabeçalhos a acrescentar em toda chamada REST autenticada. */
export function cabecalhosAuth(): Record<string, string> {
  const token = lerToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** Lista de subprotocolos do handshake — o token vai junto quando existe. */
export function protocolosWs(): string[] {
  const token = lerToken();
  return token ? [PROTOCOLO_WS, token] : [PROTOCOLO_WS];
}
