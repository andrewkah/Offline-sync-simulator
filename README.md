# Offline-sync-simulator

Offline Sync Simulator demonstrates how field data collected in low-connectivity areas can be submitted and safely synchronized when a connection is available.

## What It Solves

Field officers may need to collect data where network access is unreliable. Retrying a submission after reconnecting can send the same record more than once. This project simulates a server endpoint that accepts a batch of records and prevents duplicate submissions from being saved.

## How It Works

- Accepts PDP records at `POST /api/v1/sync/pdp-batch`.
- Validates each record, including its submission UUID, council, PDP status, expiry year, and field-officer timestamp.
- Uses the submission UUID as an idempotency key. Duplicate records within the batch or already stored in SQLite are reported as dropped.
- Saves new records and returns a summary with committed and dropped records.

The project focuses on the synchronization API and its persistence behavior; it does not implement a field-officer app or local offline storage.
