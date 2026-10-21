# Deploying to Hugging Face Spaces

The app runs for free on a Hugging Face Space. Everything happens in the browser, no installation needed.

## 1. Create the Space

1. Create a free account at [huggingface.co/join](https://huggingface.co/join).
2. Open [huggingface.co/new-space](https://huggingface.co/new-space) and fill in:
   - **Space name:** `medication-side-effect-explorer`
   - **License:** MIT
   - **Space SDK:** Gradio, template **Blank**
   - **Hardware:** CPU basic (free)
   - **Visibility:** Public
3. Click **Create Space**.

## 2. Upload the files

1. In the Space, open the **Files** tab, then **Contribute > Upload files**.
2. Drag in these three items from this project:
   - `app.py`
   - `requirements.txt`
   - the whole `med_explorer` folder
3. Click **Commit changes to main**.

The Space builds automatically. After 2 to 3 minutes the **App** tab shows the running app.

If the uploader drops the folder structure, upload the `med_explorer` files again and type `med_explorer/` in front
of each name before committing, so the four files sit inside a `med_explorer` folder in the Space.

## 3. Add an openFDA API key (recommended)

Without a key, all visitors share a limit of 1,000 openFDA requests per day, which is about 100 new drug searches.

1. Get a free key at [open.fda.gov/apis/authentication](https://open.fda.gov/apis/authentication/).
2. In the Space, open **Settings > Variables and secrets > New secret**.
3. Name: `OPENFDA_API_KEY`, value: your key. The Space restarts and uses it.

## 4. Share it

Copy the Space link (`https://huggingface.co/spaces/YOUR_USERNAME/medication-side-effect-explorer`) and add it:

- to the main README, under the title: `**Live demo:** <link>`
- to the GitHub repo's **About** box (gear icon on the repo page, field "Website")

## Updating the app

After changing the code, upload the changed files again in the Files tab. The Space rebuilds on its own.
