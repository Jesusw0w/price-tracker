import { Component, inject, signal } from '@angular/core';
import { form, FormField, FormRoot, required } from '@angular/forms/signals';
import { label, money, ProductStore, SERIES_COLORS } from '../products';

@Component({
  selector: 'app-sidebar',
  imports: [FormRoot, FormField],
  template: `
    <div class="brand">
      <span class="logo" aria-hidden="true"></span>
      <div>
        <p class="title">Price Tracker</p>
        <p class="subtitle">Any online shop</p>
      </div>
    </div>

    <form [formRoot]="addForm" class="add">
      <label for="link">Track a product</label>
      <div class="row">
        <input
          id="link"
          [formField]="addForm.link"
          placeholder="https:// product link"
          autocomplete="off"
          [attr.aria-invalid]="showError()"
          aria-describedby="link-help"
        />
        <button type="submit" [disabled]="addForm().submitting()">Add</button>
      </div>
      <p
        id="link-help"
        class="help"
        [class.error]="showError()"
        [attr.role]="showError() ? 'alert' : null"
      >
        {{
          showError() ? addForm.link().errors()[0].message : 'Prices appear after the next scrape.'
        }}
      </p>
    </form>

    <section aria-labelledby="tracked-heading">
      <div class="section-head">
        <h2 id="tracked-heading">Tracked</h2>
        <span class="count">{{ store.slots().size }}/{{ maxCharted }} charted</span>
      </div>
      <ul>
        @for (product of store.products(); track product.id) {
          @let color = store.color(product.id);
          @let last = product.history.at(-1);
          @let name = label(product);
          <li [class.charted]="color">
            <label>
              <input
                type="checkbox"
                [checked]="!!color"
                [disabled]="!color && store.chartFull()"
                (change)="store.toggle(product.id)"
              />
              <span class="key" [style.background]="color ?? null" aria-hidden="true"></span>
              <span class="name" [title]="name">{{ name }}</span>
            </label>
            <span class="price">{{ last ? money(last.price, product.currency) : 'Pending' }}</span>
            <button
              type="button"
              class="remove"
              (click)="store.remove(product.id)"
              [attr.aria-label]="'Stop tracking ' + name"
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
  protected readonly money = money;
  protected readonly label = label;
  protected readonly maxCharted = SERIES_COLORS.length;

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

  protected showError(): boolean {
    const link = this.addForm.link();
    return link.touched() && link.invalid();
  }
}
