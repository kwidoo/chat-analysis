# Tasks to Implement Missing Endpoints

Based on my analysis of the frontend and backend code, I've identified several endpoints that the frontend is trying to use but aren't implemented in the backend. Here are the tasks needed to implement these missing endpoints:

## Task 1: Implement MFA Verification Endpoint

**Endpoint:** `/api/auth/verify-mfa`
**Description:** This endpoint should validate a provided MFA code and issue JWT tokens upon successful verification.
**Requirements:**

- Create a POST route handler in routes.py
- Accept JSON payload with `mfa_token` and `mfa_code` fields
- Validate the MFA code against the stored token
- Return JWT access and refresh tokens upon successful verification
- Return appropriate error responses for invalid codes

## Task 2: Implement Search Suggestions Endpoint

**Endpoint:** `/api/search/suggest`
**Description:** This endpoint should provide search query suggestions based on user input.
**Requirements:**

- Create a POST route handler in routes.py
- Accept JSON payload with `input` field containing the partial search query
- Implement logic to generate relevant suggestions based on the input
- Return a JSON response with an array of suggestion strings

## Task 3: Implement Natural Language Processing Endpoint

**Endpoint:** `/api/search/process-nl`
**Description:** This endpoint should transform natural language queries into structured queries.
**Requirements:**

- Create a POST route handler in routes.py
- Accept JSON payload with a `query` field containing natural language text
- Process the natural language query into a structured format suitable for search
- Return a JSON response with the processed structured query

## Task 4: Fix Upload Endpoint URL Mismatch

**Description:** Currently the frontend uses `/api/upload` but the backend implements `/api/files/upload`
**Options:**

1. Create a route alias in app.py that forwards requests from `/api/upload` to `/api/files/upload`
2. OR modify the frontend to use the correct endpoint `/api/files/upload`
   **Requirements:**

- Ensure file uploads work correctly with proper error handling
- Maintain compatibility with existing frontend code

## Task 5: Complete OAuth Implementation

**Description:** Review and complete the OAuth implementation to ensure it matches what the frontend expects.
**Requirements:**

- Review the existing OAuth implementation in the backend
- Implement or fix the OAuth callback handling to match frontend expectations
- Ensure proper token exchange and user authentication flow

Each of these tasks is critical for enabling the full functionality that the frontend expects from the backend API.
