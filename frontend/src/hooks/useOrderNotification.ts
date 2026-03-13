/**
 * useOrderNotification — звук + вибрация при новом заказе (T-094).
 * Использует Web Audio API для воспроизведения двух коротких тонов.
 */

import { useCallback, useEffect, useRef } from 'react';

export function useOrderNotification() {
  const audioCtxRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    return () => {
      void audioCtxRef.current?.close();
    };
  }, []);

  const notify = useCallback(() => {
    // Vibration API (mobile devices)
    if (navigator.vibrate) {
      navigator.vibrate([100, 50, 100]);
    }

    // Web Audio API — два коротких восходящих тона
    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
        audioCtxRef.current = new AudioContext();
      }
      const ctx = audioCtxRef.current;

      const playTone = (freq: number, startAt: number, duration: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(freq, startAt);
        gain.gain.setValueAtTime(0.25, startAt);
        gain.gain.exponentialRampToValueAtTime(0.001, startAt + duration);
        osc.start(startAt);
        osc.stop(startAt + duration);
      };

      const now = ctx.currentTime;
      playTone(880, now, 0.15);
      playTone(1100, now + 0.2, 0.15);
    } catch {
      // Audio not available — ignore silently
    }
  }, []);

  return { notify };
}
