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
  unavailable_since: null,
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

  it('flags a product no longer sold at its link in red, with what to do', async () => {
    TestBed.configureTestingModule({ imports: [Sidebar], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(Sidebar);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/me').flush(ME);
    TestBed.tick();
    const gone = { ...product(1), unavailable_since: '2026-10-09' };
    const shared = { ...gone, id: 2, mine: false };
    http.expectOne('/api/products').flush([gone, shared, product(3)]);
    await fixture.whenStable();

    const [mine, theirs, fine] = (fixture.nativeElement as HTMLElement).querySelectorAll('li');
    expect(mine.classList).toContain('stale');
    expect(mine.querySelector('.price')?.textContent?.trim()).toBe('update link');
    expect(mine.querySelector('.price')?.getAttribute('title')).toContain('Change link');
    expect(theirs.querySelector('.price')?.getAttribute('title')).toContain('Only its owner');
    expect(fine.classList).not.toContain('stale');
  });
});
