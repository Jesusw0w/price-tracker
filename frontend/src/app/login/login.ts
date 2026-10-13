import { Component, inject } from '@angular/core';
import { Account } from '../account';
import { ProductStore } from '../products';

@Component({
  selector: 'app-login',
  template: `
    <section aria-labelledby="login-title">
      <div class="masthead">
        <span>Price Tracker</span>
        <span>{{ account.status() === 'pending' ? 'Awaiting approval' : 'Members only' }}</span>
      </div>

      @switch (account.status()) {
        @case ('pending') {
          <div class="intro">
            <h1 id="login-title">Almost in</h1>
            <p>
              Thanks for signing up, {{ account.email() }}. Every new account is approved by hand,
              and you can come in as soon as yours is.
            </p>
          </div>
          <button type="button" class="primary" (click)="checkAgain()">
            <span>Check again</span><span aria-hidden="true">↻</span>
          </button>
          <div class="lines">
            <p class="line">
              <span>Not you</span>
              <span class="leader" aria-hidden="true"></span>
              <button type="button" class="link" (click)="account.signOut()">Sign out</button>
            </p>
          </div>
        }
        @case ('rejected') {
          <div class="intro">
            <h1 id="login-title">No access</h1>
            <p>{{ account.email() }} hasn't been given access to Price Tracker.</p>
          </div>
          <button type="button" class="primary" (click)="account.signOut()">
            <span>Sign out</span><span aria-hidden="true">→</span>
          </button>
        }
        @default {
          <div class="intro">
            <h1 id="login-title">Sign in</h1>
            <p>Price history for anything you track, from any online shop.</p>
          </div>

          <button type="button" class="primary" (click)="account.signIn()">
            <span>Sign in</span><span aria-hidden="true">→</span>
          </button>

          <div class="lines">
            <p class="line">
              <span>Forgot your password</span>
              <span class="leader" aria-hidden="true"></span>
              <button type="button" class="link" (click)="account.signIn('reset')">Reset</button>
            </p>
            <p class="line">
              <span>No account yet</span>
              <span class="leader" aria-hidden="true"></span>
              <button type="button" class="link" (click)="account.signIn('signup')">
                Create one
              </button>
            </p>
          </div>

          <p class="note">
            New accounts are approved by hand before they can track anything. You'll see your
            dashboard as soon as yours is.
          </p>
        }
      }
    </section>
  `,
  styles: `
    :host {
      display: block;
      width: min(100%, 27.5rem);
      font-family: var(--mono);
      text-shadow: 0 1px 2px rgb(0 0 0 / 0.55);
    }

    section {
      display: flex;
      flex-direction: column;
      gap: 1.5rem;
    }

    .masthead {
      display: flex;
      justify-content: space-between;
      padding-bottom: 1.5rem;
      border-bottom: 1px dashed var(--rule);
      font-size: 0.75rem;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .intro {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    h1 {
      margin: 0;
      font-family: var(--sans);
      font-size: 3rem;
      line-height: 1;
      font-weight: 600;
      letter-spacing: -0.03em;
      color: var(--ink);
    }

    .intro p {
      margin: 0;
      font-size: 0.875rem;
      line-height: 1.6;
      color: var(--ink-2);
    }

    .primary {
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 3.25rem;
      padding: 0 1.1rem;
      border: 1px solid var(--ink);
      border-radius: 4px;
      background: var(--ink);
      color: var(--page);
      font: inherit;
      font-size: 0.875rem;
      font-weight: 600;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      text-shadow: none;
      cursor: pointer;
    }

    .primary:hover {
      background: #fff;
    }

    .lines {
      display: flex;
      flex-direction: column;
      gap: 0.25rem;
      font-size: 0.875rem;
    }

    .line {
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      min-height: 2.25rem;
      margin: 0;
    }

    .leader {
      flex: 1;
      border-bottom: 1px dotted var(--leader);
      transform: translateY(-0.25rem);
    }

    .link {
      padding: 0.5rem 0;
      border: 0;
      background: none;
      color: var(--link);
      font: inherit;
      cursor: pointer;
    }

    .link:hover {
      text-decoration: underline;
    }

    .note {
      margin: 0;
      padding-top: 1.5rem;
      border-top: 1px dashed var(--rule);
      font-size: 0.75rem;
      line-height: 1.6;
      color: var(--muted);
    }
  `,
})
export class Login {
  protected readonly account = inject(Account);
  private readonly store = inject(ProductStore);

  // Products failed with 403 while waiting, so they reload along with the account
  protected checkAgain(): void {
    this.account.retry();
    this.store.reload();
  }
}
