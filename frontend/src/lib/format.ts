const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDateTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Date unavailable" : dateTimeFormatter.format(date);
}

export function shortenId(value: string): string {
  if (value.length <= 18) {
    return value;
  }
  return `${value.slice(0, 10)}…${value.slice(-6)}`;
}
