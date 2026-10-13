import { Component, computed, inject, signal } from '@angular/core';
import { form, FormField, FormRoot, required } from '@angular/forms/signals';
import { CdkDrag, CdkDragHandle, CdkDropList, CdkDropListGroup } from '@angular/cdk/drag-drop';
import { GroupStore, Section } from '../groups';
import { NewGroup } from '../new-group';
import { label, money, Product, ProductStore, SERIES_COLORS, staleHint } from '../products';

type Flag = 'charted' | 'lowest' | 'dropped' | 'pending';
type Sort = 'manual' | 'high' | 'low';

const WEEK_MS = 7 * 86_400_000;

const FLAGS: { id: Flag; label: string }[] = [
  { id: 'charted', label: 'charted' },
  { id: 'lowest', label: 'at lowest' },
  { id: 'dropped', label: 'dropped 7d' },
  { id: 'pending', label: 'pending' },
];

const SORTS: Record<Sort, { label: string; next: Sort }> = {
  manual: { label: 'manual', next: 'high' },
  high: { label: 'price ↓', next: 'low' },
  low: { label: 'price ↑', next: 'manual' },
};

const latest = (p: Product) => p.history.at(-1)?.price;

/** Whether the latest price is the lowest the product has had. */
const atLowest = (p: Product) =>
  !!p.history.length && latest(p)! <= Math.min(...p.history.map((h) => h.price));

/** Whether the price is lower than it was a week before the latest scrape. */
function droppedThisWeek(p: Product): boolean {
  const last = p.history.at(-1);
  if (!last) return false;
  const cutoff = Date.parse(last.date) - WEEK_MS;
  const before = [...p.history].reverse().find((h) => Date.parse(h.date) <= cutoff);
  return !!before && last.price < before.price;
}

@Component({
  selector: 'app-sidebar',
  imports: [FormRoot, FormField, CdkDropListGroup, CdkDropList, CdkDrag, CdkDragHandle, NewGroup],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.css',
})
export class Sidebar {
  protected readonly store = inject(ProductStore);
  protected readonly groups = inject(GroupStore);
  protected readonly money = money;
  protected readonly label = label;
  protected readonly staleHint = staleHint;
  protected readonly maxShown = SERIES_COLORS.length;
  protected readonly flagList = FLAGS;
  protected readonly sorts = SORTS;

  protected readonly query = signal('');
  protected readonly flags = signal<ReadonlySet<Flag>>(new Set());
  protected readonly sort = signal<Sort>('manual');

  /** Drag and drop positions count every product, so it is off while the list is narrowed. */
  protected readonly filtering = computed(
    () => !!this.query().trim() || this.flags().size > 0 || this.sort() !== 'manual',
  );

  protected readonly counts = computed(() => {
    const products = this.store.products();
    return Object.fromEntries(
      FLAGS.map(({ id }) => [id, products.filter((p) => this.matches(p, id)).length]),
    ) as Record<Flag, number>;
  });

  protected readonly sections = computed<Section[]>(() => {
    const query = this.query().trim().toLowerCase();
    const flags = [...this.flags()];
    const sort = this.sort();
    const keep = (p: Product) =>
      (!query || label(p).toLowerCase().includes(query)) &&
      flags.every((flag) => this.matches(p, flag));
    // Pending products have no price, so they sort last either way
    const price = (p: Product) =>
      latest(p) ?? (sort === 'low' ? Number.POSITIVE_INFINITY : Number.NEGATIVE_INFINITY);

    const sections = this.groups.sections().map((section) => {
      const products = section.products.filter(keep);
      if (sort === 'high') products.sort((a, b) => price(b) - price(a));
      if (sort === 'low') products.sort((a, b) => price(a) - price(b));
      return { ...section, products };
    });
    return this.filtering() ? sections.filter((s) => s.products.length) : sections;
  });

  protected readonly noMatches = computed(
    () => this.filtering() && this.store.products().length > 0 && !this.sections().length,
  );

  private readonly model = signal({ link: '' });
  protected readonly addForm = form(
    this.model,
    (s) => required(s.link, { message: 'Paste a product link' }),
    {
      submission: {
        action: async (f) => {
          const message = await this.store.add(f.link().value());
          if (message) return { kind: 'server', message, fieldTree: f.link };
          f().reset({ link: '' });
          return undefined;
        },
      },
    },
  );

  protected readonly showError = computed(() => {
    const link = this.addForm.link();
    return link.touched() && link.invalid();
  });

  protected toggleFlag(flag: Flag): void {
    this.flags.update((flags) => {
      const next = new Set(flags);
      if (!next.delete(flag)) next.add(flag);
      return next;
    });
  }

  protected clearFilters(): void {
    this.query.set('');
    this.flags.set(new Set());
    this.sort.set('manual');
  }

  private matches(p: Product, flag: Flag): boolean {
    switch (flag) {
      case 'charted':
        return this.store.slots().has(p.id);
      case 'lowest':
        return atLowest(p);
      case 'dropped':
        return droppedThisWeek(p);
      case 'pending':
        return !p.history.length;
    }
  }

  protected atLowest = atLowest;
}
