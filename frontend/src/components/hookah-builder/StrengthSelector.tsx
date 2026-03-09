/**
 * StrengthSelector — кнопки выбора крепости кальяна.
 * Лёгкий (1-4) / Средний (5-7) / Крепкий (8-10)
 */

import { STRENGTH_CONFIG } from './strengthConfig';

export type StrengthLevel = 'light' | 'medium' | 'strong';

interface StrengthSelectorProps {
  value: StrengthLevel | null;
  onChange: (level: StrengthLevel) => void;
}

export default function StrengthSelector({ value, onChange }: StrengthSelectorProps) {
  return (
    <div className="hb-strength-selector">
      <p className="hb-section-label">Выберите крепость</p>
      <div className="hb-strength-buttons">
        {(Object.entries(STRENGTH_CONFIG) as [StrengthLevel, typeof STRENGTH_CONFIG[StrengthLevel]][]).map(
          ([level, cfg]) => (
            <button
              key={level}
              type="button"
              className={`hb-strength-btn ${value === level ? 'active' : ''}`}
              style={value === level ? { borderColor: cfg.color, color: cfg.color } : undefined}
              onClick={() => onChange(level)}
            >
              <span className="hb-strength-name">{cfg.label}</span>
              <span className="hb-strength-range">{cfg.range}</span>
            </button>
          )
        )}
      </div>
    </div>
  );
}
