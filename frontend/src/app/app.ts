import { Component, computed, inject } from '@angular/core';
import { Account, isUnauthorized } from './account';
import { Background } from './background';
import { DashboardPicker } from './dashboard-picker/dashboard-picker';
import { PriceChart, Series } from './price-chart/price-chart';
import { PriceTable } from './price-table/price-table';
import { label, ProductStore, RANGES } from './products';
import { Sidebar } from './sidebar/sidebar';

@Component({
  imports: [Sidebar, DashboardPicker, PriceChart, PriceTable],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly store = inject(ProductStore);
  protected readonly account = inject(Account);
  protected readonly background = inject(Background);
  protected readonly ranges = RANGES;

  // A session can also expire after the page loaded
  protected readonly signedOut = computed(
    () => this.account.signedOut() || isUnauthorized(this.store.loadError()),
  );
  protected readonly loadError = computed(
    () => this.account.loadError() || !!this.store.loadError(),
  );

  protected readonly series = computed<Series[]>(() =>
    this.store.scoped().flatMap((p) => {
      const color = this.store.color(p.id);
      return color
        ? [
            {
              label: label(p),
              color,
              currency: p.currency,
              points: p.history.map((h) => ({ x: Date.parse(h.date), y: h.price })),
            },
          ]
        : [];
    }),
  );
}
