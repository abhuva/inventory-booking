import type { Basket } from '$lib/api';

export function createBasketState() {
  let activeBasket = $state<Basket | null>(null);
  let basketTitle = $state('');
  let basketNotes = $state('');

  return {
    get activeBasket() {
      return activeBasket;
    },
    set activeBasket(value: Basket | null) {
      activeBasket = value;
    },
    get basketTitle() {
      return basketTitle;
    },
    set basketTitle(value: string) {
      basketTitle = value;
    },
    get basketNotes() {
      return basketNotes;
    },
    set basketNotes(value: string) {
      basketNotes = value;
    },
    syncForm() {
      basketTitle = activeBasket?.title ?? '';
      basketNotes = activeBasket?.notes ?? '';
    },
    clear() {
      activeBasket = null;
      basketTitle = '';
      basketNotes = '';
    }
  };
}
