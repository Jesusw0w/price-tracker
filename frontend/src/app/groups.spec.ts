import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Account } from './account';
import { Group, GroupStore, Section } from './groups';
import { Product, ProductStore } from './products';

const product = (id: number): Product => ({
  id,
  url: `https://shop.example/p/${id}`,
  name: `Product ${id}`,
  currency: 'EUR',
  public: false,
  mine: true,
  history: [],
});

describe('GroupStore', () => {
  let groups: GroupStore;
  let store: ProductStore;

  async function load(ids: number[], saved: Group[] = []): Promise<void> {
    TestBed.configureTestingModule({ providers: [provideHttpClientTesting()] });
    groups = TestBed.inject(GroupStore);
    store = TestBed.inject(ProductStore);
    const http = TestBed.inject(HttpTestingController);
    TestBed.tick();
    http.expectOne('/api/me').flush({
      email: 'ana@example.com',
      settings: { groups: saved, dashboard: null, background: null },
    });
    TestBed.tick();
    http.expectOne('/api/products').flush(ids.map(product));
    await TestBed.inject(ApplicationRef).whenStable();
  }

  const layout = (sections: Section[]) =>
    sections.map((s) => [s.group?.name ?? '-', s.products.map((p) => p.id)]);

  it('places products where they are dropped and keeps the rest ungrouped', async () => {
    await load([1, 2, 3, 4]);
    groups.create('GPUs');
    const gpus = groups.groups()[0].id;

    groups.move(1, gpus, 0);
    groups.move(3, gpus, 0); // dropped above product 1
    expect(layout(groups.sections())).toEqual([
      ['GPUs', [3, 1]],
      ['-', [2, 4]],
    ]);

    groups.move(3, null);
    expect(layout(groups.sections())).toEqual([
      ['GPUs', [1]],
      ['-', [2, 3, 4]],
    ]);
  });

  it('counts positions among shown products, skipping archived ids in the group', async () => {
    await load([1, 2, 3], [{ id: 'g', name: 'G', productIds: [9, 1, 2], collapsed: false }]); // 9 is archived
    groups.move(3, 'g', 1); // between 1 and 2 as the user sees them
    expect(groups.groups()[0].productIds).toEqual([9, 1, 3, 2]);
  });

  it('removing a group ungroups its products and the change is saved', async () => {
    await load([1, 2]);
    groups.create('Old');
    groups.move(1, groups.groups()[0].id);
    groups.remove(groups.groups()[0].id);
    TestBed.tick();
    expect(layout(groups.sections())).toEqual([['-', [1, 2]]]);
    expect(TestBed.inject(Account).settings().groups).toEqual([]);
  });

  it('shows or hides a whole group with one toggle', async () => {
    await load([1, 2, 3, 4, 5, 6]);
    groups.create('Pair');
    const pair = groups.groups()[0].id;
    groups.move(5, pair);
    groups.move(6, pair);
    const section = () => groups.sections()[0];

    expect(groups.shownState(section())).toBe('none'); // defaults show the first four
    groups.toggleShown(section());
    expect(groups.shownState(section())).toBe('all');
    store.toggle(5);
    expect(groups.shownState(section())).toBe('some');
    groups.toggleShown(section());
    expect(groups.shownState(section())).toBe('all');
    groups.toggleShown(section());
    expect(groups.shownState(section())).toBe('none');
  });
});
