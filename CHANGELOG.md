# Changelog

Todas as mudanças notáveis do Projeto Milla ficam registradas aqui.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e o
projeto adota [Versionamento Semântico](https://semver.org/lang/pt-BR/).
A versão corrente vive em `config.VERSAO` — é dali que o `api.py`, este arquivo
e a tag do git leem.

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

- **28 erros de ESLint → 0.** Cada um corrigido pela causa, não suprimido:
  `payload: any` do WebSocket virou união discriminada (`WSMessage`) em que cada
  variante declara os campos que o backend envia; `useRef<any[]>` na física do
  grafo virou `NoFisico`/`ArestaFisica` tipados com exposição de acessores
  estáveis (`lerNosFisica`/`lerArestasFisica`/`lerSimulacao`) em vez de o
  consumidor ler a ref na renderização.
- **Testes Python: 4 falhando → 5 passando.**
- `Iniciar_Milla.bat`, README e documentação interna atualizados.

### Limitações conhecidas

- O bundle de produção ficou em ~805 kB (aviso do Vite sobre chunks > 500 kB);
  ainda não passou por code-splitting.
- Não há linter de Python configurado no repositório.

## [0.1.0] - 2026-05-18

Versão inicial publicada no GitHub: pipeline cognitivo completo (fusão,
feedback, micélio, sono, curiosidade e comitê multi-agente), dashboard React
com grafo d3-force, núcleo 3D e absorção de arquivos e URLs.

[0.2.0]: https://github.com/Churinti/Projeto-Milla/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Churinti/Projeto-Milla/tree/v0.1.0
