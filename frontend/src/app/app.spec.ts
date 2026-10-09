import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { App } from './app';

const ME = {
  email: 'ana@example.com',
  status: 'approved',
  owner: false,
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
        unavailable_since: null,
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
    expect(el.querySelector('app-login button')?.textContent).toContain('Sign in');
    expect(el.querySelector('[role="alert"]')).toBeNull();
    expect(el.querySelector('app-sidebar')).toBeNull();
  });

  it('offers a retry when the server is unreachable', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    const down = { status: 503, statusText: 'Service Unavailable' };
    http.expectOne('/api/me').flush(null, down);
    http.expectOne('/api/products').flush(null, down);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('[role="alert"]')?.textContent).toContain("Can't reach the server");
    el.querySelector<HTMLButtonElement>('[role="alert"] button')?.click();
    TestBed.tick();
    http.expectOne('/api/me');
    http.expectOne('/api/products');
  });

  it('keeps a new account on the waiting screen until the owner approves it', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    http.expectOne('/api/me').flush({ ...ME, status: 'pending' });
    http
      .expectOne('/api/products')
      .flush({ detail: 'Waiting for approval' }, { status: 403, statusText: 'Forbidden' });
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('app-login h1')?.textContent).toContain('Almost in');
    expect(el.querySelector('app-sidebar')).toBeNull();
    expect(el.querySelector('[role="alert"]')).toBeNull();
  });

  it('shows the owner the access requests', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    http.expectOne('/api/me').flush({ ...ME, owner: true });
    http.expectOne('/api/products').flush([]);
    // The members dialog renders, and so asks for the list, once /api/me has resolved
    const members = await vi.waitFor(() => {
      TestBed.tick();
      return http.expectOne('/api/members');
    });
    members.flush([
      {
        sub: 'b',
        email: 'bob@example.com',
        status: 'pending',
        requested_at: '2026-10-09T10:00:00Z',
      },
    ]);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('app-members .badge')?.textContent).toBe('1');
  });

  it('sets the cards from the saved opacity and the Customize slider', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    http.expectOne('/api/me').flush({ ...ME, settings: { ...ME.settings, opacity: 40 } });
    http.expectOne('/api/products').flush([]);
    await fixture.whenStable();

    const host = fixture.nativeElement as HTMLElement;
    expect(host.style.getPropertyValue('--card-alpha')).toBe('0.4');

    const slider = host.querySelector<HTMLInputElement>('app-opacity-slider input')!;
    slider.value = '85';
    slider.dispatchEvent(new Event('input'));
    TestBed.tick();
    expect(host.style.getPropertyValue('--card-alpha')).toBe('0.85');
  });
});
