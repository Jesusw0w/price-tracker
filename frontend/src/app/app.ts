import {
  afterNextRender,
  Component,
  computed,
  DOCUMENT,
  DestroyRef,
  ElementRef,
  inject,
  Injector,
  signal,
  viewChild,
} from '@angular/core';
import { Account, isUnauthorized } from './account';
import { Background } from './background';
import { DashboardPicker } from './dashboard-picker/dashboard-picker';
import { Login } from './login/login';
import { PriceChart, Series } from './price-chart/price-chart';
import { PriceTable } from './price-table/price-table';
import { label, ProductStore, RANGES, SERIES_COLORS } from './products';
import { Sidebar } from './sidebar/sidebar';

@Component({
  imports: [Sidebar, DashboardPicker, Login, PriceChart, PriceTable],
  selector: 'app-root',
  templateUrl: './app.html',
  styleUrl: './app.css',
  host: { '(document:keydown.escape)': 'closePanel()' },
})
export class App {
  protected readonly store = inject(ProductStore);
  protected readonly account = inject(Account);
  protected readonly background = inject(Background);
  protected readonly ranges = RANGES;
  protected readonly maxShown = SERIES_COLORS.length;

  /** Only used on narrow screens, where the sidebar becomes a slide-in panel. */
  protected readonly panelOpen = signal(false);
  private readonly panelToggle = viewChild<ElementRef<HTMLButtonElement>>('panelToggle');
  private readonly panelClose = viewChild<ElementRef<HTMLButtonElement>>('panelClose');
  private readonly injector = inject(Injector);

  constructor() {
    // Widening the window turns the panel back into the sidebar, so it must not stay "open"
    const narrow = inject(DOCUMENT).defaultView?.matchMedia?.('(max-width: 56rem)');
    if (narrow) {
      const onChange = (e: MediaQueryListEvent) => {
        if (!e.matches) this.panelOpen.set(false);
      };
      narrow.addEventListener('change', onChange);
      inject(DestroyRef).onDestroy(() => narrow.removeEventListener('change', onChange));
    }
  }

  protected openPanel(): void {
    this.panelOpen.set(true);
    afterNextRender(() => this.panelClose()?.nativeElement.focus(), { injector: this.injector });
  }

  protected closePanel(): void {
    if (!this.panelOpen()) return;
    this.panelOpen.set(false);
    // The dashboard is inert until the next render, so focus can only move back after it
    afterNextRender(() => this.panelToggle()?.nativeElement.focus(), { injector: this.injector });
  }

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
