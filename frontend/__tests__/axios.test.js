import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';

// Sample response data
const userData = { id: '123', name: 'Test User', email: 'test@example.com' };

describe('Axios Interceptors', () => {
    let mock;
    let originalFetch;

    beforeEach(() => {
        // Store original fetch
        originalFetch = global.fetch;

        // Clear localStorage before each test
        localStorage.clear();

        // Create fresh axios mock
        mock = new MockAdapter(axios);

        // Mock fetch for testing interceptors
        global.fetch = jest.fn();
    });

    afterEach(() => {
        // Restore original fetch
        global.fetch = originalFetch;

        // Reset axios mock
        mock.reset();
    });

    test('should add Authorization header when access token exists', async () => {
        // Set up localStorage with a token
        localStorage.setItem('accessToken', 'test-access-token');

        // Mock API response
        mock.onGet('/api/user/profile').reply(200, userData);

        // Make the request
        const response = await axios.get('/api/user/profile');

        // Verify the request included the auth header
        expect(mock.history.get[0].headers.Authorization).toBe('Bearer test-access-token');

        // Verify the response data
        expect(response.data).toEqual(userData);
    });

    test('should not add Authorization header when no token exists', async () => {
        // Mock API response
        mock.onGet('/api/public-endpoint').reply(200, { message: 'public data' });

        // Make the request
        await axios.get('/api/public-endpoint');

        // Verify no Authorization header was added
        expect(mock.history.get[0].headers.Authorization).toBeUndefined();
    });

    test('should refresh token when receiving 401 error with valid refresh token', async () => {
        // Setup initial tokens
        localStorage.setItem('accessToken', 'expired-token');
        localStorage.setItem('refreshToken', 'valid-refresh-token');

        // Mock first request to return 401
        mock.onGet('/api/user/profile').replyOnce(401)
            // Second request (with new token) should succeed
            .onGet('/api/user/profile').reply(200, userData);

        // Mock token refresh response
        mock.onPost('/api/auth/refresh').reply(200, {
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token'
        });

        // Make the request that will be intercepted
        const response = await axios.get('/api/user/profile');

        // Check that the refresh endpoint was called
        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe('/api/auth/refresh');

        // Check that the original endpoint was called twice
        // (once with expired token, once with new token)
        expect(mock.history.get.length).toBe(2);

        // Verify the new tokens were saved to localStorage
        expect(localStorage.getItem('accessToken')).toBe('new-access-token');
        expect(localStorage.getItem('refreshToken')).toBe('new-refresh-token');

        // Verify we got the data from the retry
        expect(response.data).toEqual(userData);
    });

    test('should logout user when refresh token is invalid', async () => {
        // Setup localStorage
        localStorage.setItem('accessToken', 'expired-token');
        localStorage.setItem('refreshToken', 'invalid-refresh-token');

        // Setup mocks
        mock.onGet('/api/user/profile').reply(401);
        mock.onPost('/api/auth/refresh').reply(401, { error: 'Invalid refresh token' });

        // Mock redirect
        const mockNavigate = jest.fn();
        // This would typically be handled by react-router's useNavigate hook
        // For test purposes, we're mocking the behavior
        window.location.href = jest.fn();

        // Make request that should fail
        try {
            await axios.get('/api/user/profile');
        } catch (error) {
            // Expected to fail
        }

        // Verify refresh was attempted
        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe('/api/auth/refresh');

        // Verify tokens were removed from localStorage
        expect(localStorage.getItem('accessToken')).toBeNull();
        expect(localStorage.getItem('refreshToken')).toBeNull();
    });

    test('should not retry non-401 errors', async () => {
        // Setup localStorage
        localStorage.setItem('accessToken', 'test-access-token');

        // Mock 404 response
        mock.onGet('/api/not-found').reply(404, { error: 'Not found' });

        // Make request
        try {
            await axios.get('/api/not-found');
            fail('Should have thrown an error');
        } catch (error) {
            expect(error.response.status).toBe(404);
        }

        // Verify refresh was not attempted
        expect(mock.history.post.length).toBe(0);

        // Verify the original request was only made once
        expect(mock.history.get.length).toBe(1);
    });

    test('should handle concurrent requests with 401 efficiently', async () => {
        // Setup localStorage
        localStorage.setItem('accessToken', 'expired-token');
        localStorage.setItem('refreshToken', 'valid-refresh-token');

        // Mock endpoints
        // All first requests will fail with 401
        mock.onGet('/api/user/profile').replyOnce(401);
        mock.onGet('/api/user/settings').replyOnce(401);
        mock.onGet('/api/user/notifications').replyOnce(401);

        // After token refresh, subsequent requests should succeed
        mock.onGet('/api/user/profile').replyOnce(200, { id: '123', name: 'User' });
        mock.onGet('/api/user/settings').replyOnce(200, { theme: 'dark' });
        mock.onGet('/api/user/notifications').replyOnce(200, { count: 5 });

        // Token refresh endpoint
        mock.onPost('/api/auth/refresh').reply(200, {
            access_token: 'new-access-token',
            refresh_token: 'new-refresh-token'
        });

        // Make multiple concurrent requests
        const requests = [
            axios.get('/api/user/profile'),
            axios.get('/api/user/settings'),
            axios.get('/api/user/notifications')
        ];

        // Wait for all requests to complete
        const responses = await Promise.all(requests);

        // Verify refresh token was only called once
        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe('/api/auth/refresh');

        // Verify all requests eventually succeeded
        expect(responses[0].data).toEqual({ id: '123', name: 'User' });
        expect(responses[1].data).toEqual({ theme: 'dark' });
        expect(responses[2].data).toEqual({ count: 5 });

        // Verify tokens were updated in localStorage
        expect(localStorage.getItem('accessToken')).toBe('new-access-token');
        expect(localStorage.getItem('refreshToken')).toBe('new-refresh-token');
    });
});
