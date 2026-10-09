import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Account, Settings } from './account';
import { label, Product, ProductStore, RANGES, SERIES_COLORS } from './products';

const product = (id: number, prices: [string, number][] = []): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  public: false,
  mine: true,
  unavailable_since: null,
  history: prices.map(([date, price]) => ({ date, price })),
});

describe('label', () => {
  it('labels an unscraped product by its short link, so two of one shop differ', () => {
    const unnamed = { ...product(1), name: null, url: 'https://www.amazon.es/dp/B0G34RRG1F' };
    expect(label(unnamed)).toBe('amazon.es/dp/B0G34RRG1F');
    expect(label(product(1))).toBe('Product 1');
  });
});

describe('ProductStore', () => {
  let store: ProductStore;
  let http: HttpTestingController;

  async function load(products: Product[], dashboard: Settings['dashboard'] = null) {
    TestBed.configureTestingModule({ providers: [provideHttpClientTesting()] });
    store = TestBed.inject(ProductStore);
    http = TestBed.inject(HttpTestingController);
    TestBed.tick();
    http
      .expectOne('/api/me')
      .flush({ email: 'ana@example.com', settings: { groups: [], dashboard, background: null } });
    TestBed.tick();
    http.expectOne('/api/products').flush(products);
    await TestBed.inject(ApplicationRef).whenStable();
  }

  const ten = () => Array.from({ length: 10 }, (_, i) => product(i + 1));

  afterEach(() => http.verify({ ignoreCancelled: true }));

  it('reloads while a product waits for its first scrape', async () => {
    const pending = { ...product(1), name: null };
    await load([pending]);
    vi.useFakeTimers();
    try {
      // Re-arm the poll under fake timers: load ran on real ones
      store.reload();
      TestBed.tick();
      http.expectOne('/api/products').flush([pending]);
      await vi.advanceTimersByTimeAsync(0);
      TestBed.tick();

      await vi.advanceTimersByTimeAsync(30_000);
      TestBed.tick();
      http.expectOne('/api/products').flush([product(1)]);
      await vi.advanceTimersByTimeAsync(0);
      TestBed.tick();
      await vi.advanceTimersByTimeAsync(60_000);
      http.expectNone('/api/products');
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows the first products by default', async () => {
    await load(ten());
    expect([...store.slots().keys()]).toEqual([1, 2, 3, 4]);
    expect(store.shown().map((p) => p.id)).toEqual([1, 2, 3, 4]);
  });

  it('keeps colours stable when toggling and caps the chart', async () => {
    await load(ten());
    const third = store.color(3);
    store.toggle(2);
    expect(store.color(3)).toBe(third);

    store.toggle(10);
    expect(store.color(10)).toBe(SERIES_COLORS[1]);

    for (let id = 5; id < 10; id++) store.toggle(id);
    expect(store.slots().size).toBe(SERIES_COLORS.length);
    store.toggle(2);
    expect(store.color(2)).toBeUndefined();
  });

  it('restores the saved selection and saves changes to the account', async () => {
    await load(ten(), [
      [7, 5],
      [99, 0],
    ]);
    expect([...store.slots()]).toEqual([[7, 5]]); // 99 is no longer visible

    store.toggle(3);
    expect(TestBed.inject(Account).settings().dashboard).toEqual([
      [7, 5],
      [3, 0],
    ]);
  });

  it('shares a product and keeps the answer from the API', async () => {
    await load(ten());
    const sharing = store.setPublic(2, true);
    const patch = http.expectOne({ method: 'PATCH', url: '/api/products/2' });
    expect(patch.request.body).toEqual({ public: true });
    patch.flush({ ...product(2), public: true });
    await sharing;
    expect(store.products().find((p) => p.id === 2)?.public).toBe(true);
  });

  it('moves a product to a new link and shows why a link is refused', async () => {
    await load(ten());
    const moving = store.changeLink(2, 'https://shop.example/p/new');
    const put = http.expectOne({ method: 'PUT', url: '/api/products/2/link' });
    expect(put.request.body).toEqual({ link: 'https://shop.example/p/new' });
    put.flush({ ...product(2), url: 'https://shop.example/p/new' });
    expect(await moving).toBeUndefined();
    expect(store.products().find((p) => p.id === 2)?.url).toBe('https://shop.example/p/new');

    const refused = store.changeLink(2, 'https://shop.example/p/3');
    http
      .expectOne('/api/products/2/link')
      .flush(
        { detail: 'Another of your products has this link' },
        { status: 409, statusText: 'Conflict' },
      );
    expect(await refused).toBe('Another of your products has this link');
  });

  it('archives a product and restores it with its history', async () => {
    await load(ten());
    const archiving = store.archive(2);
    http.expectOne({ method: 'DELETE', url: '/api/products/2' }).flush(null);
    await archiving;
    expect(store.products().some((p) => p.id === 2)).toBe(false);
    expect(store.slots().has(2)).toBe(false);

    store.showArchived.set(true);
    TestBed.tick();
    const archived = product(2, [['2023-06-01', 5]]);
    http.expectOne('/api/products/archived').flush([archived]);
    await TestBed.inject(ApplicationRef).whenStable();
    expect(store.archived()).toEqual([archived]);

    const restoring = store.restore(archived);
    const post = http.expectOne({ method: 'POST', url: '/api/products' });
    expect(post.request.body).toEqual({ link: archived.url });
    post.flush(archived);
    expect(await restoring).toBeUndefined();
    expect(store.archived()).toEqual([]);
    expect(store.shown().some((p) => p.id === 2)).toBe(true);
  });

  it('scopes history to the range ending at the newest scrape', async () => {
    await load(ten());
    store['list'].value.set([
      product(1, [
        ['2023-01-01', 3],
        ['2023-06-01', 2],
      ]),
      product(2, [['2023-06-20', 1]]),
    ]);
    store.range.set(RANGES[0]);
    expect(store.scoped().map((p) => p.history.length)).toEqual([1, 1]);
  });
});
