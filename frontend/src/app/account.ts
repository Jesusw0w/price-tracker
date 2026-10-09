import { HttpClient, HttpErrorResponse, httpResource } from '@angular/common/http';
import { computed, DOCUMENT, inject, linkedSignal, Service, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Group } from './groups';

export interface Settings {
  groups: Group[];
  /** [product id, colour slot] pairs; null until the user picks, so defaults apply. */
  dashboard: [number, number][] | null;
  background: string | null;
}

interface Me {
  email: string;
  settings: Settings;
}

const EMPTY: Settings = { groups: [], dashboard: null, background: null };
const SAVE_DELAY_MS = 500;

export const isUnauthorized = (error: unknown) =>
  error instanceof HttpErrorResponse && error.status === 401;

/**
 * The signed-in user and their dashboard settings, saved to the API as they change. The
 * session lives in an HttpOnly cookie, so nothing here ever sees a token.
 */
@Service()
export class Account {
  private readonly http = inject(HttpClient);
  private readonly location = inject(DOCUMENT).location;
  private readonly me = httpResource<Me>(() => '/api/me');
  private saveTimer: ReturnType<typeof setTimeout> | undefined;

  readonly ready = computed(() => this.me.hasValue());
  readonly email = computed(() => (this.me.hasValue() ? this.me.value().email : null));
  readonly signedOut = computed(() => isUnauthorized(this.me.error()));
  readonly loadError = computed(() => !!this.me.error() && !this.signedOut());
  readonly saveFailed = signal(false);
  readonly settings = linkedSignal(() => (this.me.hasValue() ? this.me.value().settings : EMPTY));

  update(change: Partial<Settings>): void {
    this.settings.update((settings) => ({ ...settings, ...change }));
    clearTimeout(this.saveTimer);
    // One request for a drag or a burst of toggles, not one per change
    this.saveTimer = setTimeout(() => this.save(), SAVE_DELAY_MS);
  }

  /** ``reset`` starts at Cognito's password reset, which ends in a sign-in too. */
  signIn(page: 'login' | 'reset' = 'login'): void {
    this.location.assign(page === 'reset' ? '/api/auth/login?page=reset' : '/api/auth/login');
  }

  retry(): void {
    this.me.reload();
  }

  async signOut(): Promise<void> {
    if (this.saveTimer !== undefined) {
      clearTimeout(this.saveTimer);
      await this.save();
    }
    const { logout_url } = await firstValueFrom(
      this.http.post<{ logout_url: string }>('/api/auth/logout', null),
    );
    // Ends Cognito's own session too, or the next sign-in would skip the password
    this.location.assign(logout_url);
  }

  private async save(): Promise<void> {
    this.saveTimer = undefined;
    try {
      await firstValueFrom(this.http.put('/api/me/settings', this.settings()));
      this.saveFailed.set(false);
    } catch {
      this.saveFailed.set(true);
    }
  }
}
