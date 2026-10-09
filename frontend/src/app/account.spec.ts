import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef, DOCUMENT } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Account } from './account';

describe('Account', () => {
  const assign = vi.fn();

  async function load(): Promise<{ account: Account; http: HttpTestingController }> {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClientTesting(),
        // jsdom can't navigate, so sign-in and sign-out land here instead
        {
          provide: DOCUMENT,
          useFactory: () =>
            new Proxy(document, {
              get: (target, key) => {
                if (key === 'location') return { assign };
                const value: unknown = Reflect.get(target, key);
                return typeof value === 'function' ? value.bind(target) : value;
              },
            }),
        },
      ],
    });
    const account = TestBed.inject(Account);
    const http = TestBed.inject(HttpTestingController);
    TestBed.tick();
    http.expectOne('/api/me').flush({
      email: 'ana@example.com',
      settings: { groups: [], dashboard: null, background: null },
    });
    await TestBed.inject(ApplicationRef).whenStable();
    // Only now: whenStable never settles under fake timers
    vi.useFakeTimers();
    return { account, http };
  }

  beforeEach(() => assign.mockReset());
  afterEach(() => vi.useRealTimers());

  it('saves a burst of changes as one request', async () => {
    const { account, http } = await load();
    account.update({ background: 'a.webp' });
    account.update({ dashboard: [[1, 0]] });
    http.expectNone('/api/me/settings');

    vi.advanceTimersByTime(500);
    const put = http.expectOne({ method: 'PUT', url: '/api/me/settings' });
    expect(put.request.body).toEqual({ groups: [], dashboard: [[1, 0]], background: 'a.webp' });
    put.flush(null, { status: 204, statusText: 'No Content' });
    http.verify();
  });

  it('flags a failed save so the change is not silently lost', async () => {
    const { account, http } = await load();
    account.update({ background: 'a.webp' });
    vi.advanceTimersByTime(500);
    http.expectOne('/api/me/settings').flush(null, { status: 500, statusText: 'Server Error' });
    await vi.runAllTimersAsync();
    expect(account.saveFailed()).toBe(true);
  });

  it('starts a password reset through the backend login, which keeps PKCE', async () => {
    const { account } = await load();
    account.signIn('reset');
    expect(assign).toHaveBeenCalledWith('/api/auth/login?page=reset');
  });

  it('saves pending changes before signing out of the app and of Cognito', async () => {
    const { account, http } = await load();
    account.update({ background: 'a.webp' });
    const signingOut = account.signOut();

    http.expectOne({ method: 'PUT', url: '/api/me/settings' }).flush(null);
    await vi.runAllTimersAsync();
    http
      .expectOne({ method: 'POST', url: '/api/auth/logout' })
      .flush({ logout_url: 'https://login.example/logout' });
    await signingOut;
    expect(assign).toHaveBeenCalledWith('https://login.example/logout');
  });

  it('sends the browser to the backend to sign in', async () => {
    const { account } = await load();
    account.signIn();
    expect(assign).toHaveBeenCalledWith('/api/auth/login');
  });
});
