import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

// Reaproveita os plugins e aliases do vite.config.ts (React, Tailwind) para que
// os testes importem exatamente os mesmos módulos que o dev server e o build.
export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      // Zera mocks/espionagens entre testes; sem isso um `vi.mock` de um teste
      // vaza para o seguinte.
      clearMocks: true,
      restoreMocks: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'html'],
        include: ['src/**/*.{ts,tsx}'],
        // `src/types` só declara tipos (nenhuma linha executável) e o
        // `main.tsx` é o bootstrap do React. Nada de código de produto é
        // isentado: os componentes visuais entram no denominador.
        exclude: ['src/main.tsx', 'src/test/**', 'src/types/**', 'src/**/*.test.{ts,tsx}'],
        // Guarda contra regressão silenciosa, não meta de número: é o mesmo
        // papel do --cov-fail-under=35 do backend.
        thresholds: { statements: 45, lines: 45 },
      },
    },
  })
);
