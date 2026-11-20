# Travel API Research — Travel and Tourism Planning & Booking Platform

**Project:** Travel and Tourism Planning & Booking Platform (Group Bohemian Software, BLG 411E)
**Activity:** WBS-2.1 — Travel API research, test account, limits and fallback plan
**Owner:** Mehmet Berkay Balcı (Technical Lead for external travel API integration)
**Version:** 1.0
**Date:** 20 Nov 2026
**Based on:** Project Charter v1.1 and Project Plan v1.1

This document records which external travel APIs the project uses for flights and hotels, how they were tested, their limits, and what the team does if a provider is unavailable (risk R-08).

---

## 1. Summary

The charter's example provider, **Amadeus Self-Service, was decommissioned on 17 July 2026**. New registrations were paused in March 2026, all self-service keys were disabled on the cutover date, and the official SDKs were archived. Only the Amadeus Enterprise portal remains, and it requires a commercial agreement. Risk **R-08** (travel API unavailable or limited) has therefore materialized.

Recommended replacement:

| Domain | Primary provider | Fallback |
|---|---|---|
| Flights | **Duffel** (test mode) | Seeded sample data |
| Hotels | **LiteAPI / Nuitée** (sandbox key) | Seeded sample data |

Both are free to use for testing. Duffel test mode was verified with a real search (see section 3). LiteAPI sandbox was verified with real calls (see section 4).

## 2. Candidates

| Provider | Domain | Free access | Verdict |
|---|---|---|---|
| Amadeus Self-Service | Flights, hotels | None for new developers since July 2026 | Rejected |
| Amadeus Enterprise | Flights, hotels | Sales contract, accreditation | Rejected (not feasible for a course project) |
| **Duffel** | Flights | Test mode, free. Search, offer, order flow. Verified with a real call | **Selected for flights** |
| **LiteAPI (Nuitée)** | Hotels | Free sandbox key. Rates search, prebook, book | **Selected for hotels** |
| Travelpayouts | Flights | Free signup, but the search API reportedly requires large traffic (50K MAU) | Rejected |
| FlightAPI.io, AeroDataBox | Flights / status | Very small free quotas, no booking flow | Rejected |
| Apify / RapidAPI wrappers (Google Flights data) | Flights | Third-party scrapers, unclear terms, no booking | Rejected |

## 3. Duffel (flights)

- **Access:** free sign-up at app.duffel.com. In "Developer test mode", create an access token (prefix `duffel_test_`). Verified: the token works and returns offers (`live_mode: false`).
- **Flow:** offer request (search) → offers → order (booking). Maps to our booking model, where a flight is stored as a snapshot (`item_type = 'FLIGHT'`).
- **Verified sample** (`POST /air/offer_requests?return_offers=true`, IST → LHR, 20 Dec 2026, 1 adult, economy; saved as `samples/duffel_offer_request_IST_LHR.json`):
  - 18 offers, 136 KB response.
  - Airlines: Lufthansa (14), Iberia, British Airways, Vueling, Duffel Airways. So test mode returns **real airline names**, not only "Duffel Airways". The data is still sandbox data, so schedules and prices are not authoritative.
  - Prices: 117.64 – 292.22 EUR, all in EUR. The currency is not chosen by us, so the UI must show the returned currency and not assume one.
  - 3 offers are direct, 15 have one stop (2 segments). Segment count must be handled in the model.
  - Offers expire **30 minutes** after creation (`expires_at`). `payment_required_by` is about 3 days out, `price_guarantee_expires_at` about 2 days out.
  - Useful fields per offer: `id`, `total_amount`, `total_currency`, `base_amount`, `tax_amount`, `owner.name`, `slices[].duration`, `slices[].segments[]` (origin and destination IATA codes, `departing_at`, `arriving_at`, `marketing_carrier`, flight number, aircraft, terminals), per-passenger baggage and cabin, `conditions` (change and refund rules and penalties).
  - Timestamps in segments have no timezone offset (local airport time). Store them as local date-times and show them that way.
- **Offers expire:** the booking flow must re-search or show an expiry message. We store a price snapshot at booking time.
- **Limits and costs:** test mode is free and no quota or expiry was found in the docs. Live mode charges per order plus a percentage and has a search-to-book ratio policy (1500:1, a commercial rule). Not relevant for this project.
  - **Rate limit (measured):** the offer request endpoint returns `ratelimit-limit: 30` with `ratelimit-remaining` and `ratelimit-reset` headers. The reset time falls on a minute boundary, so the window is probably 60 seconds (not confirmed in the official docs). Exceeding the limit returns HTTP 429.
  - **Mitigation:** cache identical route and date searches for 5-10 minutes, log `ratelimit-remaining`, back off until `ratelimit-reset` on 429, and use mock providers in tests and CI.
  - **Verified route coverage** (20 Dec 2026, 1 adult, economy, offers returned): IST-CDG 60, IST-FRA 58, IST-DXB 50, IST-AYT 31, IST-ESB 22, IST-LHR 17, IST-JFK 11. Counts change between calls, so the demo must not depend on exact numbers.

## 4. LiteAPI / Nuitée Connect (hotels)

LiteAPI is now branded **Nuitée Connect** (dashboard at connect.nuitee.com, docs at docs.liteapi.travel).

- **Access:** free account, sandbox key (`sand_...`) from Developer tools. A credit card is only needed for a production key. Sent in the `X-API-Key` header. Base URL `https://api.liteapi.travel/v3.0`.
- **Endpoints verified with real calls:**
  - `GET /data/hotels?countryCode=TR&cityName=Istanbul&limit=10` returns static hotel data (10 hotels, 24 KB).
  - `POST /hotels/rates` with `cityName` + `countryCode`, `checkin`, `checkout`, `occupancies`, `currency`, `guestNationality`, `maxRatesPerHotel: 1` returns rates (655 KB). City search works in sandbox, no hotel IDs are needed first.
- **Verified sample** (Istanbul, 20–22 Dec 2026, 2 adults, USD): rates for **188 hotels**, one room offer each (`maxRatesPerHotel: 1`). Prices 83.24 – 1503.82 USD. Board types: Room Only (141), Breakfast Included (46), Half Board (1). Response has `sandbox: true`.
- **Hotel static fields:** `id` (e.g. `lp6a87c`), `name`, `chain`, `stars`, `rating`, `reviewCount`, `address`, `city`, `country`, `latitude`, `longitude`, `main_photo`, `thumbnail`, `hotelDescription` (HTML), `facilityIds`.
- **Rate fields:** `offerId` (needed for prebook), `roomTypeId`, `rates[]` with `name` (room name), `boardType`/`boardName`, `maxOccupancy`, `retailRate.total`, `suggestedSellingPrice`, `taxesAndFees`, `cancellationPolicies` (`refundableTag`, cancel times and penalties), `paymentTypes`, `perks`.
- **Offers are short-lived:** `offerId` must be used for prebook soon after search. Never store it long-term.
- **Important for the review module:** LiteAPI hotels already carry an external `rating` and `reviewCount`. Our own reviews (WBS-12.1) are separate data. The UI must label which is which, and our average rating comes only from our own `reviews` table.
- **Limits:** sandbox **5 requests/second**, HTTP 429 when exceeded, so use exponential backoff. Core booking endpoints are free, some premium endpoints are billed (see the provider's pricing page).
- **Flights:** Nuitée also offers a Flights API, but access must be requested via a dashboard ticket and the sandbox data is limited and unreliable for pricing. Not used. Flights stay on Duffel.
- **Owner of the hotel integration:** İnci (WBS-3.1). Samples captured by Berkay.

## 5. Fallback plan (R-08 mitigation)

1. All external calls go through one provider interface in the shared client (WBS-2.2), for example `FlightProvider` and `HotelProvider`. Interfaces are justified here because there are multiple implementations.
2. Implementations: `DuffelFlightProvider`, `LiteApiHotelProvider`, `MockFlightProvider`, `MockHotelProvider`.
3. Selection by environment variable, for example `FLIGHT_PROVIDER=duffel|mock` and `HOTEL_PROVIDER=liteapi|mock`. Secrets (`DUFFEL_ACCESS_TOKEN`, `LITEAPI_KEY`) are read from the environment only, never committed.
4. Mock providers return seeded sample data from JSON files in the repo (at least 10 routes and 10 cities, with realistic offer shapes). CI and tests always use the mock providers. The demo can run on mocks if a provider is down or throttled.
5. If a provider fails at runtime (timeout, 429, 5xx), the API returns a clear error response and does not crash. Retry with backoff for 429 only.

## 6. Open items

- [x] Create Duffel test account and token (Berkay)
- [x] LiteAPI sandbox key created (Berkay)
- [x] Duffel rate limit measured (30 per window, window length to confirm)
- [x] Duffel sample response captured (`samples/duffel_offer_request_IST_LHR.json`)
- [x] LiteAPI sample responses captured (`samples/liteapi_*_sample.json`)
- [ ] Team agrees on the provider interface and normalized offer model (WBS-2.2)
- [ ] Update plan and charter wording: Amadeus → Duffel and LiteAPI (Murat / Cumali)

## 7. Conflicts with the glossary (to decide in WBS-2.2)

Glossary v1.0 says only one currency is supported at a time and that dates are stored in UTC.

- **Currency:** Duffel returned all test offers in EUR and we did not choose the currency. LiteAPI returns prices in the currency we request (USD in our test). The team must decide how to show both without conversion, for example by showing each price in its own currency, or by requesting EUR from LiteAPI and displaying flights and hotels separately.
- **Time:** Duffel segment times are local airport times without a UTC offset. Converting to UTC needs the airport time zone. Decide whether to store local time plus airport code or to convert.

## 8. Sources

- PhocusWire, 9 Feb 2026: Amadeus shutting down its self-service APIs portal (registrations paused, decommission 17 July).
- Developer write-ups confirming the 17 July 2026 shutdown and SDK archival.
- Duffel documentation and test-mode usage guides.
- LiteAPI documentation: rate limiting and FAQ pages, OpenAPI spec (`X-API-Key`, `/hotels/rates`).
