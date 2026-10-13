import { Component, inject } from '@angular/core';
import { GroupStore } from './groups';

@Component({
  selector: 'app-new-group',
  template: `
    <form (submit)="add($event, name)">
      <span aria-hidden="true">+</span>
      <input
        #name
        aria-label="New group name"
        placeholder="new group"
        maxlength="40"
        autocomplete="off"
      />
      <button type="submit">Add group</button>
    </form>
  `,
  styles: `
    form {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      border-bottom: 1px dashed var(--rule);
      font-family: var(--mono);
      font-size: 0.8125rem;
      color: var(--muted);
    }
    form:focus-within {
      border-bottom-style: solid;
      border-bottom-color: var(--link);
    }
    input {
      flex: 1;
      min-width: 0;
      min-height: 2.25rem;
      padding: 0;
      border: 0;
      background: none;
      color: var(--ink);
      font: inherit;
      outline: none;
    }
    input::placeholder {
      color: var(--muted);
    }
    button {
      flex: none;
      min-height: 2.25rem;
      padding: 0;
      border: 0;
      background: none;
      color: var(--link);
      font: inherit;
      cursor: pointer;
    }
    button:hover {
      text-decoration: underline;
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
