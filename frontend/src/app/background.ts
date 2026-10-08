import { httpResource } from '@angular/common/http';
import { computed, Service, signal } from '@angular/core';

const STORAGE_KEY = 'price-tracker.background';

function read(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
}

/** A random wallpaper from public/backgrounds, remembered in this browser. */
@Service()
export class Background {
  private readonly index = httpResource<string[]>(() => '/backgrounds/index.json', {
    defaultValue: [],
  });
  private readonly images = computed(() => (this.index.hasValue() ? this.index.value() : []));
  private readonly chosen = signal(read());

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
    const next = others[Math.floor(Math.random() * others.length)];
    this.chosen.set(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // storage blocked: the pick lasts for this visit
    }
  }
}
