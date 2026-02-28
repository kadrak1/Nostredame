import { useEffect, useState } from 'react';
import api from '../../api/client';

interface VenueInfo {
  id: number;
  name: string;
  address: string;
  phone: string;
  working_hours: Record<string, { open: string; close: string }> | null;
}

export default function AdminDashboard() {
  const [venue, setVenue] = useState<VenueInfo | null>(null);

  useEffect(() => {
    api.get<VenueInfo>('/venue/detail').then((r) => setVenue(r.data)).catch(() => {});
  }, []);

  return (
    <div className="admin-page">
      <h1>Обзор</h1>

      {venue && (
        <div className="info-cards">
          <div className="info-card">
            <h3>Заведение</h3>
            <p className="info-value">{venue.name}</p>
            <p className="info-muted">{venue.address}</p>
          </div>
          <div className="info-card">
            <h3>Телефон</h3>
            <p className="info-value">{venue.phone || '—'}</p>
          </div>
          <div className="info-card">
            <h3>Режим работы</h3>
            {venue.working_hours ? (
              <div className="schedule">
                {Object.entries(venue.working_hours).map(([day, hours]) => (
                  <div key={day} className="schedule-row">
                    <span className="schedule-day">{DAY_LABELS[day] ?? day}</span>
                    <span>{hours.open}–{hours.close}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="info-muted">Не задан</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const DAY_LABELS: Record<string, string> = {
  mon: 'Пн',
  tue: 'Вт',
  wed: 'Ср',
  thu: 'Чт',
  fri: 'Пт',
  sat: 'Сб',
  sun: 'Вс',
};
