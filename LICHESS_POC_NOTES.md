# Lichess Upload POC - Implementation Notes

## Current Status

**⚠️ IMPORTANT LIMITATION:** Lichess API does not currently support programmatic study creation.

This is a known limitation - Lichess does not provide an API endpoint for creating studies programmatically. See: https://github.com/lichess-org/api/issues/224

**This POC cannot work until Lichess adds study creation to their API.**

**Last Updated:** After discovering API limitation

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

1. **⚠️ Study Creation Not Supported**: **CRITICAL LIMITATION**
   - Lichess API does NOT support programmatic study creation
   - The endpoint `POST /api/study` does not exist (returns 404)
   - This is a known limitation: https://github.com/lichess-org/api/issues/224
   - **This feature cannot work until Lichess adds study creation to their API**
   - Workaround: Users must manually create studies on lichess.org, then we could potentially add chapters via API (if that endpoint exists)

2. **API Endpoints**: The actual Lichess API endpoints may differ. Need to verify:
   - Study creation: **NOT SUPPORTED BY LICHESS API**
   - Chapter addition endpoint format: Unknown if `POST /api/study/{id}/chapters` exists
   - Response structure: Cannot verify without working endpoints

2. **Token Refresh**: No token refresh mechanism (tokens may expire)
   - User must re-authenticate with `--auth` flag when token expires

3. **Rate Limiting**: No handling for API rate limits
   - May need to add retry logic and rate limit detection

4. **PGN Format**: Basic validation only
   - May need to adjust PGN export format for Lichess compatibility
   - Comments and annotations should be preserved via StringExporter

5. **OAuth Client ID**: Currently hardcoded as "pgn-curator"
   - Needs to be registered with Lichess or made configurable

## Current Status: NOT WORKING

**This POC cannot function because Lichess does not provide API endpoints for study creation.**

The implementation is complete but will fail when attempting to create studies, as the Lichess API does not support this operation.

### Error You'll See:
```
Failed to create study: Lichess API does not support programmatic study creation.
Studies must be created manually on lichess.org.
```

## Potential Workarounds (Not Implemented)

1. **Manual Study Creation + Chapter Addition**
   - User creates study manually on lichess.org
   - We could potentially add chapters via API (need to verify if chapter addition endpoint exists)

2. **Web Scraping / Selenium** (Not recommended, fragile)
   - Could automate the web interface, but violates ToS and is fragile

3. **Wait for Lichess API Update**
   - Monitor: https://github.com/lichess-org/api/issues/224
   - When/if Lichess adds study creation, this POC will work

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

