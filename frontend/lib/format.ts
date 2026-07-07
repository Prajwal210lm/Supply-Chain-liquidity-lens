export function formatAED(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M AED'
  if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K AED'
  return value.toLocaleString() + ' AED'
}

export function formatValue(value: number): string {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(1) + 'M'
  if (value >= 1_000) return (value / 1_000).toFixed(1) + 'K'
  return value.toLocaleString()
}
