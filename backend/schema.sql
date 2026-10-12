-- Food Bank Volunteer Booking System Database Schema
-- SQLite

CREATE TABLE IF NOT EXISTS volunteer_slots (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,                         -- event identifier (no foreign key)
    date TEXT NOT NULL,                                -- format: YYYY-MM-DD
    start_time TEXT NOT NULL,                          -- format: HH:MM (24-hour local time)
    end_time TEXT NOT NULL,                            -- format: HH:MM (24-hour local time)
    capacity INTEGER NOT NULL CHECK(capacity > 0),
    booked INTEGER NOT NULL DEFAULT 0 CHECK(booked >= 0), -- booked is a denormalized count changed only by the booking transaction in app/db.py
    CHECK (booked <= capacity)
);

CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY,
    slot_id INTEGER NOT NULL REFERENCES volunteer_slots(id),
    volunteer_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,                               -- required phone number
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, -- UTC timestamp
    UNIQUE(slot_id, email)
);
