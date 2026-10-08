import { HttpInterceptorFn } from '@angular/common/http';
import { inject, Service, signal } from '@angular/core';

const STORAGE_KEY = 'price-tracker.api-token';

function read(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? '';
  } catch {
    return '';
  }
}

/** The owner's bearer token, kept in localStorage so the UI stays unlocked across visits. */
@Service()
export class ApiToken {
  readonly value = signal(read());

  set(token: string): void {
    try {
      localStorage.setItem(STORAGE_KEY, token);
    } catch {
      // storage blocked: the token lasts until the tab closes
    }
    this.value.set(token);
  }
}

// Only same-origin /api calls get the token, so it never leaks to another host
export const apiTokenInterceptor: HttpInterceptorFn = (req, next) => {
  const token = inject(ApiToken).value();
  return next(
    token && req.url.startsWith('/api/')
      ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
      : req,
  );
};
