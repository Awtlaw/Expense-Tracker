# Deploying Expense Tracker to Render

## Step-by-Step Deployment Guide

### Prerequisites

- GitHub account (free)
- Render account (free at https://render.com)
- Your project pushed to a GitHub repository

---

## Step 1: Push Your Code to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit - Expense Tracker with Flask-SQLAlchemy"

# Add remote origin (replace with your repo URL)
git remote add origin https://github.com/YOUR-USERNAME/expense-tracker.git

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## Step 2: Create a Render Account

1. Go to https://render.com
2. Sign up with GitHub (recommended - easier deployment)
3. Authorize Render to access your GitHub

---

## Step 3: Deploy on Render

### Option A: Using render.yaml (Recommended)

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Select your `expense-tracker` repository
5. Render will auto-detect the `render.yaml` file
6. Click **"Create Web Service"**

### Option B: Manual Configuration

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Fill in the following:
   - **Name**: `expense-tracker`
   - **Environment**: Python 3.11
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn 'app:create_app()'`
   - **Plan**: Free (or paid if needed)

---

## Step 4: Set Environment Variables

1. In Render dashboard, go to your service
2. Click **"Environment"** tab
3. Add the following variables:

```
SECRET_KEY = [Generate a secure key - use python -c "import secrets; print(secrets.token_hex(32))"]
FLASK_ENV = production
DATABASE_URL = sqlite:///database.db
```

**To generate a secure SECRET_KEY:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Step 5: Deploy

1. Render will automatically start building when you create the service
2. Check the **"Logs"** tab to monitor deployment
3. Once you see "✓ Deploy successful", your app is live!
4. Your app will be available at: `https://expense-tracker.onrender.com`

---

## Step 6: Verify Deployment

1. Visit your app URL (shown in Render dashboard)
2. You should see the Expense Tracker landing page
3. Test user registration and login

---

## Important Notes for Production

### Database Persistence Issue

The free SQLite database doesn't persist between Render restarts. For production, upgrade to:

**Option 1: PostgreSQL on Render (Recommended)**

```bash
# Update requirements.txt to add psycopg2
pip install psycopg2-binary
```

Add to `requirements.txt`:

```
psycopg2-binary
```

Then use the PostgreSQL connection string from Render.

**Option 2: Use a managed database service**

- Render PostgreSQL (add from dashboard)
- AWS RDS
- Railway
- Supabase

### Security Checklist

- [ ] Change `SECRET_KEY` to a random value
- [ ] Set `FLASK_ENV = production`
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Enable HTTPS (Render provides free SSL)
- [ ] Set strong password requirements in helpers.py
- [ ] Review CORS settings if using from different domains

---

## Automatic Deployments

Render will automatically redeploy when you:

1. Push to the `main` branch on GitHub
2. Or manually trigger from Render dashboard

To disable auto-deploy:

- Render Dashboard → Service Settings → Auto-Deploy: Off

---

## Troubleshooting

### "Build failed" error

- Check Build Command in logs
- Ensure all packages in requirements.txt are compatible
- Check for Python syntax errors

### "Application crashed"

- View Logs tab for errors
- Check environment variables are set
- Verify `app.py` has `create_app()` function

### Database not persisting

- SQLite doesn't persist on free tier
- Upgrade to PostgreSQL
- Data will be reset on service restart

### Slow startup

- Free tier has resource limits
- Consider upgrading plan for better performance

---

## Cost Estimate

**Free Tier:**

- $0/month
- 0.5 GB RAM
- 0.5 vCPU
- Auto-sleeps after 15 minutes of inactivity
- Data resets on restart

**Paid Tier (Starter):**

- $7/month
- 1 GB RAM
- 0.5 vCPU
- Always running
- Persistent storage (with PostgreSQL)

---

## Environment Variables Reference

| Variable       | Value                                     | Notes                                 |
| -------------- | ----------------------------------------- | ------------------------------------- |
| `SECRET_KEY`   | Random 32-char hex                        | Generate with `secrets.token_hex(32)` |
| `FLASK_ENV`    | `production`                              | Must be "production" for security     |
| `DATABASE_URL` | PostgreSQL URL or `sqlite:///database.db` | Use PostgreSQL for production         |
| `DEBUG`        | `False`                                   | Never set to True in production       |

---

## Next Steps

1. **Monitor the app** in Render dashboard
2. **Set up logging** to track errors
3. **Enable PostgreSQL** for data persistence
4. **Add custom domain** (optional, paid feature)
5. **Enable HTTP/2** in service settings

---

## Support Links

- Render Docs: https://render.com/docs
- Flask Deployment: https://render.com/docs/deploy-flask
- GitHub Integration: https://render.com/docs/github

---

**Your app is now live on Render! 🎉**
