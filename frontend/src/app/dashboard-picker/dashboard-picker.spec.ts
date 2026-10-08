import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Product } from '../products';
import { DashboardPicker } from './dashboard-picker';

const product = (id: number): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  history: [],
});

describe('DashboardPicker', () => {
  beforeEach(() => localStorage.clear());

  async function render() {
    TestBed.configureTestingModule({
      imports: [DashboardPicker],
      providers: [provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(DashboardPicker);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne('/api/products').flush([product(1), product(2)]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const click = async (selector: string) => {
      el.querySelector<HTMLButtonElement>(selector)!.click();
      await fixture.whenStable();
    };
    return { el, http, click };
  }

  it('archives only after the user confirms', async () => {
    const { el, http, click } = await render();

    await click('[aria-label="Archive Product 1"]');
    expect(el.querySelector('.confirm')?.textContent).toContain('price history is kept');
    http.expectNone({ method: 'DELETE' });

    await click('.confirm .text-button');
    expect(el.querySelector('.confirm')).toBeNull();

    await click('[aria-label="Archive Product 1"]');
    await click('.confirm .primary');
    http.expectOne({ method: 'DELETE', url: '/api/products/1' }).flush(null);
  });

  it('warns that delete cannot be undone and sends a permanent delete', async () => {
    const { el, http, click } = await render();

    await click('[aria-label="Delete Product 2"]');
    const confirm = el.querySelector('.confirm.danger');
    expect(confirm?.textContent).toContain("can't be undone");

    await click('.confirm .primary');
    const request = http.expectOne((r) => r.method === 'DELETE' && r.url === '/api/products/2');
    expect(request.request.params.get('permanent')).toBe('true');
  });
});
