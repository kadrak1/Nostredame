/**
 * StrengthSelector — кнопки выбора крепости кальяна.
 * Лёгкий (1-4) / Средний (5-7) / Крепкий (8-10)
 */

export type StrengthLevel = 'light' | 'medium' | 'strong';

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
