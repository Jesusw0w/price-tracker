import { CdkDrag, CdkDragHandle, CdkDropList, CdkDropListGroup } from '@angular/cdk/drag-drop';
import { NgTemplateOutlet } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { GroupStore } from '../groups';
import { NewGroup } from '../new-group';
import { label, Product, ProductStore, SERIES_COLORS } from '../products';

type Action = 'archive' | 'delete';

/**
 * Dialog for managing products: which active ones the dashboard shows, groups, archiving,
 * restoring and permanent deletion. Archive and delete ask for confirmation first.
 */
@Component({
  selector: 'app-dashboard-picker',
  imports: [NgTemplateOutlet, CdkDropListGroup, CdkDropList, CdkDrag, CdkDragHandle, NewGroup],
  template: `
    <button type="button" class="open" aria-haspopup="dialog" (click)="open(dialog)">
      Customize
    </button>

    <dialog #dialog closedby="any" aria-labelledby="picker-heading" (close)="closed()">
      <div class="body">
        <header>
          <h2 id="picker-heading">Products</h2>
          <span class="count">{{ store.slots().size }}/{{ maxShown }} on the dashboard</span>
        </header>

        <section aria-labelledby="active-heading">
          <h3 id="active-heading">
            Active <span class="count">{{ store.products().length }}</span>
          </h3>
          <div class="groups" cdkDropListGroup>
            @for (section of groups.sections(); track section.group?.id ?? 'ungrouped') {
              @let group = section.group;
              @let state = groups.shownState(section);
              @let groupLabel = group?.name ?? 'Ungrouped';
              <div class="group-head">
                <input
                  type="checkbox"
                  [checked]="state === 'all'"
                  [indeterminate]="state === 'some'"
                  [disabled]="!section.products.length"
                  (change)="groups.toggleShown(section)"
                  [attr.aria-label]="'Show all of ' + groupLabel"
                />
                @if (group) {
                  <input
                    #groupName
                    class="group-name"
                    [value]="group.name"
                    (change)="rename(group.id, groupName)"
                    aria-label="Group name"
                    maxlength="40"
                  />
                  <button
                    type="button"
                    class="icon"
                    (click)="groups.remove(group.id)"
                    [attr.aria-label]="'Remove group ' + group.name"
                    title="Remove group; its products become ungrouped"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M18 6 6 18M6 6l12 12" />
                    </svg>
                  </button>
                } @else {
                  <span class="group-name">Ungrouped</span>
                }
              </div>
              <ul
                cdkDropList
                [cdkDropListData]="group?.id ?? null"
                [cdkDropListSortingDisabled]="!group"
                (cdkDropListDropped)="
                  groups.move($event.item.data, $event.container.data, $event.currentIndex)
                "
                [attr.aria-label]="groupLabel"
              >
                @for (product of section.products; track product.id) {
                  @let color = store.color(product.id);
                  @let name = label(product);
                  <li
                    cdkDrag
                    [cdkDragData]="product.id"
                    cdkDragPreviewContainer="parent"
                    [class.shown]="color"
                  >
                    <div class="row">
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
                        <span
                          class="key"
                          [style.background]="color ?? null"
                          aria-hidden="true"
                        ></span>
                        <span class="name" [title]="name">{{ name }}</span>
                      </label>
                      @if (groups.groups().length) {
                        <select
                          #moveTo
                          class="move"
                          (change)="groups.move(product.id, moveTo.value || null)"
                          [attr.aria-label]="'Group for ' + name"
                        >
                          <option value="" [selected]="!group">Ungrouped</option>
                          @for (option of groups.groups(); track option.id) {
                            <option [value]="option.id" [selected]="option.id === group?.id">
                              {{ option.name }}
                            </option>
                          }
                        </select>
                      }
                      <button
                        type="button"
                        class="icon"
                        (click)="ask(product, 'archive')"
                        [attr.aria-label]="'Archive ' + name"
                        title="Archive"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <rect width="20" height="5" x="2" y="3" rx="1" />
                          <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8" />
                          <path d="M10 12h4" />
                        </svg>
                      </button>
                      <button
                        type="button"
                        class="icon danger"
                        (click)="ask(product, 'delete')"
                        [attr.aria-label]="'Delete ' + name"
                        title="Delete"
                      >
                        <svg viewBox="0 0 24 24" aria-hidden="true">
                          <path d="M10 11v6M14 11v6M3 6h18" />
                          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                          <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                        </svg>
                      </button>
                    </div>
                    <ng-container
                      *ngTemplateOutlet="confirmation; context: { $implicit: product }"
                    />
                  </li>
                } @empty {
                  <li class="empty">
                    {{
                      group
                        ? 'Drag products here.'
                        : store.products().length
                          ? 'All grouped.'
                          : 'Nothing tracked yet.'
                    }}
                  </li>
                }
              </ul>
            }
          </div>
          <app-new-group />
          @if (store.chartFull()) {
            <p class="help">The chart holds {{ maxShown }} products. Untick one to swap.</p>
          }
        </section>

        <section aria-labelledby="archived-heading">
          <h3 id="archived-heading">
            Archived <span class="count">{{ store.archived().length }}</span>
          </h3>
          <p class="help">Not scraped and not on the dashboard. Price history is kept.</p>
          @if (restoreError(); as message) {
            <p class="help error" role="alert">{{ message }}</p>
          }
          <ul>
            @for (product of store.archived(); track product.id) {
              @let name = label(product);
              <li class="archived">
                <div class="row">
                  <span class="name" [title]="name">{{ name }}</span>
                  <button
                    type="button"
                    class="text-button"
                    (click)="restore(product)"
                    [attr.aria-label]="'Restore ' + name"
                  >
                    Restore
                  </button>
                  <button
                    type="button"
                    class="icon danger"
                    (click)="ask(product, 'delete')"
                    [attr.aria-label]="'Delete ' + name"
                    title="Delete"
                  >
                    <svg viewBox="0 0 24 24" aria-hidden="true">
                      <path d="M10 11v6M14 11v6M3 6h18" />
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
                      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                    </svg>
                  </button>
                </div>
                <ng-container *ngTemplateOutlet="confirmation; context: { $implicit: product }" />
              </li>
            } @empty {
              <li class="empty">Nothing archived.</li>
            }
          </ul>
        </section>

        <button type="button" class="primary done" (click)="dialog.close()">Done</button>
      </div>
    </dialog>

    <ng-template #confirmation let-product>
      @let ask = pending();
      @if (ask && ask.product.id === product.id) {
        @let name = label(product);
        <div class="confirm" [class.danger]="ask.action === 'delete'" role="alert">
          @if (ask.action === 'archive') {
            <p>
              Archive <strong>{{ name }}</strong
              >? It stops being scraped and leaves the dashboard. Its price history is kept, and you
              can restore it below.
            </p>
          } @else {
            <p>
              Delete <strong>{{ name }}</strong> for good? Its price history is deleted too. This
              can't be undone.
            </p>
          }
          <div class="actions">
            <button type="button" class="text-button" (click)="pending.set(null)">Cancel</button>
            <button type="button" class="primary" (click)="confirm()">
              {{ ask.action === 'archive' ? 'Archive' : 'Delete' }}
            </button>
          </div>
        </div>
      }
    </ng-template>
  `,
  styles: `
    .open {
      padding: 0.35rem 0.85rem;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgb(21 27 32 / 0.7);
      color: var(--ink-2);
      font: inherit;
      font-size: 0.85rem;
      cursor: pointer;
    }
    .open:hover {
      background: rgb(203 213 219 / 0.06);
      color: var(--ink);
    }
    dialog {
      width: min(36rem, calc(100vw - 2rem));
      max-height: min(40rem, calc(100vh - 4rem));
      padding: 1.25rem 1.5rem;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--surface);
      color: var(--ink-2);
      box-shadow: 0 20px 50px rgb(0 0 0 / 0.5);
    }
    dialog::backdrop {
      background: rgb(13 18 21 / 0.6);
      backdrop-filter: blur(4px);
    }
    .body,
    section {
      display: flex;
      flex-direction: column;
      gap: 0.6rem;
    }
    .body {
      gap: 1.25rem;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
    }
    h2,
    h3 {
      margin: 0;
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--ink-2);
    }
    h2 {
      font-size: 0.85rem;
      color: var(--ink);
    }
    h3 {
      display: flex;
      gap: 0.5rem;
      padding-bottom: 0.4rem;
      border-bottom: 1px solid var(--grid);
    }
    .count,
    .help {
      margin: 0;
      font-size: 0.75rem;
      font-weight: 400;
      letter-spacing: normal;
      text-transform: none;
      color: var(--muted);
    }
    .help.error {
      color: var(--danger);
    }
    ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    li {
      padding: 0.3rem 0.5rem;
      border-radius: 8px;
    }
    li:hover {
      background: rgb(203 213 219 / 0.06);
    }
    .row {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    label {
      display: flex;
      flex: 1;
      align-items: center;
      gap: 0.6rem;
      min-width: 0;
      cursor: pointer;
    }
    input {
      accent-color: var(--steel);
    }
    .key {
      flex: none;
      width: 14px;
      height: 2px;
      border-radius: 1px;
      background: var(--border);
    }
    .name {
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: 0.875rem;
    }
    li.shown .name {
      color: var(--ink);
    }
    li.archived .name {
      color: var(--muted);
    }
    .empty {
      color: var(--muted);
      font-size: 0.875rem;
    }
    .icon {
      display: grid;
      flex: none;
      place-items: center;
      width: 1.6rem;
      height: 1.6rem;
      padding: 0;
      border: 0;
      border-radius: 6px;
      background: none;
      color: var(--muted);
      cursor: pointer;
    }
    .icon svg {
      width: 1rem;
      height: 1rem;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .icon:hover,
    .icon:focus-visible {
      background: rgb(203 213 219 / 0.1);
      color: var(--ink);
    }
    .icon.danger:hover,
    .icon.danger:focus-visible {
      background: rgb(230 103 103 / 0.15);
      color: var(--danger);
    }
    .text-button {
      flex: none;
      padding: 0.25rem 0.6rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: none;
      color: var(--ink-2);
      font: inherit;
      font-size: 0.8rem;
      cursor: pointer;
    }
    .text-button:hover,
    .text-button:focus-visible {
      border-color: var(--steel);
      color: var(--ink);
    }
    .primary {
      padding: 0.35rem 0.9rem;
      border: 0;
      border-radius: 8px;
      background: var(--steel);
      color: #fff;
      font: inherit;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
    }
    .primary:hover {
      background: #6d889b;
    }
    .done {
      align-self: flex-end;
      padding: 0.55rem 1rem;
    }
    .groups {
      display: flex;
      flex-direction: column;
      gap: 0.35rem;
    }
    .group-head {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 0.4rem;
      padding: 0 0.5rem;
    }
    .group-name {
      flex: 1;
      min-width: 0;
      padding: 0.2rem 0.4rem;
      border: 1px solid transparent;
      border-radius: 6px;
      background: none;
      color: var(--ink);
      font: inherit;
      font-size: 0.8rem;
      font-weight: 600;
    }
    input.group-name:hover,
    input.group-name:focus {
      border-color: var(--border);
    }
    ul.cdk-drop-list {
      min-height: 1.75rem;
    }
    .grip {
      display: grid;
      flex: none;
      place-items: center;
      color: var(--muted);
      cursor: grab;
      touch-action: none;
    }
    .grip svg {
      width: 0.9rem;
      height: 0.9rem;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
    }
    li:not(:hover) .grip {
      opacity: 0.4;
    }
    .move {
      flex: none;
      max-width: 8rem;
      padding: 0.2rem 0.3rem;
      border: 1px solid var(--border);
      border-radius: 6px;
      background: rgb(13 18 21 / 0.55);
      color: var(--ink-2);
      font: inherit;
      font-size: 0.75rem;
    }
    .confirm {
      margin: 0.4rem 0 0.2rem;
      padding: 0.6rem 0.75rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: rgb(95 120 138 / 0.12);
      font-size: 0.8rem;
    }
    .confirm p {
      margin: 0 0 0.5rem;
    }
    .confirm strong {
      color: var(--ink);
      font-weight: 600;
      overflow-wrap: anywhere;
    }
    .confirm.danger {
      border-color: rgb(230 103 103 / 0.4);
      background: rgb(230 103 103 / 0.1);
    }
    .confirm.danger .primary {
      background: #b04a4a;
    }
    .confirm.danger .primary:hover {
      background: #c25656;
    }
    .actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.5rem;
    }
  `,
})
export class DashboardPicker {
  protected readonly store = inject(ProductStore);
  protected readonly groups = inject(GroupStore);
  protected readonly label = label;
  protected readonly maxShown = SERIES_COLORS.length;

  protected readonly pending = signal<{ product: Product; action: Action } | null>(null);
  protected readonly restoreError = signal<string | undefined>(undefined);

  protected open(dialog: HTMLDialogElement): void {
    this.store.showArchived.set(true);
    dialog.showModal();
  }

  protected closed(): void {
    this.pending.set(null);
    this.restoreError.set(undefined);
    this.store.showArchived.set(false);
  }

  protected ask(product: Product, action: Action): void {
    this.restoreError.set(undefined);
    this.pending.set({ product, action });
  }

  protected async confirm(): Promise<void> {
    const ask = this.pending();
    if (!ask) return;
    this.pending.set(null);
    if (ask.action === 'archive') await this.store.archive(ask.product.id);
    else {
      await this.store.deletePermanently(ask.product.id);
      this.groups.forget(ask.product.id);
    }
  }

  protected rename(id: string, input: HTMLInputElement): void {
    const name = input.value.trim();
    if (name) this.groups.rename(id, name);
    // An empty name would leave the group unlabelled, so put the old one back
    else input.value = this.groups.groups().find((g) => g.id === id)?.name ?? '';
  }

  protected async restore(product: Product): Promise<void> {
    this.restoreError.set(await this.store.restore(product));
  }
}
