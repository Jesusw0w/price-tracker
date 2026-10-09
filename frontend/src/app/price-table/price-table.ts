import { Component, computed, inject } from '@angular/core';
import { DatePipe } from '@angular/common';
import { label, money, ProductStore, staleHint } from '../products';

@Component({
  selector: 'app-price-table',
  imports: [DatePipe],
  template: `
    <div class="scroll">
      <table>
        <caption>
          Prices in the selected range
        </caption>
        <thead>
          <tr>
            <th scope="col">Product</th>
            <th scope="col" class="num">Now</th>
            <th scope="col" class="num">Lowest</th>
            <th scope="col" class="num">Highest</th>
            <th scope="col" class="num">Above lowest</th>
          </tr>
        </thead>
        <tbody>
          @for (row of rows(); track row.id) {
            <tr>
              <th scope="row">
                <span class="product">
                  <span
                    class="key"
                    [style.background]="store.color(row.id) ?? null"
                    aria-hidden="true"
                  ></span>
                  <a
                    [href]="row.url"
                    target="_blank"
                    rel="noopener noreferrer"
                    [title]="row.name"
                    >{{ row.name }}</a
                  >
                </span>
                @if (row.unavailableSince; as since) {
                  <span class="sub gone" [title]="row.hint">
                    No longer sold here since {{ since | date: 'd MMM y' }}
                  </span>
                }
              </th>
              @if (row.stats; as s) {
                <td class="num">{{ money(s.now, row.currency) }}</td>
                <td class="num">
                  {{ money(s.low, row.currency) }}
                  <span class="sub">{{ s.lowDate | date: 'd MMM' }}</span>
                </td>
                <td class="num">{{ money(s.high, row.currency) }}</td>
                <td class="num">
                  @if (s.now <= s.low) {
                    <span class="badge"><span aria-hidden="true">✓</span> At lowest</span>
                  } @else {
                    +{{ ((s.now / s.low - 1) * 100).toFixed(1) }}%
                  }
                </td>
              } @else {
                <td colspan="4" class="pending">No prices in this range yet</td>
              }
            </tr>
          } @empty {
            <tr>
              <td colspan="5" class="pending">
                No products shown. Tick some in the sidebar or in Customize.
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styles: `
    .scroll {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem;
    }
    caption {
      caption-side: top;
      font-family: var(--mono);
      padding-bottom: 0.75rem;
      text-align: left;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-2);
    }
    th,
    td {
      padding: 0.6rem 0.75rem;
      border-bottom: 1px solid var(--grid);
      text-align: left;
      white-space: nowrap;
    }
    thead th {
      font-weight: 500;
      color: var(--muted);
    }
    tbody th {
      font-weight: 400;
    }
    .product {
      display: flex;
      align-items: center;
      gap: 0.6rem;
      max-width: 26rem;
    }
    a {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--ink);
      text-decoration: none;
    }
    a:hover {
      color: var(--link);
      text-decoration: underline;
    }
    .num {
      font-family: var(--mono);
      font-size: 0.8125rem;
      text-align: right;
      font-variant-numeric: tabular-nums;
      color: var(--ink);
    }
    .sub {
      display: block;
      font-size: 0.75rem;
      color: var(--muted);
    }
    .sub.gone {
      color: var(--danger);
    }
    .key {
      flex: none;
      width: 14px;
      height: 2px;
      border-radius: 1px;
    }
    .badge {
      color: var(--good-text);
      font-weight: 600;
    }
    .pending {
      color: var(--muted);
    }
  `,
})
export class PriceTable {
  protected readonly store = inject(ProductStore);
  protected readonly money = money;

  protected readonly rows = computed(() =>
    this.store.scoped().map((p) => {
      const prices = p.history.map((h) => h.price);
      const low = Math.min(...prices);
      return {
        id: p.id,
        url: p.url,
        name: label(p),
        currency: p.currency,
        unavailableSince: p.unavailable_since,
        hint: staleHint(p) ?? '',
        stats: prices.length
          ? {
              now: prices[prices.length - 1],
              low,
              high: Math.max(...prices),
              lowDate: p.history.filter((h) => h.price === low).at(-1)?.date,
            }
          : null,
      };
    }),
  );
}
