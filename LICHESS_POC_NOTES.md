# Lichess Upload POC - Implementation Notes

## Current Status

This is a proof-of-concept implementation for uploading curated PGN files to Lichess as studies.

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

## Known Limitations (POC)

1. **API Endpoints**: The actual Lichess API endpoints may differ. Need to verify:
   - Study creation endpoint format
   - Chapter addition endpoint format
   - Response structure

2. **Error Handling**: Limited error handling for API failures

3. **Token Refresh**: No token refresh mechanism (tokens may expire)

4. **Rate Limiting**: No handling for API rate limits

5. **PGN Format**: May need to adjust PGN export format for Lichess compatibility

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

