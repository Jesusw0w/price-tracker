import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Background } from './background';

describe('Background', () => {
  async function load(images: string[], saved: string | null = null): Promise<Background> {
    TestBed.configureTestingModule({ providers: [provideHttpClientTesting()] });
    const background = TestBed.inject(Background);
    const http = TestBed.inject(HttpTestingController);
    TestBed.tick();
    http.expectOne('/api/me').flush({
      email: 'ana@example.com',
      settings: { groups: [], dashboard: null, background: saved },
    });
    http.expectOne('/backgrounds/index.json').flush(images);
    await TestBed.inject(ApplicationRef).whenStable();
    return background;
  }

  it('keeps the gradient until shuffled, then never repeats the current image', async () => {
    const background = await load(['a.webp', 'b c.webp']);
    expect(background.image()).toBeNull();

    for (let i = 0; i < 5; i++) {
      const before = background.image();
      background.shuffle();
      expect(background.image()).not.toBe(before);
    }
    expect(['url("/backgrounds/a.webp")', 'url("/backgrounds/b%20c.webp")']).toContain(
      background.image(),
    );
  });

  it('forgets a saved image that left the folder', async () => {
    const background = await load(['a.webp'], 'gone.webp');
    expect(background.image()).toBeNull();
    expect(background.available()).toBe(true);
  });
});
