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

## Scripts

| Script | O que faz |
| :--- | :--- |
| `npm run dev` | Dev server com HMR |
| `npm run lint` | ESLint (regras React, React Hooks e TypeScript) |
| `npm run build` | `tsc -b` (type-check) e depois o bundle de produção em `dist/` |
| `npm run preview` | Serve o build de produção localmente |

## Estrutura

```
src/
├── components/
│   ├── AbsorcaoCognitiva.tsx   # Upload Drag & Drop de arquivos e absorção de URL
│   ├── Dodecaedro3D.tsx        # Núcleo 3D (Three.js), reage à fase cognitiva
│   ├── GrafoNeon.tsx           # Grafo em Canvas 2D com física d3-force
│   ├── MetricsPanel.tsx        # HUD circular de telemetria do Self
│   └── TerminalChat.tsx        # Console com streaming token-a-token
├── hooks/
│   ├── useConsciencia.ts       # Conector WebSocket tipado, com auto-reconnect
│   └── useGrafoFisica.ts       # Simulação de física inercial d3-force
├── store/
│   └── conscienciaStore.ts     # Estado global (Zustand) e aplicação de deltas
├── types/
│   └── consciencia.ts          # Tipos compartilhados, incl. a união WSMessage
├── App.tsx                     # Grid HUD principal
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
