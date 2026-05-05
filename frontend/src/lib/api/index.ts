// Domain-split API layer. Existing call sites importing from
// `@/lib/api` resolve here via the barrel re-export.
export * from './expenses';
export * from './receipts';
export * from './analytics';
export * from './query';
