-- =========================================
-- SINHA'S GmbH Apartment Management Schema
-- Production-Ready for PostgreSQL
-- =========================================

-- =========================
-- 1. MASTER TABLES
-- =========================

CREATE TABLE cities (
    city_id              BIGSERIAL PRIMARY KEY,
    city_name            VARCHAR(100) NOT NULL UNIQUE,
    canton               VARCHAR(100) NOT NULL,
    country              VARCHAR(100) NOT NULL DEFAULT 'Switzerland',
    postal_code_prefix   VARCHAR(20),
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE properties (
    property_id          BIGSERIAL PRIMARY KEY,
    city_id              BIGINT NOT NULL,
    property_code        VARCHAR(50) NOT NULL UNIQUE,
    property_name        VARCHAR(150) NOT NULL,
    street_address       VARCHAR(255) NOT NULL,
    postal_code          VARCHAR(20) NOT NULL,
    building_type        VARCHAR(50),  -- apartment building, chalet, house, mixed-use
    total_floors         INTEGER,
    total_units          INTEGER,
    furnished_standard   BOOLEAN NOT NULL DEFAULT TRUE,
    notes                TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_properties_city
        FOREIGN KEY (city_id) REFERENCES cities(city_id)
);

CREATE TABLE unit_types (
    unit_type_id         BIGSERIAL PRIMARY KEY,
    type_name            VARCHAR(100) NOT NULL UNIQUE, 
    description          TEXT
);

CREATE TABLE occupancy_types (
    occupancy_type_id    BIGSERIAL PRIMARY KEY,
    occupancy_name       VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE stay_types (
    stay_type_id         BIGSERIAL PRIMARY KEY,
    stay_type_name       VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE units (
    unit_id              BIGSERIAL PRIMARY KEY,
    property_id          BIGINT NOT NULL,
    unit_type_id         BIGINT NOT NULL,
    occupancy_type_id    BIGINT NOT NULL,
    unit_code            VARCHAR(50) NOT NULL UNIQUE,
    unit_name            VARCHAR(150) NOT NULL,
    floor_no             VARCHAR(20),
    apartment_no         VARCHAR(20),
    bedrooms             INTEGER NOT NULL DEFAULT 0,
    bathrooms            INTEGER NOT NULL DEFAULT 1,
    max_occupancy        INTEGER NOT NULL DEFAULT 1,
    area_sqm             NUMERIC(10,2),
    furnished            BOOLEAN NOT NULL DEFAULT TRUE,
    kitchen              BOOLEAN NOT NULL DEFAULT TRUE,
    wifi                 BOOLEAN NOT NULL DEFAULT TRUE,
    washing_machine      BOOLEAN NOT NULL DEFAULT FALSE,
    dryer                BOOLEAN NOT NULL DEFAULT FALSE,
    balcony              BOOLEAN NOT NULL DEFAULT FALSE,
    parking              BOOLEAN NOT NULL DEFAULT FALSE,
    ladies_only          BOOLEAN NOT NULL DEFAULT FALSE,
    expat_friendly       BOOLEAN NOT NULL DEFAULT TRUE,
    contract_within_60m  BOOLEAN NOT NULL DEFAULT TRUE,
    status               VARCHAR(30) NOT NULL DEFAULT 'active',
    description          TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_units_property
        FOREIGN KEY (property_id) REFERENCES properties(property_id),
    CONSTRAINT fk_units_unit_type
        FOREIGN KEY (unit_type_id) REFERENCES unit_types(unit_type_id),
    CONSTRAINT fk_units_occupancy_type
        FOREIGN KEY (occupancy_type_id) REFERENCES occupancy_types(occupancy_type_id)
);

CREATE TABLE unit_stay_types (
    unit_id              BIGINT NOT NULL,
    stay_type_id         BIGINT NOT NULL,
    PRIMARY KEY (unit_id, stay_type_id),
    CONSTRAINT fk_unit_stay_types_unit
        FOREIGN KEY (unit_id) REFERENCES units(unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_unit_stay_types_stay_type
        FOREIGN KEY (stay_type_id) REFERENCES stay_types(stay_type_id) ON DELETE CASCADE
);

-- =========================
-- 2. PLATFORM / LISTING TABLES
-- =========================

CREATE TABLE platforms (
    platform_id          BIGSERIAL PRIMARY KEY,
    platform_name        VARCHAR(100) NOT NULL UNIQUE,
    website_url          VARCHAR(255),
    platform_type        VARCHAR(50), 
    is_active            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE unit_listings (
    listing_id           BIGSERIAL PRIMARY KEY,
    unit_id              BIGINT NOT NULL,
    platform_id          BIGINT NOT NULL,
    external_listing_id  VARCHAR(150),
    listing_title        VARCHAR(255) NOT NULL,
    listing_url          VARCHAR(500),
    advertised_rent      NUMERIC(12,2),
    currency_code        VARCHAR(10) NOT NULL DEFAULT 'CHF',
    cleaning_fee         NUMERIC(12,2) DEFAULT 0,
    service_fee          NUMERIC(12,2) DEFAULT 0,
    deposit_amount       NUMERIC(12,2),
    min_stay_nights      INTEGER,
    max_stay_nights      INTEGER,
    instant_bookable     BOOLEAN NOT NULL DEFAULT FALSE,
    is_published         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_unit_listings_unit
        FOREIGN KEY (unit_id) REFERENCES units(unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_unit_listings_platform
        FOREIGN KEY (platform_id) REFERENCES platforms(platform_id),
    CONSTRAINT uq_unit_platform UNIQUE (unit_id, platform_id)
);

-- =========================
-- 3. CUSTOMER / GUEST TABLES
-- =========================

CREATE TABLE customers (
    customer_id          BIGSERIAL PRIMARY KEY,
    customer_type        VARCHAR(30) NOT NULL, 
    -- individual, company, relocation_agency
    company_name         VARCHAR(255),
    first_name           VARCHAR(100),
    last_name            VARCHAR(100),
    email                VARCHAR(255),
    phone                VARCHAR(50),
    nationality          VARCHAR(100),
    is_expat             BOOLEAN NOT NULL DEFAULT FALSE,
    preferred_language   VARCHAR(50),
    billing_address      TEXT,
    city                 VARCHAR(100),
    country              VARCHAR(100),
    passport_no          VARCHAR(100),
    id_document_type     VARCHAR(50),
    tax_number           VARCHAR(100),
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE guests (
    guest_id             BIGSERIAL PRIMARY KEY,
    customer_id          BIGINT,
    first_name           VARCHAR(100) NOT NULL,
    last_name            VARCHAR(100) NOT NULL,
    date_of_birth        DATE,
    gender               VARCHAR(20),
    nationality          VARCHAR(100),
    email                VARCHAR(255),
    phone                VARCHAR(50),
    passport_no          VARCHAR(100),
    visa_status          VARCHAR(100),
    arrival_from_country VARCHAR(100),
    emergency_contact    VARCHAR(255),
    notes                TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_guests_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- =========================
-- 4. BOOKING TABLES
-- =========================

CREATE TABLE booking_sources (
    booking_source_id    BIGSERIAL PRIMARY KEY,
    source_name          VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE bookings (
    booking_id           BIGSERIAL PRIMARY KEY,
    booking_code         VARCHAR(50) NOT NULL UNIQUE,
    unit_id              BIGINT NOT NULL,
    customer_id          BIGINT NOT NULL,
    booking_source_id    BIGINT NOT NULL,
    listing_id           BIGINT,
    stay_type_id         BIGINT NOT NULL,
    check_in_date        DATE NOT NULL,
    check_out_date       DATE NOT NULL,
    adults_count         INTEGER NOT NULL DEFAULT 1,
    children_count       INTEGER NOT NULL DEFAULT 0,
    total_guests         INTEGER NOT NULL DEFAULT 1,
    booking_status       VARCHAR(30) NOT NULL DEFAULT 'pending',
    contract_required    BOOLEAN NOT NULL DEFAULT TRUE,
    contract_sent_at     TIMESTAMP WITH TIME ZONE,
    contract_signed_at   TIMESTAMP WITH TIME ZONE,
    booking_date         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    base_rent_amount     NUMERIC(12,2) NOT NULL,
    deposit_amount       NUMERIC(12,2) DEFAULT 0,
    cleaning_fee         NUMERIC(12,2) DEFAULT 0,
    utility_fee          NUMERIC(12,2) DEFAULT 0,
    service_fee          NUMERIC(12,2) DEFAULT 0,
    discount_amount      NUMERIC(12,2) DEFAULT 0,
    tax_amount           NUMERIC(12,2) DEFAULT 0,
    total_amount         NUMERIC(12,2) NOT NULL,
    currency_code        VARCHAR(10) NOT NULL DEFAULT 'CHF',
    special_requests     TEXT,
    internal_notes       TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_bookings_unit
        FOREIGN KEY (unit_id) REFERENCES units(unit_id),
    CONSTRAINT fk_bookings_customer
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CONSTRAINT fk_bookings_source
        FOREIGN KEY (booking_source_id) REFERENCES booking_sources(booking_source_id),
    CONSTRAINT fk_bookings_listing
        FOREIGN KEY (listing_id) REFERENCES unit_listings(listing_id),
    CONSTRAINT fk_bookings_stay_type
        FOREIGN KEY (stay_type_id) REFERENCES stay_types(stay_type_id),
    CONSTRAINT chk_booking_dates CHECK (check_out_date > check_in_date)
);

CREATE TABLE booking_guests (
    booking_id           BIGINT NOT NULL,
    guest_id             BIGINT NOT NULL,
    is_primary_guest     BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (booking_id, guest_id),
    CONSTRAINT fk_booking_guests_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_guests_guest
        FOREIGN KEY (guest_id) REFERENCES guests(guest_id) ON DELETE CASCADE
);

-- =========================
-- 5. CONTRACT TABLES
-- =========================

CREATE TABLE contract_templates (
    template_id          BIGSERIAL PRIMARY KEY,
    template_name        VARCHAR(150) NOT NULL UNIQUE,
    stay_type_id         BIGINT,
    language_code        VARCHAR(20) NOT NULL DEFAULT 'EN',
    template_version     VARCHAR(50),
    template_body        TEXT NOT NULL,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contract_templates_stay_type
        FOREIGN KEY (stay_type_id) REFERENCES stay_types(stay_type_id)
);

CREATE TABLE contracts (
    contract_id          BIGSERIAL PRIMARY KEY,
    booking_id           BIGINT NOT NULL,
    template_id          BIGINT,
    contract_number      VARCHAR(100) NOT NULL UNIQUE,
    contract_status      VARCHAR(30) NOT NULL DEFAULT 'draft',
    start_date           DATE NOT NULL,
    end_date             DATE NOT NULL,
    signed_date          DATE,
    rent_amount          NUMERIC(12,2) NOT NULL,
    deposit_amount       NUMERIC(12,2) DEFAULT 0,
    utility_terms        TEXT,
    cancellation_terms   TEXT,
    document_path        VARCHAR(500),
    generated_in_minutes INTEGER,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_contracts_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_contracts_template
        FOREIGN KEY (template_id) REFERENCES contract_templates(template_id),
    CONSTRAINT chk_contract_dates CHECK (end_date > start_date)
);

-- =========================
-- 6. SERVICES TABLES
-- =========================

CREATE TABLE services (
    service_id           BIGSERIAL PRIMARY KEY,
    service_name         VARCHAR(150) NOT NULL UNIQUE,
    service_category     VARCHAR(100),
    description          TEXT,
    default_price        NUMERIC(12,2) DEFAULT 0,
    currency_code        VARCHAR(10) NOT NULL DEFAULT 'CHF',
    is_active            BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE booking_services (
    booking_service_id   BIGSERIAL PRIMARY KEY,
    booking_id           BIGINT NOT NULL,
    service_id           BIGINT NOT NULL,
    quantity             INTEGER NOT NULL DEFAULT 1,
    unit_price           NUMERIC(12,2) NOT NULL,
    total_price          NUMERIC(12,2) NOT NULL,
    requested_at         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    service_status       VARCHAR(30) NOT NULL DEFAULT 'requested',
    notes                TEXT,
    CONSTRAINT fk_booking_services_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_booking_services_service
        FOREIGN KEY (service_id) REFERENCES services(service_id)
);

-- =========================
-- 7. PAYMENTS TABLES
-- =========================

CREATE TABLE payment_methods (
    payment_method_id    BIGSERIAL PRIMARY KEY,
    method_name          VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE payments (
    payment_id           BIGSERIAL PRIMARY KEY,
    booking_id           BIGINT NOT NULL,
    payment_method_id    BIGINT NOT NULL,
    payment_reference    VARCHAR(150),
    payment_date         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    amount               NUMERIC(12,2) NOT NULL,
    currency_code        VARCHAR(10) NOT NULL DEFAULT 'CHF',
    payment_type         VARCHAR(50) NOT NULL,
    payment_status       VARCHAR(30) NOT NULL DEFAULT 'received',
    notes                TEXT,
    CONSTRAINT fk_payments_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_method
        FOREIGN KEY (payment_method_id) REFERENCES payment_methods(payment_method_id)
);

-- =========================
-- 8. PRICING TABLES
-- =========================

CREATE TABLE rate_plans (
    rate_plan_id         BIGSERIAL PRIMARY KEY,
    rate_plan_name       VARCHAR(150) NOT NULL UNIQUE,
    stay_type_id         BIGINT,
    billing_cycle        VARCHAR(50), 
    cancellation_policy  TEXT,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_rate_plans_stay_type
        FOREIGN KEY (stay_type_id) REFERENCES stay_types(stay_type_id)
);

CREATE TABLE unit_rate_plans (
    unit_rate_plan_id    BIGSERIAL PRIMARY KEY,
    unit_id              BIGINT NOT NULL,
    rate_plan_id         BIGINT NOT NULL,
    valid_from           DATE NOT NULL,
    valid_to             DATE,
    price_amount         NUMERIC(12,2) NOT NULL,
    currency_code        VARCHAR(10) NOT NULL DEFAULT 'CHF',
    min_stay_nights      INTEGER,
    max_stay_nights      INTEGER,
    is_active            BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_unit_rate_plans_unit
        FOREIGN KEY (unit_id) REFERENCES units(unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_unit_rate_plans_rate_plan
        FOREIGN KEY (rate_plan_id) REFERENCES rate_plans(rate_plan_id),
    CONSTRAINT chk_unit_rate_dates CHECK (valid_to IS NULL OR valid_to >= valid_from)
);

-- =========================
-- 9. AVAILABILITY / BLOCKS
-- =========================

CREATE TABLE availability_blocks (
    block_id             BIGSERIAL PRIMARY KEY,
    unit_id              BIGINT NOT NULL,
    booking_id           BIGINT,
    block_start_date     DATE NOT NULL,
    block_end_date       DATE NOT NULL,
    block_reason         VARCHAR(100) NOT NULL,
    notes                TEXT,
    created_at           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_availability_blocks_unit
        FOREIGN KEY (unit_id) REFERENCES units(unit_id) ON DELETE CASCADE,
    CONSTRAINT fk_availability_blocks_booking
        FOREIGN KEY (booking_id) REFERENCES bookings(booking_id) ON DELETE SET NULL,
    CONSTRAINT chk_block_dates CHECK (block_end_date > block_start_date)
);

-- =========================
-- 10. DOCUMENTS
-- =========================

CREATE TABLE documents (
    document_id          BIGSERIAL PRIMARY KEY,
    related_table        VARCHAR(100) NOT NULL,
    related_id           BIGINT NOT NULL,
    document_type        VARCHAR(100) NOT NULL,
    file_name            VARCHAR(255) NOT NULL,
    file_path            VARCHAR(500) NOT NULL,
    mime_type            VARCHAR(100),
    uploaded_at          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    uploaded_by          VARCHAR(100),
    notes                TEXT
);

-- =========================
-- 11. INDEXES
-- =========================

CREATE INDEX idx_properties_city_id ON properties(city_id);
CREATE INDEX idx_units_property_id ON units(property_id);
CREATE INDEX idx_unit_listings_unit_id ON unit_listings(unit_id);
CREATE INDEX idx_bookings_unit_id ON bookings(unit_id);
CREATE INDEX idx_bookings_customer_id ON bookings(customer_id);
CREATE INDEX idx_bookings_checkin_checkout ON bookings(check_in_date, check_out_date);
CREATE INDEX idx_contracts_booking_id ON contracts(booking_id);
CREATE INDEX idx_payments_booking_id ON payments(booking_id);
CREATE INDEX idx_availability_blocks_unit_dates ON availability_blocks(unit_id, block_start_date, block_end_date);

-- =========================================
-- POSTGRESQL DEPENDENT MASTER DATA SEEDING
-- =========================================

-- Stay Types
INSERT INTO stay_types (stay_type_name) VALUES
('Long Term'), ('Short Term'), ('Tourist');

-- Occupancy Types
INSERT INTO occupancy_types (occupancy_name) VALUES
('Entire Unit'), ('Private Room'), ('Shared Room'), ('Ladies Only'), ('Family Only');

-- Unit Types
INSERT INTO unit_types (type_name, description) VALUES
('Studio', 'Fully furnished studio apartment'),
('1 Bedroom', 'One-bedroom furnished apartment'),
('2 Bedroom', 'Two-bedroom furnished apartment'),
('Penthouse', 'Premium penthouse apartment'),
('Ladies Sharing', 'Ladies-only sharing apartment'),
('Family Apartment', 'Apartment suitable for family stay'),
('Executive Apartment', 'Business apartment for executives');

-- Platforms
INSERT INTO platforms (platform_name, website_url, platform_type) VALUES
('Direct', NULL, 'direct'),
('Homegate', 'https://www.homegate.ch', 'classifieds'),
('Flatfox', 'https://flatfox.ch', 'classifieds'),
('Airbnb', 'https://www.airbnb.com', 'OTA'),
('Booking.com', 'https://www.booking.com', 'OTA');

-- Booking Sources
INSERT INTO booking_sources (source_name) VALUES
('Direct'), ('Homegate'), ('Flatfox'), ('Airbnb'), ('Booking.com'), 
('Corporate'), ('Agent'), ('Relocation Agency');

-- Payment Methods
INSERT INTO payment_methods (method_name) VALUES
('Bank Transfer'), ('Credit Card'), ('Cash'), ('Stripe'), 
('Airbnb Payout'), ('Booking.com Payout');

-- =========================================
-- SWISS CITIES & PROPERTIES SAMPLE DATA
-- =========================================

INSERT INTO cities (city_name, canton, country, postal_code_prefix) VALUES
('Zürich', 'Zürich', 'Switzerland', '80'),
('Basel', 'Basel-Stadt', 'Switzerland', '40'),
('Davos', 'Graubünden', 'Switzerland', '72'),
('Lauterbrunnen', 'Bern', 'Switzerland', '38'),
('Wallisellen', 'Zürich', 'Switzerland', '83');

-- Insert Sample Properties based on Cities
INSERT INTO properties (city_id, property_code, property_name, street_address, postal_code, building_type, total_floors, total_units, furnished_standard) VALUES
((SELECT city_id FROM cities WHERE city_name = 'Zürich'), 'ZUR-01', 'Zürich Central Suites', 'Bahnhofstrasse 10', '8001', 'mixed-use', 5, 20, TRUE),
((SELECT city_id FROM cities WHERE city_name = 'Basel'), 'BAS-01', 'Basel Riverside', 'Rheingasse 15', '4058', 'apartment building', 4, 15, TRUE),
((SELECT city_id FROM cities WHERE city_name = 'Davos'), 'DAV-01', 'Davos Alpine Retreat', 'Promenade 50', '7270', 'chalet', 3, 10, TRUE),
((SELECT city_id FROM cities WHERE city_name = 'Lauterbrunnen'), 'LAU-01', 'Lauterbrunnen Valley Views', 'Zilwald 20', '3822', 'house', 2, 4, TRUE),
((SELECT city_id FROM cities WHERE city_name = 'Wallisellen'), 'WAL-01', 'Wallisellen Business Hub', 'Melchrütistrasse 8', '8304', 'apartment building', 6, 25, TRUE);

-- Sample Units Setup
INSERT INTO units (property_id, unit_type_id, occupancy_type_id, unit_code, unit_name, floor_no, apartment_no, bedrooms, area_sqm) VALUES
(
    (SELECT property_id FROM properties WHERE property_code = 'WAL-01'),
    (SELECT unit_type_id FROM unit_types WHERE type_name = 'Penthouse'),
    (SELECT occupancy_type_id FROM occupancy_types WHERE occupancy_name = 'Entire Unit'),
    'WAL-PH-01', 'Penthouse Wallisellen', '6', '601', 3, 150.00
),
(
    (SELECT property_id FROM properties WHERE property_code = 'ZUR-01'),
    (SELECT unit_type_id FROM unit_types WHERE type_name = 'Studio'),
    (SELECT occupancy_type_id FROM occupancy_types WHERE occupancy_name = 'Entire Unit'),
    'ZUR-ST-05', 'Zurich Business Studio', '2', '205', 0, 45.00
),
(
    (SELECT property_id FROM properties WHERE property_code = 'DAV-01'),
    (SELECT unit_type_id FROM unit_types WHERE type_name = 'Family Apartment'),
    (SELECT occupancy_type_id FROM occupancy_types WHERE occupancy_name = 'Entire Unit'),
    'DAV-FA-02', 'Alpine Family Suite', '1', '102', 2, 110.00
);

-- Link Units to Sample Platforms (Listings)
INSERT INTO unit_listings (unit_id, platform_id, listing_title, advertised_rent, currency_code) VALUES
((SELECT unit_id FROM units WHERE unit_code = 'WAL-PH-01'), (SELECT platform_id FROM platforms WHERE platform_name = 'Airbnb'), 'Exclusive Penthouse Wallisellen', 250.00, 'CHF'),
((SELECT unit_id FROM units WHERE unit_code = 'ZUR-ST-05'), (SELECT platform_id FROM platforms WHERE platform_name = 'Booking.com'), 'Central Zurich Studio', 150.00, 'CHF');
