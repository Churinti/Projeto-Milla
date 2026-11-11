import { beforeEach, afterEach, describe, expect, it, vi } from 'vitest';
import { useConscienciaStore } from './conscienciaStore';
import type { DeltaGrafo, No, RelatorioDeSono } from '../types/consciencia';

const criarNo = (conceito: string, sobrescrever: Partial<No> = {}): No => ({
  conceito,
  faces: { logica: 0.5, emocao: 0.4 },
  energia: 0.6,
  ativacoes: 1,
  origem: 'teste',
  ...sobrescrever,
});

const deltaVazio = (): DeltaGrafo => ({
  nos_novos: [],
  nos_modificados: [],
  nos_removidos: [],
  arestas_novas: [],
  arestas_modificadas: [],
  arestas_removidas: [],
});

const estado = () => useConscienciaStore.getState();

beforeEach(() => {
  // A store é um singleton de módulo: cada teste parte do estado inicial.
  useConscienciaStore.setState(useConscienciaStore.getInitialState(), true);
});

afterEach(() => {
  vi.useRealTimers();
});

describe('conscienciaStore · estado inicial', () => {
  it('começa em sintonia, sem nós e com a mensagem de boas-vindas', () => {
    expect(estado().statusConexao).toBe('connecting');
    expect(estado().nos).toEqual([]);
    expect(estado().arestas).toEqual([]);
    expect(estado().faseCognitiva).toBe('idle');
    expect(estado().mensagens).toHaveLength(1);
    expect(estado().mensagens[0].sender).toBe('milla');
  });
});

describe('conscienciaStore · aplicarDelta (nós)', () => {
  it('injeta nós novos com posição inicial em torno do centro da viewport', () => {
    estado().aplicarDelta({ ...deltaVazio(), nos_novos: [criarNo('Geometria')] });

    const [no] = estado().nos;
    expect(no.conceito).toBe('Geometria');
    expect(no.faces).toEqual({ logica: 0.5, emocao: 0.4 });
    // window.innerWidth/2 = 512, com jitter de ±50px.
    expect(no.x).toBeGreaterThan(462);
    expect(no.x).toBeLessThan(562);
    expect(no.y).toBeGreaterThan(334);
    expect(no.y).toBeLessThan(434);
  });

  it('não duplica um conceito que já existe no grafo', () => {
    estado().aplicarDelta({ ...deltaVazio(), nos_novos: [criarNo('A')] });
    estado().aplicarDelta({ ...deltaVazio(), nos_novos: [criarNo('A')] });

    expect(estado().nos).toHaveLength(1);
  });

  it('atualiza faces/energia/ativações preservando a posição física do d3', () => {
    useConscienciaStore.setState({
      nos: [criarNo('A', { x: 11, y: 22, energia: 0.2 })],
    });

    estado().aplicarDelta({
      ...deltaVazio(),
      nos_modificados: [
        criarNo('A', { x: undefined, y: undefined, energia: 0.9, origem: 'feedback', faces: { logica: 0.99 } }),
      ],
    });

    const [no] = estado().nos;
    expect(no.x).toBe(11);
    expect(no.y).toBe(22);
    expect(no.energia).toBe(0.9);
    expect(no.origem).toBe('feedback');
    expect(no.faces).toEqual({ logica: 0.99 });
  });

  it('marca o nó podado como isFadingOut e o remove só depois dos 2s de animação', () => {
    vi.useFakeTimers();
    useConscienciaStore.setState({ nos: [criarNo('A'), criarNo('B')] });

    estado().aplicarDelta({ ...deltaVazio(), nos_removidos: ['A'] });

    expect(estado().nos).toHaveLength(2);
    expect(estado().nos.find((n) => n.conceito === 'A')?.isFadingOut).toBe(true);

    vi.advanceTimersByTime(1999);
    expect(estado().nos).toHaveLength(2);

    vi.advanceTimersByTime(1);
    expect(estado().nos.map((n) => n.conceito)).toEqual(['B']);
  });

  it('removerNos descarta apenas os conceitos listados', () => {
    useConscienciaStore.setState({ nos: [criarNo('A'), criarNo('B')] });

    estado().removerNos(['A']);

    expect(estado().nos.map((n) => n.conceito)).toEqual(['B']);
  });
});

describe('conscienciaStore · aplicarDelta (arestas)', () => {
  it('adiciona arestas novas e ignora a duplicata em direção invertida', () => {
    estado().aplicarDelta({
      ...deltaVazio(),
      arestas_novas: [{ de: 'A', para: 'B', peso: 0.8, tipo: 'normal' }],
    });
    estado().aplicarDelta({
      ...deltaVazio(),
      arestas_novas: [
        { de: 'B', para: 'A', peso: 0.8 },
        { de: 'B', para: 'C', peso: 0.4 },
      ],
    });

    expect(estado().arestas).toHaveLength(2);
    expect(estado().arestas.map((a) => `${a.de}-${a.para}`)).toEqual(['A-B', 'B-C']);
  });

  it('remove aresta independentemente da direção informada', () => {
    useConscienciaStore.setState({
      arestas: [
        { de: 'A', para: 'B', peso: 0.8 },
        { de: 'B', para: 'C', peso: 0.4 },
      ],
    });

    estado().aplicarDelta({
      ...deltaVazio(),
      arestas_removidas: [{ de: 'B', para: 'A' }],
    });

    expect(estado().arestas).toHaveLength(1);
    expect(estado().arestas[0].de).toBe('B');
    expect(estado().arestas[0].para).toBe('C');
  });

  it('atualiza o peso achando a aresta nas duas direções e preserva o tipo quando ausente', () => {
    useConscienciaStore.setState({
      arestas: [{ de: 'A', para: 'B', peso: 0.3, tipo: 'hifa' }],
    });

    estado().aplicarDelta({
      ...deltaVazio(),
      arestas_modificadas: [{ de: 'B', para: 'A', peso: 0.95 }],
    });

    expect(estado().arestas[0].peso).toBe(0.95);
    expect(estado().arestas[0].tipo).toBe('hifa');
  });

  it('troca o tipo da aresta quando o delta informa um novo tipo', () => {
    useConscienciaStore.setState({
      arestas: [{ de: 'A', para: 'B', peso: 0.3, tipo: 'normal' }],
    });

    estado().aplicarDelta({
      ...deltaVazio(),
      arestas_modificadas: [{ de: 'A', para: 'B', peso: 0.3, tipo: 'insight_onirico' }],
    });

    expect(estado().arestas[0].tipo).toBe('insight_onirico');
  });
});

describe('conscienciaStore · ciclo de pensamento', () => {
  it('acumula tokens e sinaliza streaming', () => {
    estado().adicionarToken('Olá, ');
    estado().adicionarToken('mundo');

    expect(estado().tokenAtual).toBe('Olá, mundo');
    expect(estado().isStreaming).toBe(true);
    expect(estado().faseCognitiva).toBe('streaming');
  });

  it('finalizarPensamento consolida a mensagem com o estado existencial e limpa o streaming', () => {
    estado().adicionarToken('rascunho');
    estado().finalizarPensamento('Pensamento final', 0.1, null);

    const mensagens = estado().mensagens;
    const ultima = mensagens[mensagens.length - 1];
    expect(ultima.text).toBe('Pensamento final');
    expect(ultima.sender).toBe('milla');
    expect(ultima.estado).toEqual(estado().estado);
    expect(estado().tokenAtual).toBe('');
    expect(estado().isStreaming).toBe(false);
    expect(estado().faseCognitiva).toBe('idle');
  });

  it('limparStreaming zera token e flags sem apagar mensagens', () => {
    estado().adicionarToken('abc');
    const total = estado().mensagens.length;

    estado().limparStreaming();

    expect(estado().tokenAtual).toBe('');
    expect(estado().isStreaming).toBe(false);
    expect(estado().mensagens).toHaveLength(total);
  });

  it('atualizarEstadoParcial mantém a lista anterior quando a nova vem vazia', () => {
    estado().atualizarEstadoParcial('pre_pensamento', { ...estado().estado, coerencia: 0.9 }, ['A', 'B']);
    estado().atualizarEstadoParcial('streaming', undefined as never, []);

    expect(estado().nosAtivados).toEqual(['A', 'B']);
    expect(estado().estado.coerencia).toBe(0.9);
    expect(estado().isStreaming).toBe(true);
  });
});

describe('conscienciaStore · ciclo de sono', () => {
  it('iniciarSono entra em hipnagogia e guarda o total de ciclos', () => {
    estado().iniciarSono(3);

    expect(estado().sonoAtivo).toBe(true);
    expect(estado().faseCognitiva).toBe('hipnagogia');
    expect(estado().ciclosSonoTotal).toBe(3);
    expect(estado().cicloSonoAtual).toBe(0);
    expect(estado().relatorioDeSono).toBeNull();
  });

  it('processarProgressoSono atualiza fase/mensagem e preserva ciclo e total omitidos', () => {
    estado().iniciarSono(3);
    estado().processarProgressoSono('sonho', 'Entrando em REM', 2, 3);
    estado().processarProgressoSono('consolidacao', 'Poda');

    expect(estado().faseCognitiva).toBe('consolidacao');
    expect(estado().mensagemSono).toBe('Poda');
    expect(estado().cicloSonoAtual).toBe(2);
    expect(estado().ciclosSonoTotal).toBe(3);
  });

  it('finalizarSono volta à vigília e narra o relatório no chat', () => {
    const relatorio: RelatorioDeSono = {
      ciclos_executados: 3,
      nos_arquivados: 4,
      buscas_realizadas: 2,
      coerencia_inicial: 0.5,
      coerencia_final: 0.72,
      insights_gerados: [{ ponte: 'A→B', descricao: 'Nova ponte', similaridade: 0.81 }],
    };

    estado().iniciarSono(3);
    estado().finalizarSono(relatorio);

    const mensagens = estado().mensagens;
    const texto = mensagens[mensagens.length - 1].text;
    expect(estado().sonoAtivo).toBe(false);
    expect(estado().faseCognitiva).toBe('vigilia');
    expect(estado().relatorioDeSono).toEqual(relatorio);
    expect(texto).toContain('SONO CONCLUÍDO');
    expect(texto).toContain('Nós podados por decaimento: 4');
    expect(texto).toContain('Buscas de Curiosidade Autônomas: 2');
    expect(texto).toContain('A→B (cosseno: 0.81): Nova ponte');
    expect(texto).toContain('0.500 → 0.720');
  });

  it('finalizarSono sem insights nem buscas usa os textos neutros', () => {
    estado().finalizarSono({
      ciclos_executados: 1,
      nos_arquivados: 0,
      coerencia_inicial: 0.6,
      coerencia_final: 0.61,
    });

    const texto = estado().mensagens[estado().mensagens.length - 1].text;
    expect(texto).toContain('Nenhum novo insight sináptico estabilizado.');
    expect(texto).toContain('Buscas de Curiosidade Autônomas: 0');
  });
});

describe('conscienciaStore · mensagens, conexão e absorção', () => {
  it('adicionarMensagem anexa ao fim da conversa', () => {
    estado().adicionarMensagem({
      id: 'u1',
      sender: 'user',
      text: 'olá',
      timestamp: new Date().toISOString(),
    });

    expect(estado().mensagens).toHaveLength(2);
    expect(estado().mensagens[1].text).toBe('olá');
  });

  it('setConexao e setCaminhoIluminado atualizam o HUD', () => {
    estado().setConexao('connected');
    estado().setCaminhoIluminado(['A', 'B', 'C']);

    expect(estado().statusConexao).toBe('connected');
    expect(estado().caminhoIluminado).toEqual(['A', 'B', 'C']);
  });

  it('atualizarAbsorcao guarda o status e aceita a limpeza', () => {
    estado().atualizarAbsorcao({
      ativo: true,
      etapa: 'extraindo',
      progresso: 40,
      mensagem: 'analisando',
      nosInjetados: [],
    });
    expect(estado().absorcaoStatus?.progresso).toBe(40);

    estado().atualizarAbsorcao(null);
    expect(estado().absorcaoStatus).toBeNull();
  });
});
