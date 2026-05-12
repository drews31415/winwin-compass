"use client";

import { useCallback, useEffect, useState } from "react";

export const DIGITAL_CARE_MODE_KEY = "digital-care-mode";

function applyDigitalCareMode(enabled: boolean) {
  document.documentElement.classList.toggle("digital-care-mode", enabled);
}

export function useDigitalCareMode() {
  const [enabled, setEnabledState] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(DIGITAL_CARE_MODE_KEY) === "true";
    setEnabledState(stored);
    applyDigitalCareMode(stored);
  }, []);

  const setEnabled = useCallback((value: boolean) => {
    setEnabledState(value);
    localStorage.setItem(DIGITAL_CARE_MODE_KEY, String(value));
    applyDigitalCareMode(value);
  }, []);

  return { enabled, setEnabled };
}
