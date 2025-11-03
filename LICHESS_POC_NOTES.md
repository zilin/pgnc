# Lichess Upload POC - Implementation Notes

## Current Status

**⚠️ FEATURE NOT VIABLE:** Lichess API does not support programmatic study operations.

**Complete Limitations:**
1. Study creation: `POST /api/study` → 404 Not Found
2. Chapter addition: `POST /api/study/{id}/chapters` → 404 Not Found

Lichess does not provide API endpoints for:
- Creating studies programmatically
- Adding chapters to studies programmatically

See: https://github.com/lichess-org/api/issues/224

**This POC cannot function with current Lichess API capabilities.**

**Last Updated:** After confirming both endpoints fail

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

1. **⚠️ Study Operations Not Supported**: **CRITICAL LIMITATION**
   - Lichess API does NOT support ANY programmatic study operations
   - Study creation: `POST /api/study` → 404 Not Found
   - Chapter addition: `POST /api/study/{id}/chapters` → 404 Not Found
   - This is a known limitation: https://github.com/lichess-org/api/issues/224
   - **This feature cannot work at all with current Lichess API**
   - **No workarounds available** - both endpoints are missing

2. **API Endpoints**: Both endpoints confirmed non-existent:
   - Study creation: `POST /api/study` → **404 CONFIRMED**
   - Chapter addition: `POST /api/study/{id}/chapters` → **404 CONFIRMED**
   - Response structure: Cannot determine - endpoints don't exist

2. **Token Refresh**: No token refresh mechanism (tokens may expire)
   - User must re-authenticate with `--auth` flag when token expires

3. **Rate Limiting**: No handling for API rate limits
   - May need to add retry logic and rate limit detection

4. **PGN Format**: Basic validation only
   - May need to adjust PGN export format for Lichess compatibility
   - Comments and annotations should be preserved via StringExporter

5. **OAuth Client ID**: Currently hardcoded as "pgn-curator"
   - Needs to be registered with Lichess or made configurable

## Current Status: COMPLETELY NOT WORKING

**This POC cannot function because Lichess does not provide API endpoints for ANY study operations.**

Both endpoints return 404:
- Study creation: `POST /api/study` → 404
- Chapter addition: `POST /api/study/{id}/chapters` → 404

### Errors You'll See:
```
Failed to create study: Lichess API does not support programmatic study creation.
Failed: Lichess API does not support programmatic chapter addition.
```

## No Workarounds Available

1. ~~Manual Study Creation + Chapter Addition~~ - Chapter addition also fails
2. **Web Scraping / Selenium** - Not recommended (violates ToS, fragile, breaks easily)
3. **Wait for Lichess API Update** - Only viable option
   - Monitor: https://github.com/lichess-org/api/issues/224
   - When/if Lichess adds study/chapter API endpoints, this POC will work

## Conclusion

This feature is **not implementable** with the current Lichess API. The code structure is in place, but both required endpoints are missing from the Lichess API. This POC serves as documentation of what would be needed when/if Lichess adds these capabilities.

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

