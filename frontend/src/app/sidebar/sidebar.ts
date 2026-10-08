import { Component, computed, inject, signal } from '@angular/core';
import { form, FormField, FormRoot, required } from '@angular/forms/signals';
import { CdkDrag, CdkDragHandle, CdkDropList, CdkDropListGroup } from '@angular/cdk/drag-drop';
import { GroupStore } from '../groups';
import { NewGroup } from '../new-group';
import { label, money, ProductStore, SERIES_COLORS } from '../products';

@Component({
  selector: 'app-sidebar',
  imports: [FormRoot, FormField, CdkDropListGroup, CdkDropList, CdkDrag, CdkDragHandle, NewGroup],
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
        <span class="count">{{ store.slots().size }}/{{ maxShown }} shown</span>
      </div>
      <div class="groups" cdkDropListGroup>
        @for (section of groups.sections(); track section.group?.id ?? 'ungrouped') {
          @let group = section.group;
          @let state = groups.shownState(section);
          @if (group || groups.groups().length) {
            <div class="group-head">
              @if (group) {
                <button
                  type="button"
                  class="chevron"
                  [class.collapsed]="group.collapsed"
                  (click)="groups.toggleCollapsed(group.id)"
                  [attr.aria-expanded]="!group.collapsed"
                  [attr.aria-label]="'Show or hide ' + group.name"
                >
                  <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
                </button>
              }
              <label>
                <input
                  type="checkbox"
                  [checked]="state === 'all'"
                  [indeterminate]="state === 'some'"
                  [disabled]="!section.products.length"
                  (change)="groups.toggleShown(section)"
                />
                <span class="group-name">{{ group?.name ?? 'Ungrouped' }}</span>
              </label>
              <span class="count">{{ section.products.length }}</span>
            </div>
          }
          @if (!group?.collapsed) {
            <ul
              cdkDropList
              [cdkDropListData]="group?.id ?? null"
              [cdkDropListSortingDisabled]="!group"
              (cdkDropListDropped)="
                groups.move($event.item.data, $event.container.data, $event.currentIndex)
              "
              [attr.aria-label]="group?.name ?? 'Ungrouped'"
            >
              @for (product of section.products; track product.id) {
                @let color = store.color(product.id);
                @let last = product.history.at(-1);
                @let name = label(product);
                <li cdkDrag [cdkDragData]="product.id" [class.shown]="color">
                  <span class="grip" cdkDragHandle title="Drag to another group">
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <circle cx="9" cy="6" r="1" />
                      <circle cx="9" cy="12" r="1" />
                      <circle cx="9" cy="18" r="1" />
                      <circle cx="15" cy="6" r="1" />
                      <circle cx="15" cy="12" r="1" />
                      <circle cx="15" cy="18" r="1" />
                    </svg>
                  </span>
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
                  <span class="price">{{
                    last ? money(last.price, product.currency) : 'Pending'
                  }}</span>
                </li>
              } @empty {
                <li class="empty">
                  {{
                    group
                      ? 'Drag products here.'
                      : groups.groups().length
                        ? 'All grouped.'
                        : 'Nothing tracked yet.'
                  }}
                </li>
              }
            </ul>
          }
        }
      </div>
      <app-new-group />
    </section>
  `,
  styleUrl: './sidebar.css',
})
export class Sidebar {
  protected readonly store = inject(ProductStore);
  protected readonly groups = inject(GroupStore);
  protected readonly money = money;
  protected readonly label = label;
  protected readonly maxShown = SERIES_COLORS.length;

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
}
