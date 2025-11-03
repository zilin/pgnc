# Lichess Upload POC - Implementation Notes

## Current Status

This is a proof-of-concept implementation for uploading curated PGN files to Lichess as studies.

**Last Updated:** After initial POC - Enhanced error handling and validation

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

### 1. Register OAuth Application with Lichess

Before using this feature, you need to register an OAuth application with Lichess:

1. Go to https://lichess.org/account/oauth/app/create
2. Create a new application:
   - Name: `pgn-curator` (or your preferred name)
   - Redirect URI: `http://localhost:8080/oauth/callback`
   - Scopes: `study:write`
3. Note your `client_id` (you'll need to update the code)

### 2. Update Client ID

Update the `client_id` in `pgnc/lichess.py`:
- Line ~74: Change `"pgn-curator"` to your registered client ID

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

1. **API Endpoints**: The actual Lichess API endpoints may differ. Need to verify:
   - Study creation endpoint format: Currently using `POST /api/study`
   - Chapter addition endpoint format: Currently using `POST /api/study/{id}/chapters`
   - Response structure: Handles multiple possible response formats

2. **Token Refresh**: No token refresh mechanism (tokens may expire)
   - User must re-authenticate with `--auth` flag when token expires

3. **Rate Limiting**: No handling for API rate limits
   - May need to add retry logic and rate limit detection

4. **PGN Format**: Basic validation only
   - May need to adjust PGN export format for Lichess compatibility
   - Comments and annotations should be preserved via StringExporter

5. **OAuth Client ID**: Currently hardcoded as "pgn-curator"
   - Needs to be registered with Lichess or made configurable

## Testing

To test the POC:

```bash
# Install dependencies
pip install -e .

# Upload a PGN file
pgnc upload my_repertoire.pgn --name "Test Study"
```

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

