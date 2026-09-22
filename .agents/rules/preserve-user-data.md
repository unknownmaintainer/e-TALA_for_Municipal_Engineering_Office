# Preserve User-Configured Data

## Rule: NEVER modify user-adjusted data during code updates

When making code changes, bug fixes, UI updates, or feature additions, **DO NOT** touch or alter any of the following:

1. **Map Coordinates & Pinned Points**: Any GIS coordinates, map markers, or location data that users have manually set or corrected (e.g., barangay coordinates, project site pins).
2. **Seed Data**: Pre-populated records, barangay lists, default lookup values, or any seeded database entries that have already been configured or corrected by the user.
3. **User Configurations & Settings**: Saved preferences, system settings, thresholds, or any configuration values that were manually tuned by the user.
4. **Database Migration Data**: Do not create migrations that reset, overwrite, or re-seed data that users have already adjusted.
5. **Static Data Files**: JSON fixtures, CSV imports, or any data files that contain user-corrected values.

### Why
Users spend significant time manually correcting and fine-tuning data (e.g., fixing map pin positions, adjusting barangay coordinates, updating seed records). Overwriting this work forces users to redo corrections repeatedly, which is unacceptable.

### What TO Do Instead
- Only modify **code logic, templates, CSS, and JavaScript**.
- If a data-related change is genuinely needed, **ask the user first** before touching any configured data.
- When writing migrations, ensure they are **additive only** (add new fields/tables) and never reset existing user-corrected values.
