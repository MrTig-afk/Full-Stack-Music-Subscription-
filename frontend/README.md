# Frontend — Music Subscription Web App

Static HTML/CSS/JavaScript frontend for the music subscription application.

## Files

- **index.html** — Main page markup with auth, subscription, and query sections.
- **app.js** — Application logic: session management, API calls, rendering.
- **styles.css** — Responsive layout and component styling.
- **config.js** — Frontend configuration (app name, API base URL).

## Configuration

Edit [config.js](config.js) to set the API base URL:

```javascript
window.APP_CONFIG = {
  appName: "Music Subscription",
  apiBaseUrl: "http://127.0.0.1:8000", // Set to your backend URL
};
```

Alternatively, pass the API base URL as a query parameter:

```text
http://localhost:3000/?apiBase=https://api.example.com
```

Or store it in localStorage:

```javascript
localStorage.setItem("music-subscription-api-base", "https://api.example.com");
```

## Local Development

```bash
cd frontend
python -m http.server 5173
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) in your browser.

## Deployment

### Option 1: AWS S3 Static Website

1. Create an S3 bucket:

   ```bash
   aws s3 mb
   s3://music-subscription-frontend-UNIQUE-ID --region us-east-1
   ```

2. Enable static website hosting:

   ```bash
   aws s3 website s3://music-subscription-frontend-UNIQUE-ID \
     --index-document index.html \
     --error-document index.html
   ```

3. Upload frontend files:

   ```bash
   aws s3 sync . s3://music-subscription-frontend-UNIQUE-ID \
     --exclude ".git/*" --exclude "README.md"
   ```

4. Make bucket contents public (via bucket policy):

   ```bash
   aws s3api put-bucket-policy \
     --bucket music-subscription-frontend-UNIQUE-ID \
     --policy '{
       "Version": "2012-10-17",
       "Statement": [{
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::music-subscription-frontend-UNIQUE-ID/*"
       }]
     }'
   ```

5. Get the endpoint:

   ```bash
   aws s3api get-bucket-website \
     --bucket music-subscription-frontend-UNIQUE-ID \
     --region us-east-1
   ```

6. Update [config.js](config.js) to point at your backend, then re-upload:

   ```bash
   aws s3 sync . s3://music-subscription-frontend-UNIQUE-ID \
     --exclude ".git/*" --exclude "README.md"
   ```

### Option 2: CloudFront (CDN) in front of S3

For production, add a CloudFront distribution:

```bash
aws cloudfront create-distribution \
  --origin-domain-name music-subscription-frontend-UNIQUE-ID.s3-website-us-east-1.amazonaws.com \
  --default-root-object index.html
```

### Option 3: Any HTTP(S) Host

Upload the contents of the `frontend/` folder to any static web host (GitHub Pages, Netlify, Vercel, etc.). Update [config.js](config.js) with the backend API URL before deploying.

## API Base URL Examples

- **EC2 direct:** `http://<EC2_PUBLIC_DNS>`
- **EC2 via API Gateway:** `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`
- **ECS via ALB:** `http://<ALB_DNS_NAME>`
- **ECS via API Gateway:** `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`
- **Lambda via API Gateway:** `https://<api-id>.execute-api.us-east-1.amazonaws.com/prod`

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Modern mobile browsers

## Features Implemented

✅ Login with email and password  
✅ Register new account (unique email validation)  
✅ Session storage (browser sessionStorage)  
✅ Query songs by title, artist, album, year (AND matching)  
✅ Subscribe to songs (add to DynamoDB)  
✅ Remove subscriptions  
✅ Logout (clear session and browser state)  
✅ S3 presigned image URLs with fallback  
✅ Responsive design (mobile, tablet, desktop)  
✅ CORS-compatible (can call backend from separate origin)

## Troubleshooting

**"Request failed" on login/register:**

- Check the browser console (F12) for details.
- Verify the API base URL in [config.js](config.js).
- Ensure backend is running and responding to `/health`.
- Check browser Network tab to see the actual request/response.

**Images not loading:**

- Verify S3 bucket and presigned URLs are correct.
- Check browser console for CORS errors.
- Ensure the backend is generating valid presigned URLs.

**Session lost after refresh:**

- Verify sessionStorage is enabled in the browser.
- Check if the browser is in private/incognito mode (sessionStorage may be cleared).
