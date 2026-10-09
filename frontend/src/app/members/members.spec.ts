import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Members } from './members';

describe('Members', () => {
  it('approves a waiting account with one click', async () => {
    TestBed.configureTestingModule({ imports: [Members], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(Members);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    const bob = { sub: 'b', email: 'bob@example.com', requested_at: '2026-10-09T10:00:00Z' };
    http.expectOne('/api/members').flush([{ ...bob, status: 'pending' }]);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    el.querySelector<HTMLButtonElement>('li .primary')?.click();
    const patch = http.expectOne({ method: 'PATCH', url: '/api/members/b' });
    expect(patch.request.body).toEqual({ status: 'approved' });
    patch.flush({ ...bob, status: 'approved' });
    await fixture.whenStable();

    expect(el.querySelector('.badge')).toBeNull();
    expect(el.querySelector('li .text-button')?.textContent).toContain('Remove access');
  });

  it('creates an account, or says why it could not', async () => {
    TestBed.configureTestingModule({ imports: [Members], providers: [provideHttpClientTesting()] });
    const fixture = TestBed.createComponent(Members);
    fixture.detectChanges();
    const http = TestBed.inject(HttpTestingController);
    http.expectOne('/api/members').flush([]);
    await fixture.whenStable();

    const el = fixture.nativeElement as HTMLElement;
    const input = el.querySelector<HTMLInputElement>('#invite-email')!;
    const form = el.querySelector<HTMLFormElement>('form.invite')!;
    input.value = 'fay@example.com';
    form.requestSubmit();
    const post = http.expectOne({ method: 'POST', url: '/api/members' });
    expect(post.request.body).toEqual({ email: 'fay@example.com' });
    post.flush({
      sub: 'f',
      email: 'fay@example.com',
      status: 'approved',
      requested_at: '2026-10-09T10:00:00Z',
    });
    await fixture.whenStable();
    expect(el.querySelector('li .email')?.textContent).toBe('fay@example.com');
    expect(input.value).toBe('');

    input.value = 'eve@example.com';
    form.requestSubmit();
    http
      .expectOne('/api/members')
      .flush(
        { detail: 'This email already has an account' },
        { status: 409, statusText: 'Conflict' },
      );
    await fixture.whenStable();
    expect(el.querySelector('.invite .error')?.textContent).toContain('already has an account');
  });
});
