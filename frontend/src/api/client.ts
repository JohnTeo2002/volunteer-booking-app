import { ApiError, Booking, BookingRequest, ErrorEnvelope, Slot } from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  let data: unknown = null;

  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  }

  if (!response.ok) {
    let code = 'INTERNAL_ERROR';
    let message = response.statusText || 'An error occurred';
    let details = null;

    if (data && typeof data === 'object' && 'error' in data) {
      const envelope = data as ErrorEnvelope;
      if (envelope.error && typeof envelope.error === 'object') {
        code = envelope.error.code || code;
        message = envelope.error.message || message;
        details = envelope.error.details || null;
      }
    }

    throw new ApiError(code, message, details);
  }

  return data as T;
}

export async function fetchSlots(eventId?: number, date?: string): Promise<Slot[]> {
  const params = new URLSearchParams();
  if (eventId !== undefined) params.append('event_id', eventId.toString());
  if (date) params.append('date', date);

  const query = params.toString();
  const url = `${API_BASE}/slots${query ? `?${query}` : ''}`;

  const response = await fetch(url);
  return handleResponse<Slot[]>(response);
}

export async function createBooking(request: BookingRequest): Promise<Booking> {
  const response = await fetch(`${API_BASE}/book`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });
  return handleResponse<Booking>(response);
}

export async function fetchBooking(id: number, adminToken: string): Promise<Booking> {
  const response = await fetch(`${API_BASE}/booking/${id}`, {
    method: 'GET',
    headers: {
      'X-Admin-Token': adminToken,
    },
  });
  return handleResponse<Booking>(response);
}
