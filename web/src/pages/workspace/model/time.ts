export function secondsToMilliseconds(value: string, maximum = 60000): number | null {
  if (!/^(?:\d+(?:\.\d*)?|\.\d+)$/.test(value)) return null;
  const [whole, fraction = ''] = value.split('.');
  // Decimal digits preserve every integer ms; floating-point multiplication can miss 1.001 s.
  if (/[1-9]/.test(fraction.slice(3))) return null;
  const ms = Number(whole) * 1000 + Number(fraction.slice(0, 3).padEnd(3, '0'));
  return Number.isSafeInteger(ms) && ms >= 1 && ms <= maximum ? ms : null;
}
