import type { Asset } from '$lib/api';

type NumericValue = number | string | null | undefined;

export function numericValue(value: NumericValue): number | null {
  if (value === null || value === undefined || value === '') {
    return null;
  }
  const parsed = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function calculateDailyRate(
  replacementValue: NumericValue,
  recoupDays: NumericValue,
  maintenanceCostPerDay: NumericValue,
  profitMarginPercent: NumericValue
): number | null {
  const baseValue = numericValue(replacementValue);
  const days = numericValue(recoupDays);
  const maintenance = numericValue(maintenanceCostPerDay);
  const margin = numericValue(profitMarginPercent);
  if (baseValue === null || days === null || days <= 0 || maintenance === null || margin === null) {
    return null;
  }
  return (baseValue / days + maintenance) * (1 + margin / 100);
}

export function chargedRentalDays(startsAt: string, endsAt: string): number | null {
  const start = Date.parse(startsAt);
  const end = Date.parse(endsAt);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) {
    return null;
  }
  return Math.max(1, Math.ceil((end - start) / 86_400_000));
}

export function estimatedRentalLineTotal(
  asset: Asset | undefined,
  startsAt: string,
  endsAt: string,
  quantity: number | null | undefined
): number | null {
  const dailyRate = numericValue(asset?.rental_daily_rate);
  const days = chargedRentalDays(startsAt, endsAt);
  if (dailyRate === null || days === null) {
    return null;
  }
  return dailyRate * days * (quantity ?? 1);
}

export function formatEuro(value: NumericValue, maximumFractionDigits = 2): string {
  const parsed = numericValue(value);
  if (parsed === null) {
    return 'Not priced';
  }
  return new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits
  }).format(parsed);
}
