/**
 * Application Configuration Object
 *
 * Global configuration for the Music Subscription web frontend.
 * Accessed by app.js to set application name and backend API URL.
 *
 * @property {string} appName - Display name for the application (shown in header).
 *                             Change to customize branding.
 * @property {string} apiBaseUrl - Default backend API base URL.
 *                                Override via query parameter (?apiBase=...) or
 *                                localStorage (music-subscription-api-base) for flexibility
 *                                across different deployment targets.
 *
 * @example
 * // Local development
 * apiBaseUrl: "http://127.0.0.1:8000"
 *
 * @example
 * // AWS Lambda
 * apiBaseUrl: "https://api-id.execute-api.us-east-1.amazonaws.com/prod"
 *
 * @example
 * // ECS Fargate ALB
 * apiBaseUrl: "http://alb-dns.us-east-1.elb.amazonaws.com"
 */
window.APP_CONFIG = {
  appName: "Music Subscription",
  apiBaseUrl: "http://127.0.0.1:8000",
};
