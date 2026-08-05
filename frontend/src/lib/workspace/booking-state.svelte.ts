import type { Availability, BookingLineCreate } from '$lib/api';

export type BookingDraftLine = BookingLineCreate & {
  client_id: string;
};

export type BookingDraft = {
  title: string;
  person_id: string;
  starts_at: string;
  ends_at: string;
  notes: string;
  lines: BookingDraftLine[];
};

export type BookingFormState = {
  title: string;
  starts_at: string;
  ends_at: string;
  asset_id: string;
  location_id: string;
  quantity: number;
};

export type BookingDraftLineFormState = {
  asset_id: string;
  location_id: string;
  quantity: number;
  notes: string;
};

export function createBookingState() {
  let availability = $state<Availability | null>(null);
  let bookingForm = $state<BookingFormState>(emptyBookingForm());
  let bookingDraft = $state<BookingDraft>(emptyBookingDraft());
  let bookingDraftLineForm = $state<BookingDraftLineFormState>(emptyBookingDraftLineForm());

  return {
    get availability() {
      return availability;
    },
    set availability(value: Availability | null) {
      availability = value;
    },
    get bookingForm() {
      return bookingForm;
    },
    set bookingForm(value: BookingFormState) {
      bookingForm = value;
    },
    get bookingDraft() {
      return bookingDraft;
    },
    set bookingDraft(value: BookingDraft) {
      bookingDraft = value;
    },
    get bookingDraftLineForm() {
      return bookingDraftLineForm;
    },
    set bookingDraftLineForm(value: BookingDraftLineFormState) {
      bookingDraftLineForm = value;
    },
    resetBookingForm() {
      bookingForm = emptyBookingForm();
      availability = null;
    },
    clearAvailability() {
      availability = null;
    },
    addDraftLine(line: BookingLineCreate) {
      bookingDraft.lines = [
        ...bookingDraft.lines,
        {
          ...line,
          client_id: crypto.randomUUID()
        }
      ];
      availability = null;
    },
    removeDraftLine(clientId: string) {
      bookingDraft.lines = bookingDraft.lines.filter((line) => line.client_id !== clientId);
      availability = null;
    },
    resetDraft() {
      bookingDraft = emptyBookingDraft();
      bookingDraftLineForm = emptyBookingDraftLineForm();
      availability = null;
    },
    resetDraftLineForm() {
      bookingDraftLineForm = emptyBookingDraftLineForm();
    }
  };
}

function emptyBookingForm(): BookingFormState {
  return {
    title: '',
    starts_at: '',
    ends_at: '',
    asset_id: '',
    location_id: '',
    quantity: 1
  };
}

function emptyBookingDraft(): BookingDraft {
  return {
    title: '',
    person_id: '',
    starts_at: '',
    ends_at: '',
    notes: '',
    lines: []
  };
}

function emptyBookingDraftLineForm(): BookingDraftLineFormState {
  return {
    asset_id: '',
    location_id: '',
    quantity: 1,
    notes: ''
  };
}
