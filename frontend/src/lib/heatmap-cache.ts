import type { AvailabilityHeatmap } from '$lib/api';

type CachedHeatmap = {
  key: string;
  value: AvailabilityHeatmap;
};

let cachedHeatmap: CachedHeatmap | null = null;

export function readCachedHeatmap(key: string): AvailabilityHeatmap | null {
  return cachedHeatmap?.key === key ? cachedHeatmap.value : null;
}

export function writeCachedHeatmap(key: string, value: AvailabilityHeatmap): void {
  cachedHeatmap = { key, value };
}
