import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Product, ProductStore, RANGES, SERIES_COLORS } from './products';

const product = (id: number, prices: [string, number][] = []): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  history: prices.map(([date, price]) => ({ date, price })),
});

describe('ProductStore', () => {
  let store: ProductStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClientTesting()] });
    store = TestBed.inject(ProductStore);
    http = TestBed.inject(HttpTestingController);
    TestBed.tick();
    const ids = Array.from({ length: 10 }, (_, i) => i + 1);
    http.expectOne('/api/products').flush(ids.map((id) => product(id)));
  });

  it('charts the first products by default', () => {
    expect([...store.slots().keys()]).toEqual([1, 2, 3, 4]);
  });

  it('keeps colours stable when toggling and caps the chart', () => {
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

  it('scopes history to the range ending at the newest scrape', () => {
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
