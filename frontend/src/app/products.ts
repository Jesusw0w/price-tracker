import { HttpClient, HttpErrorResponse, httpResource } from '@angular/common/http';
import { computed, inject, linkedSignal, Service, signal, untracked } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { Account } from './account';

export interface PricePoint {
  date: string;
  price: number;
}

export interface Product {
  id: number;
  url: string;
  name: string | null;
  currency: string | null;
  /** Visible to every user. */
  public: boolean;
  /** Only the owner may archive, delete or share it; the rest are others' public ones. */
  mine: boolean;
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

interface SlotSource {
  products: Product[];
  settled: boolean;
}

@Service()
export class ProductStore {
  private readonly http = inject(HttpClient);
  private readonly account = inject(Account);
  private readonly list = httpResource<Product[]>(() => '/api/products', { defaultValue: [] });

  readonly products = computed(() => (this.list.hasValue() ? this.list.value() : []));
  readonly loadError = computed(() => this.list.error());
  readonly range = signal<Range>(RANGES[RANGES.length - 1]);

  // Fetched only while the product dialog is open
  readonly showArchived = signal(false);
  private readonly archivedList = httpResource<Product[]>(
    () => (this.showArchived() ? '/api/products/archived' : undefined),
    { defaultValue: [] },
  );
  readonly archived = computed(() =>
    this.archivedList.hasValue() ? this.archivedList.value() : [],
  );

  // Products shown on the dashboard: id -> colour slot. A slot sticks to its product so
  // toggling one never repaints the rest. Products and settings load in parallel, so
  // nothing is shown until the saved selection has arrived.
  readonly slots = linkedSignal<SlotSource, Map<number, number>>({
    source: () => ({ products: this.products(), settled: this.account.ready() }),
    computation: ({ products, settled }, previous) => {
      const known = (id: number) => products.some((p) => p.id === id);
      if (previous?.source.settled && previous.source.products.length) {
        return new Map([...previous.value].filter(([id]) => known(id)));
      }
      if (!settled) return new Map<number, number>();
      // Untracked: saving the selection must not feed back into computing it
      const saved = untracked(() => this.account.settings().dashboard);
      return saved
        ? new Map(saved.filter(([id, slot]) => known(id) && slot < SERIES_COLORS.length))
        : new Map(products.slice(0, DEFAULT_CHARTED).map((p, i) => [p.id, i]));
    },
  });

  readonly shown = computed(() => this.products().filter((p) => this.slots().has(p.id)));

  // Ranges count back from the newest scrape, not today, so stale data still charts
  readonly scoped = computed(() => {
    const products = this.shown();
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
    this.setShown([id], !this.slots().has(id));
  }

  /** Shows or hides several products at once; showing stops when the chart is full. */
  setShown(ids: number[], visible: boolean): void {
    this.slots.update((slots) => {
      const next = new Map(slots);
      for (const id of ids) {
        if (!visible) {
          next.delete(id);
          continue;
        }
        if (next.has(id)) continue;
        const taken = new Set(next.values());
        const free = SERIES_COLORS.findIndex((_, i) => !taken.has(i));
        if (free === -1) break;
        next.set(id, free);
      }
      return next;
    });
    this.account.update({ dashboard: [...this.slots()] });
  }

  reload(): void {
    this.list.reload();
  }

  /** Resolves to a message for the user, or undefined on success. */
  async add(link: string): Promise<string | undefined> {
    try {
      const product = await firstValueFrom(this.http.post<Product>('/api/products', { link }));
      this.list.value.update((products) => [...products, product]);
      if (!this.chartFull()) this.toggle(product.id);
      return undefined;
    } catch (e) {
      const detail = e instanceof HttpErrorResponse ? e.error?.detail : undefined;
      return typeof detail === 'string' ? detail : 'Could not add the product, try again';
    }
  }

  /** Shares one of the user's products with every user, or makes it private again. */
  async setPublic(id: number, visible: boolean): Promise<void> {
    try {
      const product = await firstValueFrom(
        this.http.patch<Product>(`/api/products/${id}`, { public: visible }),
      );
      this.list.value.update((products) => products.map((p) => (p.id === id ? product : p)));
    } catch {
      this.list.reload();
    }
  }

  /** Stops scraping the product; its history stays and it can be restored. */
  async archive(id: number): Promise<void> {
    try {
      await firstValueFrom(this.http.delete(`/api/products/${id}`));
      this.list.value.update((products) => products.filter((p) => p.id !== id));
      this.archivedList.reload();
    } catch {
      this.list.reload();
    }
  }

  /** Deletes the product, active or archived, with its price history. Cannot be undone. */
  async deletePermanently(id: number): Promise<void> {
    try {
      await firstValueFrom(
        this.http.delete(`/api/products/${id}`, { params: { permanent: true } }),
      );
      this.list.value.update((products) => products.filter((p) => p.id !== id));
      this.archivedList.value.update((products) => products.filter((p) => p.id !== id));
    } catch {
      this.list.reload();
      this.archivedList.reload();
    }
  }

  /** Resolves to a message for the user, or undefined on success. */
  async restore(product: Product): Promise<string | undefined> {
    const message = await this.add(product.url);
    if (!message) this.archivedList.value.update((all) => all.filter((p) => p.id !== product.id));
    return message;
  }
}
