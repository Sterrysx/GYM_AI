import { useState, useCallback, useRef } from 'react';

/**
 * Lightweight toast manager.
 * Returns { toast, showToast } where toast = { msg, isError, visible }.
 */
export function useToast(duration = 2400) {
  const [toast, setToast] = useState({ msg: '', isError: false, visible: false });
  const timer = useRef(null);

  const showToast = useCallback((msg, isError = false) => {
    clearTimeout(timer.current);
    setToast({ msg, isError, visible: true });
    timer.current = setTimeout(() => {
      setToast((prev) => ({ ...prev, visible: false }));
    }, duration);
  }, [duration]);

  return { toast, showToast };
}
