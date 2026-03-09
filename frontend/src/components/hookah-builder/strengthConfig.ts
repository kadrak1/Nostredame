/**
 * Shared strength-level config — separated from StrengthSelector.tsx
 * to satisfy react-refresh/only-export-components (no non-component exports in .tsx files).
 */

import type { StrengthLevel } from './StrengthSelector';

export const STRENGTH_CONFIG: Record<StrengthLevel, { label: string; range: string; color: string }> = {
  light:  { label: 'Лёгкий',  range: '1–4',  color: '#2ECC71' },
  medium: { label: 'Средний', range: '5–7',  color: '#F39C12' },
  strong: { label: 'Крепкий', range: '8–10', color: '#E94560' },
};

export const STRENGTH_RANGE: Record<StrengthLevel, [number, number]> = {
  light:  [1, 4],
  medium: [5, 7],
  strong: [8, 10],
};
