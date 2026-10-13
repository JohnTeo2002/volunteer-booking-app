import { ApiError, Booking, BookingRequest, ErrorEnvelope, Slot, ValidationErrorDetail } from '../types/api';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function validateApiUrl(urlStr: string): string {
  try {
    const url = new URL(urlStr);
    const isLocal = url.hostname === 'localhost' || url.hostname === '127.0.0.1';
    if (url.protocol !== 'https:' && !isLocal) {
      throw new Error('Production API URL must use HTTPS to secure admin tokens.');
    }
  } catch (e: unknown) {
    if (urlStr.startsWith('http://') && !urlStr.includes('localhost') && !urlStr.includes('127.0.0.1')) {
      throw new Error('Production API URL must use HTTPS.');
    }
  }
  return urlStr;
}

function isValidationErrorDetail(item: unknown): item is ValidationErrorDetail {
  if (!item || typeof item !== 'object') return false;
  return 'field' in item && 'message' in item && typeof (item as ValidationErrorDetail).field === 'string' && typeof (item as ValidationErrorDetail).message === 'string';
}

function isErrorEnvelope(data: unknown): data is ErrorEnvelope {
  if (!data || typeof data !== 'object') return false;
  if (!('error' in data)) return false;
  const err = (data as { error: unknown }).error;
  if (!err || typeof err !== 'object') return false;
  if (!('code' in err) || !('message' in err)) return false;
  const errObj = err as { code: unknown; message: unknown; details: unknown };
  if (typeof errObj.code !== 'string' || typeof errObj.message !== 'string') return false;
  if (errObj.details !== null && errObj.details !== undefined) {
    if (!Array.isArray(errObj.details)) return false;
    for (const d of errObj.details) {
      if (!isValidationErrorDetail(d)) return false;
    }
  }
  return true;
}

async function handleResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get('content-type');
  let data: unknown = null;

  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  }

  if (!response.ok) {
    let code = 'INTERNAL_ERROR';
    let message = response.statusText || 'An error occurred';
    let details: ValidationErrorDetail[] | null = null;

    if (isErrorEnvelope(data)) {
      code = data.error.code;
      message = data.error.message;
      details = data.error.details ?? null;
    }

    throw new ApiError(code, message, details);
  }

  if (data === null || data === undefined) {
    throw new ApiError('INTERNAL_ERROR', 'Expected JSON response but received empty body.');
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
  const baseUrl = validateApiUrl(API_BASE);
  const response = await fetch(`${baseUrl}/booking/${id}`, {
    method: 'GET',
    headers: {
      'X-Admin-Token': adminToken,
    },
  });
  return handleResponse<Booking>(response);
}
