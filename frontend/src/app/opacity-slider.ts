import { Component, computed, inject } from '@angular/core';
import { Account, DEFAULT_OPACITY } from './account';

/** How see-through the dashboard's cards are; saved with the account. */
@Component({
  selector: 'app-opacity-slider',
  template: `
    <label>
      <span>Panel opacity</span>
      <input type="range" min="20" max="100" step="5" [value]="opacity()" (input)="set($event)" />
      <output>{{ opacity() }}%</output>
    </label>
  `,
  styles: `
    label {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    input {
      flex: 1;
    }
  `,
})
export class OpacitySlider {
  private readonly account = inject(Account);
  protected readonly opacity = computed(() => this.account.settings().opacity ?? DEFAULT_OPACITY);

  protected set(event: Event): void {
    this.account.update({ opacity: Number((event.target as HTMLInputElement).value) });
  }
}
