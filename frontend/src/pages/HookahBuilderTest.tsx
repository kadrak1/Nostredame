/**
 * DEV-ONLY: тестовая страница для HookahBuilder.
 * Маршрут /hookah-test — не для прода.
 */

import { useState } from 'react';
import HookahBuilder from '../components/hookah-builder/HookahBuilder';

export default function HookahBuilderTest() {
  const [bookingId, setBookingId] = useState('');
  const [phone, setPhone] = useState('+79991234567');
  const [started, setStarted] = useState(false);
  const [result, setResult] = useState<'complete' | 'skip' | null>(null);

  if (result) {
    return (
      <div style={{ maxWidth: 480, margin: '60px auto', padding: 24, textAlign: 'center' }}>
        <h2 style={{ color: result === 'complete' ? '#2ECC71' : '#aaa' }}>
          {result === 'complete' ? '✅ onComplete вызван' : '⏭ onSkip вызван'}
        </h2>
        <button
          style={{ marginTop: 24, padding: '10px 24px', cursor: 'pointer' }}
          onClick={() => { setResult(null); setStarted(false); }}
        >
          Тестировать снова
        </button>
      </div>
    );
  }

  if (!started) {
    return (
      <div style={{ maxWidth: 400, margin: '60px auto', padding: 24 }}>
        <h2 style={{ marginBottom: 24 }}>🧪 HookahBuilder тест</h2>
        <p style={{ color: '#aaa', marginBottom: 16, fontSize: 14 }}>
          Введи ID существующей брони и телефон гостя
        </p>
        <label style={{ display: 'block', marginBottom: 12 }}>
          Booking ID
          <input
            type="number"
            value={bookingId}
            onChange={e => setBookingId(e.target.value)}
            placeholder="1"
            style={{ display: 'block', width: '100%', marginTop: 4, padding: '8px 12px', fontSize: 16 }}
          />
        </label>
        <label style={{ display: 'block', marginBottom: 20 }}>
          Телефон гостя
          <input
            type="text"
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="+79991234567"
            style={{ display: 'block', width: '100%', marginTop: 4, padding: '8px 12px', fontSize: 16 }}
          />
        </label>
        <button
          disabled={!bookingId || !phone}
          onClick={() => setStarted(true)}
          style={{ width: '100%', padding: '12px', fontSize: 16, cursor: 'pointer', background: '#E94560', color: '#fff', border: 'none', borderRadius: 8 }}
        >
          Открыть HookahBuilder →
        </button>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 640, margin: '0 auto', padding: '24px 16px' }}>
      <div style={{ marginBottom: 16, fontSize: 13, color: '#666' }}>
        booking_id={bookingId} · phone={phone}
      </div>
      <HookahBuilder
        bookingId={Number(bookingId)}
        guestPhone={phone}
        onComplete={() => setResult('complete')}
        onSkip={() => setResult('skip')}
      />
    </div>
  );
}
