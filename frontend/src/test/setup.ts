import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// O jsdom não calcula layout, então `scrollIntoView` não existe. O console do
// chat chama o método a cada mensagem/token — sem este stub a renderização
// estoura com "scrollIntoView is not a function".
Element.prototype.scrollIntoView = () => {};

// Com `globals: false` o Testing Library não registra a limpeza automática
// (ela depende de um `afterEach` global), então desmontamos explicitamente.
afterEach(() => {
  cleanup();
});
