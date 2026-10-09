import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Account, Settings } from './account';
import { Product, ProductStore, RANGES, SERIES_COLORS } from './products';

const product = (id: number, prices: [string, number][] = []): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  public: false,
  mine: true,
  history: prices.map(([date, price]) => ({ date, price })),
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
