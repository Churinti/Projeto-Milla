# Milla · Frontend

Painel holográfico do Projeto Milla: **Vite 8 + React 19 + TypeScript**, com
Three.js para o núcleo dodecaédrico, d3-force + Canvas 2D para o grafo de
conceitos e Zustand para o estado global.

> Este é o frontend do projeto — a documentação completa (arquitetura, API,
> segurança e guia de instalação) está no [README raiz](../README.md).

## Desenvolvimento

```bash
npm ci          # instala exatamente o package-lock.json
npm run dev     # dev server em http://localhost:5173
```

O `vite.config.ts` faz proxy de `/api` e `/ws` para `http://127.0.0.1:8000`,
então o backend precisa estar rodando (`python api.py` na raiz do projeto).

Ao abrir o painel de outro dispositivo da rede, o backend exige `MILLA_TOKEN` e
este app mostra a tela de acesso antes de montar o dashboard — o passo a passo
está no README da raiz, em “Acesso pela rede local”.

## Scripts

| Script | O que faz |
| :--- | :--- |
| `npm run dev` | Dev server com HMR |
| `npm run lint` | ESLint (regras React, React Hooks e TypeScript) |
| `npm test` | Vitest + Testing Library (jsdom), uma passada |
| `npm run test:watch` | Vitest em modo watch |
| `npm run test:coverage` | Cobertura com relatório HTML em `coverage/` (piso de 45%) |
| `npm run build` | `tsc -b` (type-check) e depois o bundle de produção em `dist/` |
| `npm run preview` | Serve o build de produção localmente |

## Testes

```bash
npm test               # executa a suíte uma vez
npm run test:watch     # reexecuta ao salvar
npm run test:coverage  # coverage/index.html navegável
```

- **Ambiente:** `jsdom`, configurado em [`vitest.config.ts`](./vitest.config.ts)
  (que reaproveita os plugins do `vite.config.ts`).
- **Setup:** [`src/test/setup.ts`](./src/test/setup.ts) registra os matchers do
  `@testing-library/jest-dom`, desmonta a árvore entre os testes e cria o stub
  de `scrollIntoView` (o jsdom não calcula layout).
- **Organização:** cada módulo testado tem seu `*.test.ts(x)` ao lado.
- **WebSocket:** `useConsciencia` é exercitado com um socket falso que expõe as
  constantes estáticas (`OPEN`, `CONNECTING`) e permite disparar abertura,
  mensagens, quedas e reconexão sem servidor real.
- **Limite conhecido:** `GrafoNeon` (Canvas 2D) e `Dodecaedro3D` (WebGL) não
  têm testes — o jsdom não implementa esses contextos.

## Estrutura

```
src/
├── components/
│   ├── AbsorcaoCognitiva.tsx   # Upload Drag & Drop de arquivos e absorção de URL
│   ├── Dodecaedro3D.tsx        # Núcleo 3D (Three.js), reage à fase cognitiva
│   ├── GrafoNeon.tsx           # Grafo em Canvas 2D com física d3-force
│   ├── MetricsPanel.tsx        # HUD circular de telemetria do Self
│   ├── PortaoAcesso.tsx        # Tela de token (monta o HUD só após liberar)
│   └── TerminalChat.tsx        # Console com streaming token-a-token
├── hooks/
│   ├── useConsciencia.ts       # Conector WebSocket tipado, com auto-reconnect
│   └── useGrafoFisica.ts       # Simulação de física inercial d3-force
├── lib/
│   └── auth.ts                 # Token na sessão, Bearer e subprotocolo do WS
├── store/
│   └── conscienciaStore.ts     # Estado global (Zustand) e aplicação de deltas
├── types/
│   └── consciencia.ts          # Tipos compartilhados, incl. a união WSMessage
├── test/setup.ts               # jsdom + jest-dom + cleanup
├── App.tsx                     # Grid HUD principal
├── App.test.tsx                # Smoke test da composição do HUD
└── index.css                   # Variáveis neon / glassmorphism
```

## Notas de implementação

- **`WSMessage` é uma união discriminada.** Cada variante declara exatamente os
  campos que o backend envia naquele `type`, então o `switch` em
  `useConsciencia.ts` valida os payloads sem `any`.
- **`useGrafoFisica` expõe acessores** (`lerNosFisica`, `lerArestasFisica`,
  `lerSimulacao`) em vez dos arrays da ref: os arrays mudam a cada tick da
  simulação, e colocá-los nas dependências de um `useEffect` dispararia o
  efeito em loop.
- **O nó sob arrasto vive num ref** (`GrafoNeon`), não em `useState` — mantê-lo
  em estado re-renderizaria o canvas a cada pixel arrastado.
- **A sincronização com a store usa `store.subscribe()`** em vez de `setState`
  no corpo de um efeito.
