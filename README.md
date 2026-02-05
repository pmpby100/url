# Kolon Mall Product URL Extractor

A Streamlit application that extracts product URLs and details (codes, image URLs, names) from Kolon Mall pages, including "Trend Items" loaded via client-side state.

## Features
- Extracts product codes from Search results and curated pages (e.g., `View/SELECTED`).
- Handles both Server-Side Rendered (HTML) links and Client-Side Hydrated (Apollo State) products.
- Displays Product Code, Name, and Thumbnail.
- Copy/Download functionality.

## How to Run Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app:
   ```bash
   streamlit run url.py
   ```

## How to Deploy to Streamlit Cloud (Web)
Since this project is ready for deployment:

1. **Upload to GitHub**:
   - Create a new repository on [GitHub](https://github.com/new).
   - Upload the following files to the repository:
     - `url.py`
     - `requirements.txt`
     - `README.md`
     - `.gitignore`

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io/).
   - Log in with GitHub.
   - Click "New app".
   - Select the repository you just created.
   - Set "Main file path" to `url.py`.
   - Click "Deploy".

Your app will be live on the web shortly!
