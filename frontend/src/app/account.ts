import { HttpClient, HttpErrorResponse, httpResource } from '@angular/common/http';
import { computed, DOCUMENT, inject, linkedSignal, Service, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import type { Group } from './groups';

export interface Settings {
  groups: Group[];
  /** [product id, colour slot] pairs; null until the user picks, so defaults apply. */
  dashboard: [number, number][] | null;
  background: string | null;
  /** Percent opacity of the dashboard's cards; null keeps the default. */
  opacity: number | null;
}

export type MemberStatus = 'pending' | 'approved' | 'rejected';

interface Me {
  email: string;
  /** Anyone can sign up; only accounts the owner approved can use the app. */
  status: MemberStatus;
  owner: boolean;
  settings: Settings;
}

const EMPTY: Settings = { groups: [], dashboard: null, background: null, opacity: null };
export const DEFAULT_OPACITY = 70;
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
  readonly status = computed(() => (this.me.hasValue() ? this.me.value().status : null));
  readonly owner = computed(() => this.me.hasValue() && this.me.value().owner);
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

  /** `reset` and `signup` open Cognito's own pages, which end in a sign-in too. */
  signIn(page: 'login' | 'reset' | 'signup' = 'login'): void {
    this.location.assign(page === 'login' ? '/api/auth/login' : `/api/auth/login?page=${page}`);
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
