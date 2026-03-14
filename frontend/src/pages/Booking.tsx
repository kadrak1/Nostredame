/**
 * Guest booking page — 4-step wizard:
 *   1. Date / time / guest count
 *   2. Table selection (read-only floor plan)
 *   3. Contact details
 *   4. Confirmation
 */

import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { Stage, Layer, Rect, Circle, Text, Line } from 'react-konva';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import api from '../api/client';
import { useGuest } from '../guest-auth';
import PhoneLogin from '../components/PhoneLogin';
import HookahBuilder from '../components/hookah-builder/HookahBuilder';

/* ------------------------------------------------------------------ */
/*  Types                                                               */
/* ------------------------------------------------------------------ */

type TableShape = 'rect' | 'circle';

interface TableData {
  id: number;
  number: number;
  capacity: number;
  x: number;
  y: number;
  width: number;
  height: number;
  shape: TableShape;
}

interface WallData {
  id: string;
  points: number[];
  strokeWidth: number;
}

interface FloorPlanData {
  width: number;
  height: number;
  walls: WallData[];
}

interface FloorPlanResponse {
  floor_plan: FloorPlanData | null;
  tables: TableData[];
}

interface BookingResult {
  id: number;
  table_id: number;
  date: string;
  time_from: string;
  time_to: string;
  guest_count: number;
  guest_name: string;
  status: string;
  notes: string;
  created_at: string;
}

interface Step1Data {
  date: string;
  time_from: string;
  time_to: string;
  guest_count: number;
}

interface Step3Data {
  guest_name: string;
  guest_phone: string;
  notes: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                           */
/* ------------------------------------------------------------------ */

const CANVAS_W = 1200;
const CANVAS_H = 800;
const GRID_SIZE = 20;

const COLORS = {
  canvasBg: '#0F1923',
  grid: '#1a2a4a',
  wall: '#8892A0',
  tableAvailable: '#2ECC71',
  tableAvailableStroke: '#27AE60',
  tableSelected: '#E94560',
  tableSelectedStroke: '#d63b54',
  tableBusy: '#3a3a4a',
  tableBusyStroke: '#4a4a5a',
  tableTooSmall: '#4a3a10',
  tableTooSmallStroke: '#6a5520',
  text: '#FFFFFF',
  textMuted: 'rgba(255,255,255,0.5)',
};

const STEPS = ['Дата и время', 'Выбор стола', 'Ваши данные', 'Подтверждение'];

/* ------------------------------------------------------------------ */
/*  Today's date helper                                                 */
/* ------------------------------------------------------------------ */

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/* ------------------------------------------------------------------ */
/*  StepIndicator                                                       */
/* ------------------------------------------------------------------ */

function StepIndicator({ current }: { current: number }) {
  return (
    <div className="bk-steps">
      {STEPS.map((label, idx) => (
        <div
          key={idx}
          className={`bk-step ${idx < current ? 'done' : ''} ${idx === current ? 'active' : ''}`}
        >
          <div className="bk-step-circle">
            {idx < current ? '✓' : idx + 1}
          </div>
          <span className="bk-step-label">{label}</span>
          {idx < STEPS.length - 1 && <div className="bk-step-line" />}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 1: DateTime                                                    */
/* ------------------------------------------------------------------ */

function Step1({
  data,
  onNext,
}: {
  data: Step1Data;
  onNext: (d: Step1Data) => void;
}) {
  const [date, setDate] = useState(data.date || todayISO());
  const [timeFrom, setTimeFrom] = useState(data.time_from || '18:00');
  const [timeTo, setTimeTo] = useState(data.time_to || '21:00');
  const [guests, setGuests] = useState(data.guest_count || 2);
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const today = new Date().toISOString().slice(0, 10);
    if (date < today) {
      setError('Нельзя бронировать в прошлом');
      return;
    }
    if (timeFrom >= timeTo) {
      setError('Время окончания должно быть позже начала');
      return;
    }
    onNext({ date, time_from: timeFrom, time_to: timeTo, guest_count: guests });
  };

  return (
    <form className="bk-card" onSubmit={handleSubmit}>
      <h2 className="bk-card-title">Когда придёте?</h2>

      {error && <div className="error">{error}</div>}

      <label>
        Дата
        <input
          type="date"
          value={date}
          min={todayISO()}
          onChange={(e) => setDate(e.target.value)}
          required
        />
      </label>

      <div className="bk-row">
        <label style={{ flex: 1 }}>
          Время прихода
          <input
            type="time"
            value={timeFrom}
            onChange={(e) => setTimeFrom(e.target.value)}
            required
          />
        </label>
        <label style={{ flex: 1 }}>
          Время ухода
          <input
            type="time"
            value={timeTo}
            onChange={(e) => setTimeTo(e.target.value)}
            required
          />
        </label>
      </div>

      <label>
        Количество гостей
        <input
          type="number"
          min={1}
          max={50}
          value={guests}
          onChange={(e) => setGuests(Number(e.target.value))}
          required
        />
      </label>

      <button type="submit" className="btn btn-primary bk-next-btn">
        Выбрать стол →
      </button>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 2: Table selection (read-only floor plan)                     */
/* ------------------------------------------------------------------ */

function Step2({
  step1,
  selectedTableId,
  onSelect,
  onNext,
  onBack,
}: {
  step1: Step1Data;
  selectedTableId: number | null;
  onSelect: (id: number) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  // Load all tables + floor plan layout
  const { data: floorData, isLoading: floorLoading, isError: floorError } = useQuery({
    queryKey: ['floor-plan'],
    queryFn: () => api.get<FloorPlanResponse>('/venue/floor-plan').then((r) => r.data),
    staleTime: 60_000,
  });

  // Load available table IDs for this time slot
  const { data: availableTables, isLoading: availLoading, isError: availError } = useQuery({
    queryKey: ['available-tables', step1.date, step1.time_from, step1.time_to, step1.guest_count],
    queryFn: () =>
      api
        .get<TableData[]>('/bookings/available-tables', {
          params: {
            date: step1.date,
            time_from: step1.time_from,
            time_to: step1.time_to,
            guests: step1.guest_count,
          },
        })
        .then((r) => r.data),
    staleTime: 30_000,
  });

  const availableIds = new Set((availableTables ?? []).map((t) => t.id));

  // Canvas responsive scaling
  useEffect(() => {
    const update = () => {
      if (containerRef.current) {
        const w = containerRef.current.offsetWidth;
        setScale(Math.min(1, (w - 4) / CANVAS_W));
      }
    };
    update();
    window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update);
  }, []);

  const walls = floorData?.floor_plan?.walls ?? [];
  const allTables = floorData?.tables ?? [];

  const isLoading = floorLoading || availLoading;

  // Memoize static grid lines — 60 vertical + 40 horizontal = 100 Konva nodes
  const gridLines = useMemo(() => {
    const vLines = Array.from({ length: Math.ceil(CANVAS_W / GRID_SIZE) + 1 }, (_, i) => (
      <Line key={`v${i}`} points={[i * GRID_SIZE, 0, i * GRID_SIZE, CANVAS_H]} stroke={COLORS.grid} strokeWidth={0.5} />
    ));
    const hLines = Array.from({ length: Math.ceil(CANVAS_H / GRID_SIZE) + 1 }, (_, i) => (
      <Line key={`h${i}`} points={[0, i * GRID_SIZE, CANVAS_W, i * GRID_SIZE]} stroke={COLORS.grid} strokeWidth={0.5} />
    ));
    return [...vLines, ...hLines];
  }, []);

  const selectedTable = allTables.find((t) => t.id === selectedTableId) ?? null;

  return (
    <div className="bk-card bk-card-wide">
      <h2 className="bk-card-title">Выберите стол</h2>

      <div className="bk-table-legend">
        <span className="bk-legend-dot" style={{ background: COLORS.tableAvailable }} />
        <span>Свободен</span>
        <span className="bk-legend-dot" style={{ background: COLORS.tableSelected }} />
        <span>Выбран</span>
        <span className="bk-legend-dot" style={{ background: COLORS.tableBusy }} />
        <span>Занят</span>
        <span className="bk-legend-dot" style={{ background: COLORS.tableTooSmall }} />
        <span>Мало мест</span>
      </div>

      {isLoading && <p className="info-muted">Загрузка плана зала...</p>}
      {floorError && <p className="error">Не удалось загрузить план зала. Попробуйте обновить страницу.</p>}
      {availError && <p className="error">Не удалось загрузить доступные столы</p>}

      {!isLoading && (
        <div className="bk-canvas-wrap" ref={containerRef}>
          <Stage
            width={CANVAS_W * scale}
            height={CANVAS_H * scale}
            scaleX={scale}
            scaleY={scale}
            style={{ background: COLORS.canvasBg, borderRadius: '8px', display: 'block' }}
          >
            {/* Grid */}
            <Layer listening={false}>{gridLines}</Layer>

            {/* Walls */}
            <Layer listening={false}>
              {walls.map((w) => (
                <Line
                  key={w.id}
                  points={w.points}
                  stroke={COLORS.wall}
                  strokeWidth={w.strokeWidth}
                  lineCap="round"
                />
              ))}
            </Layer>

            {/* Tables */}
            <Layer>
              {allTables.map((table) => {
                const available = availableIds.has(table.id);
                const selected = table.id === selectedTableId;
                const tooSmall = !available && table.capacity < step1.guest_count;
                const fill = selected
                  ? COLORS.tableSelected
                  : available
                  ? COLORS.tableAvailable
                  : tooSmall
                  ? COLORS.tableTooSmall
                  : COLORS.tableBusy;
                const stroke = selected
                  ? COLORS.tableSelectedStroke
                  : available
                  ? COLORS.tableAvailableStroke
                  : tooSmall
                  ? COLORS.tableTooSmallStroke
                  : COLORS.tableBusyStroke;

                const clickProps = available
                  ? {
                      onClick: () => onSelect(table.id),
                      onTap: () => onSelect(table.id),
                    }
                  : {};

                return (
                  <React.Fragment key={table.id}>
                    {table.shape === 'circle' ? (
                      <Circle
                        x={table.x + table.width / 2}
                        y={table.y + table.height / 2}
                        radius={table.width / 2}
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={2}
                        {...clickProps}
                      />
                    ) : (
                      <Rect
                        x={table.x}
                        y={table.y}
                        width={table.width}
                        height={table.height}
                        fill={fill}
                        stroke={stroke}
                        strokeWidth={2}
                        cornerRadius={6}
                        {...clickProps}
                      />
                    )}
                    <Text
                      x={table.x}
                      y={table.y + table.height / 2 - 14}
                      width={table.width}
                      align="center"
                      text={`#${table.number}`}
                      fontSize={14}
                      fontStyle="bold"
                      fill={COLORS.text}
                      listening={false}
                    />
                    <Text
                      x={table.x}
                      y={table.y + table.height / 2 + 2}
                      width={table.width}
                      align="center"
                      text={`${table.capacity} чел.`}
                      fontSize={11}
                      fill={available ? COLORS.textMuted : 'rgba(255,255,255,0.25)'}
                      listening={false}
                    />
                  </React.Fragment>
                );
              })}
            </Layer>
          </Stage>
        </div>
      )}

      {selectedTable && (
        <div className="bk-selected-info">
          Выбран стол <strong>#{selectedTable.number}</strong> — до {selectedTable.capacity} гостей
        </div>
      )}

      <div className="bk-nav">
        <button type="button" className="btn fp-btn-secondary" onClick={onBack}>
          ← Назад
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!selectedTableId}
          onClick={onNext}
        >
          Далее →
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 3: Contact details                                             */
/* ------------------------------------------------------------------ */

function Step3({
  data,
  onNext,
  onBack,
  isSubmitting,
  submitError,
}: {
  data: Step3Data;
  onNext: (d: Step3Data) => void;
  onBack: () => void;
  isSubmitting: boolean;
  submitError: string;
}) {
  const { guest, logout } = useGuest();
  const [name, setName] = useState(data.guest_name);
  const [phone, setPhone] = useState(data.guest_phone);
  const [notes, setNotes] = useState(data.notes);
  const [error, setError] = useState('');
  // Derive effective name from user input or restored guest session — no effect needed
  const effectiveName = name || guest?.name || '';

  const handleLoginSuccess = (guestName: string, guestPhone: string) => {
    setName(guestName);
    setPhone(guestPhone);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isSubmitting) return;  // rely on isPending as source of truth
    setError('');

    const digits = phone.replace(/\D/g, '');
    if (digits.length < 10 || digits.length > 15) {
      setError('Введите корректный номер телефона (10–15 цифр)');
      return;
    }
    if (effectiveName.trim().length < 2) {
      setError('Введите ваше имя');
      return;
    }
    onNext({ guest_name: effectiveName.trim(), guest_phone: phone.trim(), notes: notes.trim() });
  };

  return (
    <form className="bk-card" onSubmit={handleSubmit}>
      <h2 className="bk-card-title">Ваши данные</h2>

      {/* Guest auth block */}
      {guest ? (
        <div className="guest-banner">
          <span>Вы вошли как <strong>{guest.name}</strong> ({guest.phone_masked})</span>
          <button
            type="button"
            className="guest-banner-logout"
            onClick={() => { logout(); setName(''); setPhone(''); }}
          >
            Выйти
          </button>
        </div>
      ) : (
        <PhoneLogin onSuccess={handleLoginSuccess} />
      )}

      {(error || submitError) && <div className="error">{error || submitError}</div>}

      <label>
        Имя и фамилия
        <input
          type="text"
          autoComplete="name"
          placeholder="Иван Петров"
          value={effectiveName}
          onChange={(e) => setName(e.target.value)}
          maxLength={100}
          required
        />
      </label>

      <label>
        Телефон
        <input
          type="tel"
          autoComplete="tel"
          placeholder="+7 999 123-45-67"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          required
        />
      </label>

      <label>
        Комментарий <span className="bk-optional">(необязательно)</span>
        <textarea
          placeholder="Особые пожелания, аллергии, повод..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          maxLength={500}
          rows={3}
        />
      </label>

      <div className="bk-nav">
        <button type="button" className="btn fp-btn-secondary" onClick={onBack}>
          ← Назад
        </button>
        <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
          {isSubmitting ? 'Бронируем...' : 'Забронировать'}
        </button>
      </div>
    </form>
  );
}

/* ------------------------------------------------------------------ */
/*  Step 4: Confirmation                                                */
/* ------------------------------------------------------------------ */

function Step4({
  booking,
  step1,
  tableNumber,
  onAddHookah,
  hookahOrderCount = 0,
}: {
  booking: BookingResult;
  step1: Step1Data;
  tableNumber: number;
  onAddHookah?: () => void;
  hookahOrderCount?: number;
}) {
  const statusLabels: Record<string, string> = {
    pending: 'Ожидает подтверждения',
    confirmed: 'Подтверждена',
    cancelled: 'Отменена',
    completed: 'Завершена',
  };

  return (
    <div className="bk-card bk-success">
      <div className="bk-success-icon">✓</div>
      <h2 className="bk-card-title">Бронирование принято!</h2>
      <p className="bk-success-sub">
        Мы свяжемся с вами для подтверждения.
      </p>

      <div className="bk-summary">
        <div className="bk-summary-row">
          <span>Номер брони</span>
          <strong>#{booking.id}</strong>
        </div>
        <div className="bk-summary-row">
          <span>Стол</span>
          <strong>{tableNumber > 0 ? `#${tableNumber}` : `ID ${booking.table_id}`}</strong>
        </div>
        <div className="bk-summary-row">
          <span>Дата</span>
          <strong>
            {new Date(step1.date + 'T00:00:00').toLocaleDateString('ru-RU', {
              day: 'numeric',
              month: 'long',
              year: 'numeric',
            })}
          </strong>
        </div>
        <div className="bk-summary-row">
          <span>Время</span>
          <strong>{step1.time_from} — {step1.time_to}</strong>
        </div>
        <div className="bk-summary-row">
          <span>Гостей</span>
          <strong>{step1.guest_count}</strong>
        </div>
        <div className="bk-summary-row">
          <span>Имя</span>
          <strong>{booking.guest_name}</strong>
        </div>
        <div className="bk-summary-row">
          <span>Статус</span>
          <strong className="bk-status-pending">
            {statusLabels[booking.status] ?? booking.status}
          </strong>
        </div>
      </div>

      <p className="bk-save-hint">
        Сохраните номер брони <strong>#{booking.id}</strong> — он потребуется для отмены.
      </p>

      {onAddHookah && (
        <div className="bk-hookah-upsell">
          {hookahOrderCount > 0 && (
            <p className="bk-hookah-count">
              Кальянов в предзаказе: <strong>{hookahOrderCount}</strong>
            </p>
          )}
          <button
            type="button"
            className="btn btn-primary bk-next-btn"
            onClick={onAddHookah}
          >
            {hookahOrderCount > 0 ? 'Добавить ещё кальян' : 'Предзаказать кальян'}
          </button>
        </div>
      )}

      <Link to="/" className={`btn bk-next-btn ${onAddHookah ? 'fp-btn-secondary' : 'btn-primary'}`}>
        На главную
      </Link>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Booking page                                                   */
/* ------------------------------------------------------------------ */

export default function Booking() {
  const [step, setStep] = useState(0);

  const [step1Data, setStep1Data] = useState<Step1Data>({
    date: '',
    time_from: '',
    time_to: '',
    guest_count: 2,
  });
  const [selectedTableId, setSelectedTableId] = useState<number | null>(null);
  const [step3Data, setStep3Data] = useState<Step3Data>({
    guest_name: '',
    guest_phone: '',
    notes: '',
  });
  const [submitError, setSubmitError] = useState('');
  const [bookingResult, setBookingResult] = useState<BookingResult | null>(null);
  const [hookahPhase, setHookahPhase] = useState<'idle' | 'building'>('idle');
  const [hookahCount, setHookahCount] = useState(0);

  // All tables for resolving table number in confirmation
  const { data: floorData } = useQuery({
    queryKey: ['floor-plan'],
    queryFn: () => api.get<FloorPlanResponse>('/venue/floor-plan').then((r) => r.data),
    staleTime: 60_000,
  });
  const allTables = floorData?.tables ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) =>
      api.post<BookingResult>('/bookings', payload).then((r) => r.data),
    onSuccess: (data) => {
      setBookingResult(data);
      setStep(3);
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Ошибка при создании брони. Попробуйте ещё раз.';
      setSubmitError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    },
  });

  const handleStep1 = useCallback((data: Step1Data) => {
    setStep1Data(data);
    setSelectedTableId(null);
    setStep(1);
  }, []);

  const { mutate: doCreateBooking } = createMutation;
  const handleStep3 = useCallback(
    (data: Step3Data) => {
      setStep3Data(data);
      setSubmitError('');
      doCreateBooking({
        table_id: selectedTableId,
        date: step1Data.date,
        time_from: step1Data.time_from + ':00',
        time_to: step1Data.time_to + ':00',
        guest_count: step1Data.guest_count,
        guest_name: data.guest_name,
        guest_phone: data.guest_phone,
        notes: data.notes,
      });
    },
    [selectedTableId, step1Data, doCreateBooking]
  );

  const tableNumber =
    allTables.find((t) => t.id === (bookingResult?.table_id ?? selectedTableId))?.number ?? 0;

  return (
    <div className="bk-page">
      <div className="bk-container">
        {/* Header */}
        <div className="bk-header">
          <Link to="/" className="bk-back-link">
            ← Hookah Book
          </Link>
          <h1 className="bk-title">Забронировать стол</h1>
        </div>

        {/* Step indicator (hide on success screen) */}
        {step < 3 && <StepIndicator current={step} />}

        {/* Steps */}
        {step === 0 && (
          <Step1 data={step1Data} onNext={handleStep1} />
        )}

        {step === 1 && (
          <Step2
            step1={step1Data}
            selectedTableId={selectedTableId}
            onSelect={setSelectedTableId}
            onNext={() => setStep(2)}
            onBack={() => setStep(0)}
          />
        )}

        {step === 2 && (
          <Step3
            data={step3Data}
            onNext={handleStep3}
            onBack={() => setStep(1)}
            isSubmitting={createMutation.isPending}
            submitError={submitError}
          />
        )}

        {step === 3 && !bookingResult && (
          <p className="info-muted">Загрузка...</p>
        )}

        {step === 3 && bookingResult && hookahPhase === 'idle' && (
          <Step4
            booking={bookingResult}
            step1={step1Data}
            tableNumber={tableNumber}
            onAddHookah={() => setHookahPhase('building')}
            hookahOrderCount={hookahCount}
          />
        )}

        {step === 3 && bookingResult && hookahPhase === 'building' && (
          <HookahBuilder
            bookingId={bookingResult.id}
            guestPhone={step3Data.guest_phone}
            onComplete={() => { setHookahCount((c) => c + 1); setHookahPhase('idle'); }}
            onSkip={() => setHookahPhase('idle')}
          />
        )}
      </div>
    </div>
  );
}
