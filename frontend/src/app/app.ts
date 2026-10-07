import { Component, computed, inject } from '@angular/core';
import { PriceChart, Series } from './price-chart/price-chart';
import { PriceTable } from './price-table/price-table';
import { label, ProductStore, RANGES } from './products';
import { Sidebar } from './sidebar/sidebar';

@Component({
  imports: [Sidebar, PriceChart, PriceTable],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly store = inject(ProductStore);
  protected readonly ranges = RANGES;

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
