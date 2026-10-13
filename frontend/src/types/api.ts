export interface Slot {
  id: number;
  event_id: number;
  date: string;
  start_time: string;
  end_time: string;
  capacity: number;
  booked: number;
  remaining: number;
}

export interface BookingRequest {
  slot_id: number;
  volunteer_name: string;
  email: string;
  phone: string;
}

export interface Booking {
  id: number;
  slot_id: number;
  volunteer_name: string;
  email: string;
  phone: string;
  created_at: string;
}

export interface ValidationErrorDetail {
  field: string;
  message: string;
}

export interface ErrorEnvelopeBody {
  code: string;
  message: string;
  details: ValidationErrorDetail[] | null;
}

export interface ErrorEnvelope {
  error: ErrorEnvelopeBody;
}

export class ApiError extends Error {
  code: string;
  details: ValidationErrorDetail[] | null;

  constructor(code: string, message: string, details: ValidationErrorDetail[] | null = null) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
  }
}
