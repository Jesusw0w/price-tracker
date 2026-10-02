import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Product, ProductStore, RANGES, SERIES_COLORS } from './products';

const product = (asin: string, prices: [string, number][] = []): Product => ({
  asin,
  url: `https://www.amazon.es/dp/${asin}`,
  name: asin,
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
    const asins = Array.from({ length: 10 }, (_, i) => `ASIN00000${i}`);
    http.expectOne('/api/products').flush(asins.map((a) => product(a)));
  });

  it('charts the first products by default', () => {
    expect([...store.slots().keys()]).toEqual(['ASIN000000', 'ASIN000001', 'ASIN000002', 'ASIN000003']);
  });

  it('keeps colours stable when toggling and caps the chart', () => {
    const third = store.color('ASIN000002');
    store.toggle('ASIN000001');
    expect(store.color('ASIN000002')).toBe(third);

    store.toggle('ASIN000009');
    expect(store.color('ASIN000009')).toBe(SERIES_COLORS[1]);

    for (let i = 4; i < 9; i++) store.toggle(`ASIN00000${i}`);
    expect(store.slots().size).toBe(SERIES_COLORS.length);
    store.toggle('ASIN000001');
    expect(store.color('ASIN000001')).toBeUndefined();
  });

  it('scopes history to the range ending at the newest scrape', () => {
    store['list'].value.set([
      product('A', [
        ['2023-01-01', 3],
        ['2023-06-01', 2],
      ]),
      product('B', [['2023-06-20', 1]]),
    ]);
    store.range.set(RANGES[0]);
    expect(store.scoped().map((p) => p.history.length)).toEqual([1, 1]);
  });
});
