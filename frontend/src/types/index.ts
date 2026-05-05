// Wire-shape types from the backend live in `./api`; UI/chart-shape
// types built by `lib/transformers/` live in `./ui`. This barrel
// re-exports both so existing `import { Foo } from '@/types'`
// call sites continue to work unchanged.
export * from './api';
export * from './ui';
