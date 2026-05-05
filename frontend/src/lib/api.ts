// Domain-split API layer lives in `./api/`. This shim keeps existing
// `import { foo } from '@/lib/api'` call sites working — Node module
// resolution prefers `api.ts` over `api/index.ts`, so we explicitly
// re-export the barrel.
export * from './api/index';
