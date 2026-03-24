# Uploading Original Apartments File to New Schema

## Goal Description
The user requested to upload the file `ORIGINAL TOTAL APARTMENTS AND AVAILIBILITY -with details -6.3.26.xlsx` to the MongoDB database, based strictly on the newly designed 42-table schema (`sinhas_gmbh_schema.html`).

The new schema breaks properties down hierarchically into `cities` → `districts` → `buildings` → `apartments`. We will write a dedicated Python script (`upload_apartments.py`) that performs an ETL (Extract, Transform, Load) operation to process the flat Excel file into these relational collections inside MongoDB.

## Proposed Changes

### 1. New File: `upload_apartments.py`
A robust data migration script will be created to read the Excel file's `OCCUPANCY -Apartment` sheet (skipping the first row for correct headers) and process the data as follows:

- **Cities Collection (`core.cities`)**:
  - Extract unique cities (cleaning names like "Zurich", "Glattbrugg", etc.).
  - Insert them into the `cities` collection with a unique `city_id` (or standard MongoDB `_id`), `city_code`, and `country_code = 'CH'`.

- **Buildings Collection (`core.buildings`)**:
  - Group identical addresses (`Apartment address` + `street no` + `pin code` + `City`) into unique buildings.
  - Generates a `building_code` (e.g., `BLDG-001`).
  - Sets default required parameters like `has_elevator = False`, `building_status = 'active'`.

- **Apartments Collection (`core.apartments`)**:
  - Create the core apartment documents linked to the newly generated `building_id`.
  - Field Mapping:
    - `apt_code` = Combination of City Prefix + Row Index (or `AWN NO` if available).
    - `unit_number` = `POSITION`
    - `floor_number` = Parsed from `FLOOR` (Default: 0 for Ground).
    - `area_sqm` = `Apartment SQMT` (Default 50 if missing).
    - `bedrooms` = `NO. OF ROOMS` (Default 1 if missing).
    - `bathrooms` = 1 (Default value).
    - `max_occupants` = `bedrooms * 2` (Default estimation).
    - `is_furnished` = `True` (as per schema specs).
    - `apartment_status` = Mapped from the occupancy column (`Unnamed: 12`) to 'occupied' or 'available'.

### 2. Execution
Once the script is prepared, we will run it against the target MongoDB database (`sinharealty`).

## Verification Plan
### Automated Tests
- The script will be run locally to verify correct data parsing, printing a summary of extracted cities, buildings, and apartments before actual insertion.

### Manual Verification
- Execute `upload_apartments.py`.
- Query the `cities`, `buildings`, and `apartments` collections in MongoDB to ensure records were successfully inserted and relationships are intact.
