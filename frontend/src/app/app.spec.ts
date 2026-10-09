import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { App } from './app';

const ME = {
  email: 'ana@example.com',
  settings: { groups: [], dashboard: null, background: null },
};

describe('App', () => {
  it('renders tracked products in the sidebar and table', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    http.expectOne('/api/me').flush(ME);
    TestBed.tick();
    http.expectOne('/api/products').flush([
      {
        id: 1,
        url: 'https://www.amazon.es/dp/B0BMG3FBND',
        name: 'Sapphire RX 7900 XT',
        currency: 'EUR',
        public: false,
        mine: true,
        history: [
          { date: '2023-06-01', price: 1000 },
          { date: '2023-06-02', price: 950 },
        ],
      },
    ]);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('app-sidebar .name')?.textContent).toBe('Sapphire RX 7900 XT');
    expect(el.querySelector('app-price-table .badge')?.textContent).toContain('At lowest');
    expect(el.querySelector('.who')?.textContent).toBe('ana@example.com');
    expect(el.querySelector('.signin')).toBeNull();
  });

  it('asks a signed-out visitor to sign in, without an error banner', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    const unauthorized = { status: 401, statusText: 'Unauthorized' };
    http.expectOne('/api/me').flush({ detail: 'Not signed in' }, unauthorized);
    http.expectOne('/api/products').flush({ detail: 'Not signed in' }, unauthorized);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.signin button')?.textContent).toContain('Sign in');
    expect(el.querySelector('[role="alert"]')).toBeNull();
  });
});
