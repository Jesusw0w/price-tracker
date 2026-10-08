import { HttpClient, HttpErrorResponse, httpResource } from '@angular/common/http';
import { computed, inject, linkedSignal, Service, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

export interface PricePoint {
  date: string;
  price: number;
}

export interface Product {
  id: number;
  url: string;
  name: string | null;
  currency: string | null;
  history: PricePoint[];
}

export interface Range {
  label: string;
  days: number | null;
}

// Dark categorical slots, validated on the chart surface; the order is what keeps them CVD-safe
export const SERIES_COLORS = [
  '#3987e5',
  '#d95926',
  '#199e70',
  '#c98500',
  '#d55181',
  '#008300',
  '#9085e9',
  '#e66767',
];

export const RANGES: Range[] = [
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: 'All', days: null },
];

const DAY_MS = 86_400_000;
const DEFAULT_CHARTED = 4;

const formats = new Map<string, Intl.NumberFormat>();

/** A plain number when the currency is unknown, e.g. before the first scrape. */
export function money(value: number, currency: string | null): string {
  const key = currency ?? '';
  let format = formats.get(key);
  if (!format) {
    format = new Intl.NumberFormat(
      'es-ES',
      currency ? { style: 'currency', currency } : { minimumFractionDigits: 2 },
    );
    formats.set(key, format);
  }
  return format.format(value);
}

/** Before the first scrape there is no name, so the shop's host stands in. */
export const label = (p: Product) => p.name ?? new URL(p.url).hostname;

@Service()
export class ProductStore {
  private readonly http = inject(HttpClient);
  private readonly list = httpResource<Product[]>(() => '/api/products', { defaultValue: [] });

  readonly products = computed(() => (this.list.hasValue() ? this.list.value() : []));
  readonly loadError = computed(() => this.list.error());
  readonly needsToken = computed(() => {
    const error = this.list.error();
    return error instanceof HttpErrorResponse && error.status === 401;
  });
  readonly range = signal<Range>(RANGES[RANGES.length - 1]);

  // product id -> colour slot; a slot sticks to its product so toggling one never repaints the rest
  readonly slots = linkedSignal<Product[], Map<number, number>>({
    source: this.products,
    computation: (products, previous) =>
      previous?.source.length
        ? new Map([...previous.value].filter(([id]) => products.some((p) => p.id === id)))
        : new Map(products.slice(0, DEFAULT_CHARTED).map((p, i) => [p.id, i])),
  });

  // Ranges count back from the newest scrape, not today, so stale data still charts
  readonly scoped = computed(() => {
    const products = this.products();
    const days = this.range().days;
    if (days === null) return products;
    const latest = Math.max(...products.flatMap((p) => p.history.map((h) => Date.parse(h.date))));
    return products.map((p) => ({
      ...p,
      history: p.history.filter((h) => Date.parse(h.date) >= latest - days * DAY_MS),
    }));
  });

  readonly chartFull = computed(() => this.slots().size >= SERIES_COLORS.length);

  color(id: number): string | undefined {
    const slot = this.slots().get(id);
    return slot === undefined ? undefined : SERIES_COLORS[slot];
  }

  toggle(id: number): void {
    this.slots.update((slots) => {
      const next = new Map(slots);
      if (next.delete(id)) return next;
      const taken = new Set(next.values());
      const free = SERIES_COLORS.findIndex((_, i) => !taken.has(i));
      if (free !== -1) next.set(id, free);
      return next;
    });
  }

  reload(): void {
    this.list.reload();
  }

  /** Resolves to a message for the user, or undefined on success. */
  async add(link: string): Promise<string | undefined> {
    try {
      const product = await firstValueFrom(this.http.post<Product>('/api/products', { link }));
      this.list.value.update((products) => [...products, product]);
      return undefined;
    } catch (e) {
      const detail = e instanceof HttpErrorResponse ? e.error?.detail : undefined;
      return typeof detail === 'string' ? detail : 'Could not add the product, try again';
    }
  }

  async remove(id: number): Promise<void> {
    try {
      await firstValueFrom(this.http.delete(`/api/products/${id}`));
      this.list.value.update((products) => products.filter((p) => p.id !== id));
    } catch {
      this.list.reload();
    }
  }
}
