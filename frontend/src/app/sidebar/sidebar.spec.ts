import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Product, ProductStore } from '../products';
import { Sidebar } from './sidebar';

const product = (id: number): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  public: false,
  mine: true,
  history: [],
});

const ME = {
  email: 'ana@example.com',
  settings: { groups: [], dashboard: null, background: null },
};

describe('Sidebar', () => {
  it('filters the dashboard but offers no archive or delete', async () => {
    TestBed.configureTestingModule({ imports: [Sidebar], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(Sidebar);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/me').flush(ME);
    TestBed.tick();
    http.expectOne('/api/products').flush([product(1), product(2)]);
    await fixture.whenStable();
    const store = TestBed.inject(ProductStore);
    const el = fixture.nativeElement as HTMLElement;
    expect(store.shown().map((p) => p.id)).toEqual([1, 2]);

    el.querySelector<HTMLInputElement>('li input[type="checkbox"]')!.click();
    await fixture.whenStable();
    expect(store.shown().map((p) => p.id)).toEqual([2]);

    expect(el.querySelector('[aria-label^="Archive"], [aria-label^="Delete"]')).toBeNull();
  });
});
