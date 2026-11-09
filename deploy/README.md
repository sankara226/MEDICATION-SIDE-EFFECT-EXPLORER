# Deploying to Render

The live demo runs on a free [Render](https://render.com) web service, deployed straight from this GitHub repo.

## 1. Create the service

1. Sign up at [render.com](https://render.com) with your GitHub account.
2. Click **+ New > Web Service** and connect this repository.
3. Fill in:

| Field | Value |
|---|---|
| Language | Python 3 |
| Branch | `main` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `python app.py` |
| Instance Type | Free |

## 2. Add the environment variables

| Key | Value | Why |
|---|---|---|
| `OPENFDA_API_KEY` | your key | openFDA rejects keyless requests from shared cloud servers (403) |
| `GRADIO_SERVER_NAME` | `0.0.0.0` | makes the app reachable from outside the server |
| `GRADIO_SERVER_PORT` | `10000` | the port Render routes traffic to |
| `PYTHON_VERSION` | `3.11.9` | pins a stable Python version |

Get a free openFDA key at [open.fda.gov/apis/authentication](https://open.fda.gov/apis/authentication/).

## 3. Deploy

Click **Deploy Web Service**. After 3 to 5 minutes the logs show "Your service is live" and the URL
(`https://<name>.onrender.com`) appears at the top of the page.

## Good to know

- **Sleep:** free services sleep after 15 minutes without visitors. The next visit wakes them up in 30 to 60 seconds.
- **Updates:** every push to `main` redeploys the app automatically.
- **Errors:** open the **Logs** tab of the service to see what went wrong.
