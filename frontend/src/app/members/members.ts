import { HttpClient, httpResource } from '@angular/common/http';
import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { userMessage } from '../products';

type Status = 'pending' | 'approved' | 'rejected';

interface Member {
  sub: string;
  email: string;
  status: Status;
  requested_at: string;
}

/** The owner's list of everyone who signed up, to approve or turn away, and invites. */
@Component({
  selector: 'app-members',
  imports: [DatePipe],
  template: `
    <button type="button" class="open" aria-haspopup="dialog" (click)="open(dialog)">
      Access requests
      @if (waiting(); as count) {
        <span class="badge" [attr.aria-label]="count + ' waiting'">{{ count }}</span>
      }
    </button>

    <dialog #dialog closedby="any" aria-labelledby="members-heading">
      <div class="body">
        <header>
          <h2 id="members-heading">People</h2>
          <span class="count">{{ waiting() }} waiting</span>
        </header>
        <form class="invite" (submit)="invite($event, email)">
          <label for="invite-email">Create an account, already approved</label>
          <div class="row">
            <input
              #email
              id="invite-email"
              class="field"
              type="email"
              required
              autocomplete="off"
              placeholder="friend@example.com"
            />
            <button type="submit" class="primary" [disabled]="inviting()">Invite</button>
          </div>
          @if (inviteNote(); as note) {
            <p class="when" [class.error]="note.error" role="status">{{ note.text }}</p>
          }
        </form>
        <ul>
          @for (m of members(); track m.sub) {
            <li>
              <span class="who">
                <span class="email" [title]="m.email">{{ m.email }}</span>
                <span class="when">
                  {{ labels[m.status] }} · signed up {{ m.requested_at | date: 'd MMM y' }}
                </span>
              </span>
              @if (m.status !== 'approved') {
                <button type="button" class="primary" (click)="decide(m, 'approved')">
                  Approve
                </button>
              }
              @if (m.status !== 'rejected') {
                <button type="button" class="text-button" (click)="decide(m, 'rejected')">
                  {{ m.status === 'pending' ? 'Decline' : 'Remove access' }}
                </button>
              }
            </li>
          } @empty {
            <li class="when">Nobody has signed up yet.</li>
          }
        </ul>
        <button type="button" class="primary done" (click)="dialog.close()">Done</button>
      </div>
    </dialog>
  `,
  styles: `
    .open {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      height: 2.1rem;
      padding: 0 0.85rem;
      border: 1px solid var(--border);
      border-radius: 10px;
      background: rgb(21 27 32 / 0.7);
      color: var(--ink-2);
      font: inherit;
      font-size: 0.8rem;
      cursor: pointer;
    }
    .open:hover {
      color: var(--ink);
    }
    .badge {
      min-width: 1.1rem;
      padding: 0 0.3rem;
      border-radius: 999px;
      background: var(--link);
      color: var(--page);
      font-weight: 600;
    }
    dialog {
      width: min(34rem, calc(100vw - 2rem));
      padding: 1.5rem 1.75rem;
      border: 1px solid var(--border);
      border-radius: 4px;
      background: var(--surface);
      color: var(--ink-2);
      font-size: 0.8125rem;
    }
    .body {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      padding-bottom: 0.9rem;
      border-bottom: 1px dashed var(--rule);
    }
    h2 {
      margin: 0;
      font-family: var(--sans);
      font-size: 1.25rem;
      color: var(--ink);
    }
    ul {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    li {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.6rem 0;
      border-bottom: 1px dashed var(--rule);
    }
    .who {
      display: flex;
      flex: 1;
      flex-direction: column;
      min-width: 0;
    }
    .email {
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--ink);
    }
    .count,
    .when {
      font-size: 0.75rem;
      color: var(--muted);
    }
    .text-button {
      padding: 0;
      border: 0;
      background: none;
      color: var(--link);
      font: inherit;
      cursor: pointer;
    }
    .primary {
      min-height: 2.1rem;
      padding: 0 0.9rem;
      border: 0;
      border-radius: 4px;
      background: var(--ink);
      color: var(--page);
      font: inherit;
      font-weight: 600;
      cursor: pointer;
    }
    .done {
      align-self: flex-end;
    }
    .invite {
      display: flex;
      flex-direction: column;
      gap: 0.4rem;
    }
    .row {
      display: flex;
      gap: 0.5rem;
    }
    .row .field {
      margin: 0;
    }
    .error {
      color: var(--danger);
    }
  `,
})
export class Members {
  private readonly http = inject(HttpClient);
  private readonly list = httpResource<Member[]>(() => '/api/members', { defaultValue: [] });

  protected readonly labels: Record<Status, string> = {
    pending: 'Waiting',
    approved: 'Approved',
    rejected: 'Declined',
  };
  protected readonly members = computed(() => (this.list.hasValue() ? this.list.value() : []));
  protected readonly waiting = computed(
    () => this.members().filter((m) => m.status === 'pending').length,
  );

  protected readonly inviting = signal(false);
  protected readonly inviteNote = signal<{ text: string; error: boolean } | null>(null);

  protected async invite(event: SubmitEvent, input: HTMLInputElement): Promise<void> {
    event.preventDefault();
    const email = input.value.trim();
    this.inviting.set(true);
    try {
      const member = await firstValueFrom(this.http.post<Member>('/api/members', { email }));
      this.list.value.update((all) => [member, ...all]);
      input.value = '';
      this.inviteNote.set({
        text: `Created. Cognito emailed ${email} a temporary password.`,
        error: false,
      });
    } catch (e) {
      this.inviteNote.set({
        text: userMessage(e, 'Could not create the account, try again'),
        error: true,
      });
    } finally {
      this.inviting.set(false);
    }
  }

  protected open(dialog: HTMLDialogElement): void {
    this.inviteNote.set(null);
    this.list.reload();
    dialog.showModal();
  }

  protected async decide(member: Member, status: Status): Promise<void> {
    try {
      const saved = await firstValueFrom(
        this.http.patch<Member>(`/api/members/${encodeURIComponent(member.sub)}`, { status }),
      );
      this.list.value.update((all) => all.map((m) => (m.sub === saved.sub ? saved : m)));
    } catch {
      this.list.reload();
    }
  }
}
