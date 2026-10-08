import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { App } from './app';

describe('App', () => {
  it('renders tracked products in the sidebar and table', async () => {
    TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/backgrounds/index.json').flush([]);
    http.expectOne('/api/products').flush([
      {
        id: 1,
        url: 'https://www.amazon.es/dp/B0BMG3FBND',
        name: 'Sapphire RX 7900 XT',
        currency: 'EUR',
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
  });
});
