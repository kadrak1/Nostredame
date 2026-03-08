import { useState } from 'react';
import { useGuest } from '../guest-auth';

interface PhoneLoginProps {
  /** Called after successful login with the guest's name and phone they entered. */
  onSuccess: (name: string, phone: string) => void;
}

export default function PhoneLogin({ onSuccess }: PhoneLoginProps) {
  const { login } = useGuest();
  const [phone, setPhone] = useState('+7');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    // Always keep "+7" prefix; allow only up to 10 digits after it
    const digits = raw.replace(/\D/g, '').replace(/^7/, '').slice(0, 10);
    setPhone('+7' + digits);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    const digits = phone.replace(/\D/g, '');
    if (digits.length !== 11) {
      setError('Введите номер в формате +7XXXXXXXXXX');
      return;
    }

    setIsLoading(true);
    try {
      const result = await login(phone);
      onSuccess(result.name, phone);
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(typeof detail === 'string' ? detail : 'Ошибка входа. Попробуйте ещё раз.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="guest-login-box">
      <p className="guest-login-hint">Войдите, чтобы данные заполнились автоматически</p>
      {error && (
        <div className="error" style={{ marginBottom: '0.75rem' }}>
          {error}
        </div>
      )}
      <form className="guest-login-row" onSubmit={handleSubmit}>
        <input
          type="tel"
          value={phone}
          onChange={handleChange}
          placeholder="+7XXXXXXXXXX"
          maxLength={12}
          autoComplete="tel"
        />
        <button
          type="submit"
          className="btn btn-primary guest-login-btn"
          disabled={isLoading || phone.length < 12}
        >
          {isLoading ? '...' : 'Войти'}
        </button>
      </form>
    </div>
  );
}
