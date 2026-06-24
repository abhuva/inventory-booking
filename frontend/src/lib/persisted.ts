export function readStoredString(key: string, fallback = ''): string {
  if (typeof localStorage === 'undefined') {
    return fallback;
  }
  return localStorage.getItem(key) ?? fallback;
}

export function readStoredBoolean(key: string, fallback = false): boolean {
  const value = readStoredString(key, fallback ? 'true' : 'false');
  return value === 'true';
}

export function writeStoredValue(key: string, value: string | boolean): void {
  if (typeof localStorage === 'undefined') {
    return;
  }
  localStorage.setItem(key, String(value));
}
