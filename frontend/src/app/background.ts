import { httpResource } from '@angular/common/http';
import { computed, inject, Service } from '@angular/core';
import { Account } from './account';

/** A random wallpaper from public/backgrounds, saved with the account. */
@Service()
export class Background {
  private readonly account = inject(Account);
  private readonly index = httpResource<string[]>(() => '/backgrounds/index.json', {
    defaultValue: [],
  });
  private readonly images = computed(() => (this.index.hasValue() ? this.index.value() : []));
  private readonly chosen = computed(() => this.account.settings().background ?? '');

  readonly available = computed(() => this.images().length > 0);

  /** CSS value for the chosen image, or null to keep the default gradient. */
  readonly image = computed(() => {
    const name = this.chosen();
    // A saved image that was since removed from the folder falls back to the gradient
    return this.images().includes(name) ? `url("/backgrounds/${encodeURIComponent(name)}")` : null;
  });

  shuffle(): void {
    const others = this.images().filter((name) => name !== this.chosen());
    if (!others.length) return;
    this.account.update({ background: others[Math.floor(Math.random() * others.length)] });
  }
}
