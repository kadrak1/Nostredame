import { useQuery } from '@tanstack/react-query';
import api from '../../api/client';

interface VenueInfo {
  id: number;
  name: string;
  address: string;
  phone: string;
  working_hours: Record<string, { open: string; close: string }> | null;
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

export default function AdminDashboard() {
  const { data: venue, isLoading, isError } = useQuery({
    queryKey: ['venue-detail'],
    queryFn: () => api.get<VenueInfo>('/venue/detail').then((r) => r.data),
  });

  return (
    <div className="admin-page">
      <h1>Обзор</h1>

      {isLoading && <p className="info-muted">Загрузка...</p>}
      {isError && <p className="error">Не удалось загрузить данные заведения</p>}

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
