# Implementation Plan - Phase 1: Data Pipeline (HWP & Attachments)

## Goal
Enable the **Biz-Retriever** to "read" attachment files (HWP, PDF) from G2B bid announcements.
This is critical for the "Hard Match 0% False Positive" goal, as key constraints (location, exact specifications) are often hidden in attachments.

## User Review Required
> [!IMPORTANT]
> **HWP Parsing Strategy**: We will use `olefile` + `zlib` for lightweight HWP 5.0 text extraction on Raspberry Pi. This avoids heavy external binaries like `hwp5.jar` or `libhwp`.
> **Database Schema Change**: Adding `attachment_content` (Text) to `BidAnnouncement`. This requires a DB migration (or manual column add for MVP/SQLite, but we use Postgres so Alembic/SQL is needed).

## Proposed Changes

### [Dependencies]
#### [MODIFY] [requirements-base.txt](file:///c:/sideproject/requirements-base.txt)
- Add `olefile>=0.46` (for HWP parsing)
- Add `zlib` (standard lib, no action needed)

### [Database]
#### [MODIFY] [app/db/models.py](file:///c:/sideproject/app/db/models.py)
- Add `attachment_content = Column(Text, nullable=True)` to `BidAnnouncement` model.

### [Service Layer]
#### [MODIFY] [app/services/file_service.py](file:///c:/sideproject/app/services/file_service.py)
- Implement `parse_hwp(file)` using `olefile`.
- Reads `BodyText` section, decompresses with `zlib`, and extracts unicode strings.

#### [MODIFY] [app/services/crawler_service.py](file:///c:/sideproject/app/services/crawler_service.py)
- Logic update:
    1. Parse API response.
    2. If `url` exists, trace it to find the download link (G2B usually requires a specific scraping logic or secondary API call to get the file URL).
    3. *Constraint Check*: G2B file download links are often protected or complex.
    4. *MVP Strategy*: For Phase 1 MVP, detection of "Attachment Existence" might be step 1, but we strongly aim for extraction. We will try to fetch using the standard G2B download URL pattern if available.
    5. Download file -> `file_service.get_text_from_file` -> Save to `attachment_content`.

## Verification Plan

### Automated Tests
1. **HWP Parser Test**:
    - Create a small dummy HWP file (or mock the olefile structure).
    - Run `pytest scripts/test_file_parser.py` (New test).
    - Verify text matches expected content.

### Manual Verification
1. **Trigger Crawl**:
    - Run `docker compose exec api python scripts/trigger_crawl.py`.
2. **Check DB**:
    - Connect to Postgres.
    - `SELECT title, attachment_content FROM bid_announcements WHERE attachment_content IS NOT NULL;`
    - Confirm text is readable.
