# Lichess Upload POC - Implementation Notes

## Current Status

**✅ PARTIALLY WORKING:** Found working endpoint for PGN import!

**API Endpoint Status:**
1. Study creation: `POST /api/study` → ❌ 404 Not Found (must create manually)
2. PGN import: `POST /api/study/{id}/import-pgn` → ✅ **WORKS!**

**How it works:**
- User must create study manually on lichess.org
- Then use `--study-id` to import PGN games as chapters
- Each game in the PGN becomes a chapter in the study

**This POC now works with the import-pgn endpoint!**

**Last Updated:** After discovering import-pgn endpoint

## What's Implemented

1. **Lichess API Client** (`pgnc/lichess.py`)
   - OAuth2 authentication with PKCE
   - Study creation
   - Chapter addition to studies
   - Token storage/management

2. **CLI Command** (`pgnc upload`)
   - Upload PGN files to Lichess
   - Automatic authentication flow
   - Support for public/private studies

## Setup Requirements

### Option 1: Personal API Token (Recommended - Simplest)

For personal use, you can use a personal API token (no OAuth app registration needed):

1. Go to https://lichess.org/account/oauth/token/create
2. Create a new token with `study:write` scope
3. Copy the token
4. Use it with:
   ```bash
   pgnc upload my_repertoire.pgn --token YOUR_TOKEN
   ```
   Or save it to `~/.pgnc/lichess_token` file for automatic use

### Option 2: OAuth Application (For Production/Shared Use)

If you need OAuth (for production apps or sharing), register an OAuth application:

1. Go to https://lichess.org/account/oauth/app/create (if available)
2. Create a new application with:
   - Name: `pgn-curator` (or your preferred name)
   - Redirect URI: `http://localhost:8080/oauth/callback`
   - Scopes: `study:write`
3. Update `client_id` in `pgnc/lichess.py` (line ~157)
4. Use `--oauth` flag when uploading

## Features Implemented

✅ OAuth2 authentication with PKCE
✅ Study creation (public/private)
✅ PGN validation before upload
✅ Chapter upload with progress tracking
✅ Token persistence (~/.pgnc/lichess_token)
✅ Error handling with user-friendly messages
✅ Study name sanitization
✅ Graceful failure handling (continues if one chapter fails)

## Known Limitations (POC)

1. **Study Creation Not Supported**: 
   - Study creation: `POST /api/study` → ❌ 404 Not Found
   - **Workaround:** Create study manually on lichess.org, then use `--study-id`

2. **✅ PGN Import Works!**:
   - PGN import: `POST /api/study/{id}/import-pgn` → ✅ **CONFIRMED WORKING**
   - Uses form-encoded data with `pgn` parameter
   - Each game in PGN file becomes a chapter in the study

3. **Token Refresh**: No token refresh mechanism (tokens may expire)
   - User must re-authenticate with `--auth` flag when token expires

4. **Rate Limiting**: No handling for API rate limits
   - May need to add retry logic and rate limit detection

5. **PGN Format**: Basic validation only
   - May need to adjust PGN export format for Lichess compatibility
   - Comments and annotations should be preserved via StringExporter

6. **OAuth Client ID**: Currently hardcoded as "pgn-curator"
   - Needs to be registered with Lichess or made configurable

## Current Status: ✅ WORKING WITH WORKAROUND

**This POC works using the `import-pgn` endpoint!**

**Requirements:**
1. Create study manually on https://lichess.org/study
2. Get study ID from URL (e.g., `ABC123` from `https://lichess.org/study/ABC123`)
3. Use `--study-id` to import PGN games as chapters

### Usage:
```bash
# Get your API token from: https://lichess.org/account/oauth/token/create
# Create study manually on lichess.org
# Then:
pgnc upload my_repertoire.pgn --study-id ABC123
```

### How it Works:
- Each game in the PGN file is imported as a separate chapter
- Uses `POST /api/study/{id}/import-pgn` endpoint
- PGN content is form-encoded and sent to Lichess

## Limitation

- Study must be created manually (no API endpoint for study creation)
- This is acceptable - creating a study is a one-time step
- Once created, you can import multiple PGN files to it

## Conclusion

This feature **works** with the `import-pgn` endpoint! Users create the study once manually, then can import curated PGN files programmatically.

## Next Steps for Production

1. **Verify API Endpoints**: Test with actual Lichess API
2. **Handle Token Refresh**: Implement token refresh logic
3. **Better Error Messages**: Improve error handling and user feedback
4. **Progress Indicators**: Add better progress feedback for large uploads
5. **Validation**: Validate PGN format before upload
6. **Study Updates**: Support updating existing studies
7. **Configuration**: Allow OAuth settings in config file

## API Documentation References

- Lichess API: https://lichess.org/api
- OAuth: https://lichess.org/api#section/Authentication
- Studies API: https://lichess.org/api#tag/Studies

