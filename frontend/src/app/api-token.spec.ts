import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { apiTokenInterceptor } from './api-token';
import { App } from './app';

describe('API token', () => {
  beforeEach(() => localStorage.clear());

  it('asks for the token on 401 and retries with it, only on /api', async () => {
    TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideHttpClient(withInterceptors([apiTokenInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    const fixture = TestBed.createComponent(App);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();

    const first = http.expectOne('/api/products');
    expect(first.request.headers.has('Authorization')).toBe(false);
    first.flush(
      { detail: 'Missing or invalid API token' },
      { status: 401, statusText: 'Unauthorized' },
    );
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const input = el.querySelector<HTMLInputElement>('#api-token');
    expect(input).not.toBeNull();
    input!.value = 'secret-token';
    el.querySelector<HTMLFormElement>('form.unlock')!.requestSubmit();
    TestBed.tick();

    const retry = http.expectOne('/api/products');
    expect(retry.request.headers.get('Authorization')).toBe('Bearer secret-token');
    retry.flush([]);
    await fixture.whenStable();
    expect(el.querySelector('form.unlock')).toBeNull();
    expect(localStorage.getItem('price-tracker.api-token')).toBe('secret-token');

    http.verify();
  });
});
