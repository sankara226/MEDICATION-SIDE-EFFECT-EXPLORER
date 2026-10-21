# Deploying to Hugging Face Spaces

The app runs on a free Hugging Face Space (CPU basic). It takes about five minutes.

1. Create a free account at [huggingface.co](https://huggingface.co/join), then create an access token with
   **write** permission under *Settings → Access Tokens*.
2. From the project root:

   ```bash
   pip install huggingface_hub
   huggingface-cli login            # paste the token
   python deploy/deploy_to_hf.py YOUR_HF_USERNAME/medication-side-effect-explorer
   ```

3. Open the printed link. The first build takes 2–3 minutes.
4. **Recommended:** get a free openFDA key at [open.fda.gov/apis/authentication](https://open.fda.gov/apis/authentication/)
   and add it in the Space under *Settings → Variables and secrets* as a secret named `OPENFDA_API_KEY`.
   Without it, every visitor shares the Space's limit of 1,000 openFDA requests per day, and one analysis
   uses about 10 of them (repeat searches are cached).
5. Put the Space link in the main README (the "Live demo" line) and in your GitHub repo's *About* box.

To redeploy after a change, run step 2 again.

The Space gets its settings (title, SDK, entry file) from the YAML header in [`space_README.md`](space_README.md),
which the script uploads as the Space's `README.md`. That keeps the GitHub README free of it.
