import { HttpInterceptorFn } from '@angular/common/http';
import { inject, Service, signal } from '@angular/core';

const STORAGE_KEY = 'price-tracker.api-token';

/** The owner's bearer token, kept in localStorage so the UI stays unlocked across visits. */
@Service()
export class ApiToken {
  readonly value = signal(localStorage.getItem(STORAGE_KEY) ?? '');

  set(token: string): void {
    localStorage.setItem(STORAGE_KEY, token);
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
