import { computed, inject, Service } from '@angular/core';
import { Account } from './account';
import { Product, ProductStore } from './products';

export interface Group {
  id: string;
  name: string;
  productIds: number[];
  collapsed: boolean;
}

/** A group with its active products in order; `group` is null for the ungrouped rest. */
export interface Section {
  group: Group | null;
  products: Product[];
}

/** User-made product groups, saved with the account. */
@Service()
export class GroupStore {
  private readonly store = inject(ProductStore);
  private readonly account = inject(Account);

  // Archived ids stay in their group, so a restored product returns to it
  readonly groups = computed(() => this.account.settings().groups);

  readonly sections = computed<Section[]>(() => {
    const products = this.store.products();
    const byId = new Map(products.map((p) => [p.id, p]));
    const grouped = new Set<number>();
    const sections: Section[] = this.groups().map((group) => ({
      group,
      products: group.productIds.flatMap((id) => {
        const product = byId.get(id);
        if (!product || grouped.has(id)) return [];
        grouped.add(id);
        return [product];
      }),
    }));
    sections.push({ group: null, products: products.filter((p) => !grouped.has(p.id)) });
    return sections;
  });

  /** Whether all, some or none of the section's products are on the dashboard. */
  shownState(section: Section): 'all' | 'some' | 'none' {
    const slots = this.store.slots();
    const shown = section.products.filter((p) => slots.has(p.id)).length;
    if (shown === 0) return 'none';
    return shown === section.products.length ? 'all' : 'some';
  }

  /** Hides the whole section if it is all shown, otherwise shows as many as fit. */
  toggleShown(section: Section): void {
    const ids = section.products.map((p) => p.id);
    this.store.setShown(ids, this.shownState(section) !== 'all');
  }

  create(name: string): void {
    const group = { id: crypto.randomUUID(), name, productIds: [], collapsed: false };
    this.set((groups) => [...groups, group]);
  }

  rename(id: string, name: string): void {
    this.update(id, (group) => ({ ...group, name }));
  }

  toggleCollapsed(id: string): void {
    this.update(id, (group) => ({ ...group, collapsed: !group.collapsed }));
  }

  /** Removes the group; its products become ungrouped. */
  remove(id: string): void {
    this.set((groups) => groups.filter((g) => g.id !== id));
  }

  /** Drops a permanently deleted product from every group. */
  forget(productId: number): void {
    this.set((groups) =>
      groups.map((g) => ({ ...g, productIds: g.productIds.filter((id) => id !== productId) })),
    );
  }

  /**
   * Moves a product into a group, or out of all groups when `to` is null. `index` is its
   * position among the products that group shows, as drag and drop reports it.
   */
  move(productId: number, to: string | null, index = Number.POSITIVE_INFINITY): void {
    const target = this.sections().find((s) => (s.group?.id ?? null) === to);
    // Positions count only shown products; archived ids hidden in the group are skipped
    const before = target?.products.map((p) => p.id).filter((id) => id !== productId)[index];
    this.set((groups) =>
      groups.map((g) => {
        const ids = g.productIds.filter((id) => id !== productId);
        if (g.id === to)
          ids.splice(before === undefined ? ids.length : ids.indexOf(before), 0, productId);
        return { ...g, productIds: ids };
      }),
    );
  }

  private update(id: string, change: (group: Group) => Group): void {
    this.set((groups) => groups.map((g) => (g.id === id ? change(g) : g)));
  }

  private set(change: (groups: Group[]) => Group[]): void {
    this.account.update({ groups: change(this.groups()) });
  }
}
