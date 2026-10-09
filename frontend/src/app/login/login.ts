import { Component, inject } from '@angular/core';
import { Account } from '../account';

// Shown on a public page; the pool is invite only, so this is how people ask
const INVITE_EMAIL = 'owner@example.com';

@Component({
  selector: 'app-login',
  template: `
    <section aria-labelledby="login-title">
      <div class="masthead">
        <span>Price Tracker</span>
        <span>Invite only</span>
      </div>

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
          <a [href]="inviteHref">Request access</a>
        </p>
      </div>

      <p class="note">
        Accounts are created by invite. Ask for one and you'll get an email to set your password.
      </p>
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

    .link:hover,
    a:hover {
      text-decoration: underline;
    }

    a {
      padding: 0.5rem 0;
      color: var(--link);
      text-decoration: none;
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
  protected readonly inviteHref = `mailto:${INVITE_EMAIL}?subject=${encodeURIComponent('Price Tracker access')}`;
}
