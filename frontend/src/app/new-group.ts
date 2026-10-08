import { Component, inject } from '@angular/core';
import { GroupStore } from './groups';

@Component({
  selector: 'app-new-group',
  template: `
    <form (submit)="add($event, name)">
      <input
        #name
        aria-label="New group name"
        placeholder="New group"
        maxlength="40"
        autocomplete="off"
      />
      <button type="submit">Add group</button>
    </form>
  `,
  styles: `
    form {
      display: flex;
      gap: 0.5rem;
    }
    input {
      flex: 1;
      min-width: 0;
      padding: 0.4rem 0.65rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: rgb(13 18 21 / 0.55);
      color: var(--ink);
      font: inherit;
      font-size: 0.85rem;
    }
    input::placeholder {
      color: var(--muted);
    }
    button {
      flex: none;
      padding: 0.4rem 0.75rem;
      border: 1px solid var(--border);
      border-radius: 8px;
      background: none;
      color: var(--ink-2);
      font: inherit;
      font-size: 0.8rem;
      cursor: pointer;
    }
    button:hover,
    button:focus-visible {
      border-color: var(--steel);
      color: var(--ink);
    }
  `,
})
export class NewGroup {
  private readonly groups = inject(GroupStore);

  protected add(event: SubmitEvent, input: HTMLInputElement): void {
    event.preventDefault();
    const name = input.value.trim();
    if (!name) return;
    this.groups.create(name);
    input.value = '';
  }
}
