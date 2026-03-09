/**
 * OrderPreview — итоговый список выбранных табаков перед отправкой заказа.
 */

import type { SelectedItem } from './TobaccoSelector';

interface OrderPreviewProps {
  items: SelectedItem[];
}

export default function OrderPreview({ items }: OrderPreviewProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="hb-preview">
      <p className="hb-section-label">Ваш заказ</p>
      <ul className="hb-preview-list">
        {items.map((item) => (
          <li key={item.tobacco.id} className="hb-preview-item">
            <span className="hb-preview-tobacco">
              {item.tobacco.name}
              <span className="hb-preview-brand"> — {item.tobacco.brand}</span>
            </span>
          </li>
        ))}
      </ul>
      <div className="hb-preview-total">
        Итого: {items.length} {items.length === 1 ? 'табак' : 'табака'}
      </div>
    </div>
  );
}
