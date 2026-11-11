import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import {
  PROTOCOLO_WS,
  cabecalhosAuth,
  lerToken,
  limparToken,
  protocolosWs,
  salvarToken,
} from './auth';

const TOKEN = 'token-de-teste-1234567890';

beforeEach(() => {
  window.sessionStorage.clear();
});

afterEach(() => {
  window.sessionStorage.clear();
});

describe('lib/auth · credencial da sessão', () => {
  it('sem token não envia header nem credencial no WebSocket', () => {
    expect(lerToken()).toBeNull();
    expect(cabecalhosAuth()).toEqual({});
    expect(protocolosWs()).toEqual([PROTOCOLO_WS]);
  });

  it('guarda o token e o expõe como Bearer e como subprotocolo', () => {
    salvarToken(TOKEN);

    expect(lerToken()).toBe(TOKEN);
    expect(cabecalhosAuth()).toEqual({ Authorization: `Bearer ${TOKEN}` });
    expect(protocolosWs()).toEqual([PROTOCOLO_WS, TOKEN]);
  });

  it('remove espaços nas pontas ao salvar', () => {
    salvarToken(`  ${TOKEN}  `);

    expect(lerToken()).toBe(TOKEN);
  });

  it('valor em branco não vira credencial', () => {
    salvarToken('   ');

    expect(lerToken()).toBeNull();
    expect(cabecalhosAuth()).toEqual({});
  });

  it('limparToken esquece a credencial', () => {
    salvarToken(TOKEN);
    limparToken();

    expect(lerToken()).toBeNull();
    expect(protocolosWs()).toEqual([PROTOCOLO_WS]);
  });
});
