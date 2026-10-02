import { Component, inject, signal } from '@angular/core';
import { form, FormField, FormRoot, required } from '@angular/forms/signals';
import { eur, ProductStore, SERIES_COLORS } from '../products';

@Component({
  selector: 'app-sidebar',
  imports: [FormRoot, FormField],
  template: `
    <div class="brand">
      <span class="logo" aria-hidden="true"></span>
      <div>
        <p class="title">GPU Price Tracker</p>
        <p class="subtitle">Amazon.es</p>
      </div>
    </div>

    <form [formRoot]="addForm" class="add">
      <label for="link">Track a product</label>
      <div class="row">
        <input
          id="link"
          [formField]="addForm.link"
          placeholder="Amazon.es link or ASIN"
          autocomplete="off"
          [attr.aria-invalid]="showError()"
          aria-describedby="link-help"
        />
        <button type="submit" [disabled]="addForm().submitting()">Add</button>
      </div>
      <p id="link-help" class="help" [class.error]="showError()" [attr.role]="showError() ? 'alert' : null">
        {{ showError() ? addForm.link().errors()[0].message : 'Prices appear after the next scrape.' }}
      </p>
    </form>

    <section aria-labelledby="tracked-heading">
      <div class="section-head">
        <h2 id="tracked-heading">Tracked</h2>
        <span class="count">{{ store.slots().size }}/{{ maxCharted }} charted</span>
      </div>
      <ul>
        @for (product of store.products(); track product.asin) {
          @let color = store.color(product.asin);
          @let last = product.history.at(-1);
          <li [class.charted]="color">
            <label>
              <input
                type="checkbox"
                [checked]="!!color"
                [disabled]="!color && store.chartFull()"
                (change)="store.toggle(product.asin)"
              />
              <span class="key" [style.background]="color ?? null" aria-hidden="true"></span>
              <span class="name" [title]="product.name ?? product.asin">{{ product.name ?? product.asin }}</span>
            </label>
            <span class="price">{{ last ? eur(last.price) : 'Pending' }}</span>
            <button
              type="button"
              class="remove"
              (click)="store.remove(product.asin)"
              [attr.aria-label]="'Stop tracking ' + (product.name ?? product.asin)"
            >
              ×
            </button>
          </li>
        } @empty {
          <li class="empty">Nothing tracked yet.</li>
        }
      </ul>
    </section>
  `,
  styleUrl: './sidebar.css',
})
export class Sidebar {
  protected readonly store = inject(ProductStore);
  protected readonly eur = eur;
  protected readonly maxCharted = SERIES_COLORS.length;

  private readonly model = signal({ link: '' });
  protected readonly addForm = form(
    this.model,
    (s) => required(s.link, { message: 'Paste a product link or ASIN' }),
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

  protected showError(): boolean {
    const link = this.addForm.link();
    return link.touched() && link.invalid();
  }
}
