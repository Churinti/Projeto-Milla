# Changelog

Todas as mudanças notáveis do Projeto Milla ficam registradas aqui.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).
A versão corrente vive em `config.VERSAO` — é dali que o `api.py`, este arquivo
e a tag do git leem.

## [Não lançado]

### Adicionado

- **`pytest-cov` — cobertura de testes medida em todo `pytest`**, local e na
  CI. Configuração em dois lugares com papéis distintos:
  - **`.coveragerc`** (novo) — *o que* é medido: `source = .`, ou seja o
    projeto inteiro, inclusive módulos que nenhum teste importa. Assim
    `api.py` aparece no relatório com sua cobertura real em vez de sumir dele
    (antes, o módulo nunca importado simplesmente não era reportado). Exclui
    apenas `scratch/`, `frontend/` e entradas de script — nenhum código de
    produto é isentado.
  - **`pytest.ini`** — *como* roda: `--cov --cov-report=term-missing` e o piso
    `--cov-fail-under=35`, que **falha a execução** (e portanto a CI) se a
    cobertura total cair abaixo de 35%. É um guarda contra regressão
    silenciosa, não uma meta de número.
- **64 testes novos em 5 arquivos** (suíte: 5 → 69):
  - `test_metricas.py` — o "termômetro existencial": fórmula ponderada do
    nível, as 7 faixas qualitativas, histórico com `maxlen`, tendência e o
    desejo que emerge da distância até a meta.
  - `test_micelio.py` — nutrição sináptica: difusão proporcional ao peso,
    doação global com clamp biológico [0,1], brotamento de hifas (gatilho,
    isolados recentes, `max_hifas`, preferência por nó antigo) e o relatório
    do ciclo vital.
  - `test_estado_sono.py` — máquina de estados de sono e o payload
    `sono_fase` do WebSocket.
  - `test_pathfinding.py` — caminhos de raciocínio com subconsciente
    mockado: filtro de similaridade > 0.4, limite de 3 conceitos, degradação
    a `[]` quando o ChromaDB falha, Dijkstra com peso invertido (prefere
    aresta forte), `max_hops` e extração de contexto para o prompt.
  - `test_api_delta.py` — serialização do grafo e o delta que reduz o
    payload do WebSocket (nós novos/modificados/removidos, tolerância de
    0.001 na energia, normalização de direção `(A,B)` ≡ `(B,A)`, mudança de
    tipo da aresta), além dos endpoints `GET /api/estado` e `/api/grafo` via
    `TestClient`.
- **`.gitignore`**: `htmlcov/`, `.coverage`, `.ruff_cache/`.
- **README**: seção "Cobertura de testes", árvore de arquivos e tabela de
  verificações atualizadas.

### Corrigido

- **Consulta de caminho com nó isolado propagava `NodeNotFound`.**
  `PathfinderCognitivo.encontrar_caminho` monta `grafo_inv` só a partir das
  arestas, então um conceito existente no grafo mas sem nenhuma conexão não
  era copiado para ele — o `nx.shortest_path` lançava `NodeNotFound`, que o
  `except` não cobria (só `NetworkXNoPath`), e a exceção escapava para o
  chamador. Qualquer pergunta sobre um conceito isolado derrubava a consulta
  em vez de responder "sem caminho". Agora captura as duas exceções e o caso
  `conceito_a == conceito_b` retorna o caminho trivial `[no]` antes do
  Dijkstra.

### Cobertura

| | Antes | Depois |
| :--- | ---: | ---: |
| Total | 31,5%* | **48,2%** |
| `core/metricas.py` | 28,4% | **100%** |
| `core/pathfinding.py` | 14,0% | **100%** |
| `core/micelio.py` | 15,2% | **97,0%** |
| `core/estado_sono.py` | 84,6% | **100%** |
| `api.py` | não reportado | **29,7%** |

\* *O "antes" é a primeira medição com o `.coveragerc` já incluindo `api.py`
(283 stmts a 0%): sem o arquivo de configuração o número anterior de 37%
não contava a API de jeito nenhum.*

O que restou sem cobertura está concentrado em caminhos que dependem de
serviços externos — Ollama (`engine/fusao.py`), HTTP (`core/absorvedor.py`),
ChromaDB (`core/subconsciente.py`) — e nos endpoints WebSocket/POST da API,
que exigem mocks de rede para serem exercitados sem servidor real.

## [0.2.0] - 2026-10-27

Release de maturidade de engenharia: segurança do backend, tipagem do
frontend, suíte de testes executável de verdade e primeira esteira de CI.

### Segurança

- **SSRF fechado no `/api/absorver-url`.** O endpoint buscava qualquer URL que
  o cliente mandasse, o que permitia fazer o servidor consultar `127.0.0.1`, a
  rede local (`10.x`, `192.168.x`) e os metadados da cloud em
  `169.254.169.254` — estes devolvem as credenciais da máquina. A nova
  `validar_e_resolver_url()` valida esquema, recusa credenciais na URL, bloqueia
  hosts proibidos e checa **todos** os IPs resolvidos contra `ip.is_global`.
- **DNS rebinding eliminado.** Os IPs validados são devolvidos junto do erro e
  o `extrair_texto_url` conecta **no IP aprovado**, mantendo o hostname original
  no `Host` e no SNI (o certificado TLS continua sendo verificado contra o
  domínio). Sem isso o `httpx` resolveria o hostname de novo na hora de conectar
  e um domínio poderia responder uma IP pública na validação e uma interna no
  fetch.
- **Redirecionamentos validados salto a salto.** `follow_redirects=True` virou
  um loop manual de no máximo 5 saltos, cada um passando pela mesma validação —
  caso contrário um link público redirecionando para a rede interna contornava
  a checagem.
- **CORS restrito.** `allow_origins=["*"]` junto de `allow_credentials=True`
  era o pior dos dois mundos: o navegador rejeita `*` quando há credenciais,
  então nem funcionava, e ao mesmo tempo liberava qualquer site. Agora só as
  origens do dev-server do Vite (ampliáveis por `MILLA_CORS_ORIGINS`),
  `allow_credentials=False` e `GET, POST, OPTIONS` + `Content-Type` como
  métodos e headers permitidos.

### Adicionado

- **`.github/workflows/ci.yml`** — esteira com dois jobs: backend (Python 3.11
  e 3.13, `compileall` + `pytest`) e frontend (Node 22, `npm ci` + ESLint +
  `tsc -b` + build de produção).
- **`pytest.ini`** — `testpaths = scratch` e `asyncio_mode = auto`. Os quatro
  testes `async def` falhavam com *"async def functions are not natively
  supported"* porque o repositório nunca marcou `@pytest.mark.asyncio`.
- **`LICENSE`** — o README exibia o badge MIT, mas não havia arquivo de licença.
- **`CHANGELOG.md`** (este arquivo).
- **`config.VERSAO`** — fonte única de verdade da versão; `api.py`,
  `frontend/package.json` e a tag `v0.2.0` apontam para ela.
- **`ruff.toml`** — linter de Python com o conjunto de regras fixado
  explicitamente (`E4`, `E7`, `E9`, `F`) para que uma mudança de default numa
  versão futura não altere o que a CI valida. O `ruff` entrou também no
  `requirements.txt` e num passo da esteira.

### Corrigido

- **`chromadb` não estava no `requirements.txt`** apesar de ser importado por
  `core/subconsciente.py` — `pip install -r requirements.txt` não produzia um
  ambiente funcional.
- **Redirecionamento HTTP nunca era seguido.** `raise_for_status()` do httpx
  também estoura em `3xx`, então toda resposta de redirecionamento virava
  `Erro HTTP 301` em vez de avançar para o destino.
- **Falha de conexão derrubava o host inteiro.** Ao conectar no IP fixado, o
  primeiro IP que estourasse timeout encerrava a busca; agora o próximo
  endereço resolvido é tentado antes de desistir.
- **`conectar()` era referenciada antes da declaração** no `useConsciencia` —
  um erro de *temporal dead zone* real que estouraria no primeiro ciclo de
  reconexão automática do WebSocket.
- **Estado React atualizado no corpo de um efeito** (`AbsorcaoCognitiva`
  copiava a store para o estado local com `setState` dentro de `useEffect`);
  agora usa `store.subscribe()`.
- **Drag do grafo mantido em `useState`**, o que re-renderizava o componente a
  cada pixel arrastado; passou a viver num `useRef`, lido só nos handlers de
  mouse.

### Melhorado

- **Bundle de produção: 805 kB → 255 kB no primeiro load** (gzip 222 → 81 kB).
  Duas causas atacadas:
  1. O **Three.js** — de longe a maior dependência — saiu do bundle inicial.
     O núcleo dodecaédrico agora é carregado em paralelo via `React.lazy`, com
     um fallback que ocupa o mesmo slot de 400 px para o grid não pular.
  2. O `d3` guarda-chuva (que reexporta ~25 bibliotecas e **não declara
     `sideEffects`**, então o bundler não podia descartar nada) foi trocado por
     `d3-force`, a única parte que o código usa. `d3` e `@types/d3` saíram das
     dependências.
- **28 erros de ESLint → 0.** Cada um corrigido pela causa, não suprimido:
  `payload: any` do WebSocket virou união discriminada (`WSMessage`) em que cada
  variante declara os campos que o backend envia; `useRef<any[]>` na física do
  grafo virou `NoFisico`/`ArestaFisica` tipados com exposição de acessores
  estáveis (`lerNosFisica`/`lerArestasFisica`/`lerSimulacao`) em vez de o
  consumidor ler a ref na renderização.
- **Ruff: 32 achados → 0**, todos corrigidos no código e nenhum suprimido:
  13 imports mortos, 8 instruções na mesma linha, 3 variáveis atribuídas e nunca
  lidas (uma delas, `nos_antes` em `main.py`, era de um relatório de sono), 3
  f-strings sem placeholder, 3 nomes ambíguos (`l`), um import fora do topo e um
  import múltiplo na mesma linha.
- **Testes Python: 4 falhando → 5 passando.**
- `Iniciar_Milla.bat`, README e documentação interna atualizados.

### Limitações conhecidas

- O chunk assíncrono do Three.js ficou em 517 kB e ainda acusa o aviso de
  tamanho do Vite — é o preço de manter o WebGL fora do primeiro load.
- Não há cobertura de testes (`pytest-cov`) nem testes de frontend.
- Não há autenticação: Milla é um protótipo para rodar na sua máquina.

## [0.1.0] - 2026-05-18

Versão inicial publicada no GitHub: pipeline cognitivo completo (fusão,
feedback, micélio, sono, curiosidade e comitê multi-agente), dashboard React
com grafo d3-force, núcleo 3D e absorção de arquivos e URLs.

[Não lançado]: https://github.com/Churinti/Projeto-Milla/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Churinti/Projeto-Milla/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Churinti/Projeto-Milla/tree/v0.1.0
