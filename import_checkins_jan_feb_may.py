"""One-off import of checkins_jan_feb_may_2026 (1).xlsx into the Revenue
Tracker and Reservation Details collections used by Guest Client Analytics.

Reuses app.py's own business logic (auto city derivation, exact-duplicate
skip, the max-twice-per-name / back-to-back rule) instead of re-implementing
it, so this behaves exactly like using the admin panel's "+ Add New" on each
sheet.
"""
import datetime
import math
import sys

import pandas as pd

import app as app_module

SRC_FILE = r"C:\Users\Debangshu05\Downloads\checkins_jan_feb_may_2026 (1).xlsx"

db = app_module.get_db()


def clean(v):
    if v is None or pd.isna(v):
        return ''
    if isinstance(v, datetime.datetime):
        return v.strftime('%Y-%m-%d')
    return str(v).strip()


def build_records(row):
    name = clean(row['Guest Name'])
    address = clean(row['Apartment Address'])
    check_in = clean(row['Check-in Date'])
    check_out = clean(row['Check-out Date'])
    remarks = clean(row['Remarks'])
    stay_type = clean(row['Long term/Short Term'])
    deposit = clean(row['Deposit '])
    cleaning = clean(row['Cleaning'])
    rent = clean(row['Rent'])
    email = clean(row['Email'])
    phone = clean(row['Phone number'])

    rt = {
        'Guest Full Name': name,
        'Property Address': address,
        'Check-in Date': check_in,
        'Check-out Date': check_out,
        'Mobile': phone,
        'Email': email,
        'Actual Deposit': deposit,
        'Actual Cleaning': cleaning,
        'Monthly Rent (CHF)': rent,
        'Stay Type (Short/Long)': stay_type,
        'Remarks': remarks,
        'Currency': 'CHF',
        'Booking Status': 'Confirmed',
    }
    rd = {
        'Guest Name': name,
        'Address': address,
        'Check In Date': check_in,
        'Check Out Date': check_out,
        'Contact No': phone,
        'Email': email,
        'Deposit Amt': deposit,
        'Cleaning Fee': cleaning,
        'Monthly Rent': rent,
        'Remarks': remarks,
    }
    return rt, rd


def add_record(collection, data, dry_run=False):
    """Mirrors /api/guest-client-add/<collection> in app.py."""
    if collection == 'revenue_tracker':
        app_module._apply_auto_city(data)

    if collection in app_module.DUPLICATE_CHECK_EXCLUDE_FIELDS:
        existing = app_module.find_exact_duplicate(collection, data)
        if existing:
            return 'duplicate', existing['_id']

    violation = app_module.check_name_duplicate_violation(collection, data)
    if violation:
        return 'violation', violation

    if dry_run:
        return 'would_insert', None

    if collection == 'revenue_tracker':
        data['SNo'] = app_module._next_running_number(db[collection], 'SNo')
    elif collection == 'reservation_details':
        data['SL NO'] = app_module._next_running_number(db[collection], 'SL NO')

    result = db[collection].insert_one(data)
    app_module.mark_collection_updated(collection)
    data['_id'] = result.inserted_id
    app_module.sync_common_fields(collection, data)
    return 'inserted', result.inserted_id


def main():
    dry_run = '--dry-run' in sys.argv
    df = pd.read_excel(SRC_FILE, sheet_name='Jan-Feb-May 2026')
    df = df.dropna(how='all')

    stats = {'rt': {'inserted': 0, 'would_insert': 0, 'duplicate': 0, 'violation': 0},
              'rd': {'inserted': 0, 'would_insert': 0, 'duplicate': 0, 'violation': 0}}
    violations = []

    for _, row in df.iterrows():
        if not clean(row.get('Guest Name')):
            continue
        rt, rd = build_records(row)

        status, info = add_record('revenue_tracker', dict(rt), dry_run=dry_run)
        stats['rt'][status] += 1
        if status == 'violation':
            violations.append(('revenue_tracker', rt['Guest Full Name'], info))

        status, info = add_record('reservation_details', dict(rd), dry_run=dry_run)
        stats['rd'][status] += 1
        if status == 'violation':
            violations.append(('reservation_details', rd['Guest Name'], info))

    print('DRY RUN' if dry_run else 'LIVE RUN')
    print('Revenue Tracker:', stats['rt'])
    print('Reservation Details:', stats['rd'])
    if violations:
        print('\nSkipped due to name-duplicate rule:')
        for coll, name, msg in violations:
            print(f'  [{coll}] {name}: {msg}')


if __name__ == '__main__':
    main()
