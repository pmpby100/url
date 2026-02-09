import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
from st_copy_to_clipboard import st_copy_to_clipboard

def extract_product_urls(url):
    """
    Extracts product URLs and thumbnails from the given Kolon Mall URL.
    Returns a list of dictionaries: {'code': str, 'image': str}.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Suppress only the single warning from urllib3 needed.
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        
        # verify=False added to bypass SSL certificate verification errors
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        products = []
        # Find all anchor tags
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Check if '/Product/' is in the href
            if '/Product/' in href:
                # Split by '/Product/' and take the last part to get the ID/code
                parts = href.split('/Product/')
                if len(parts) > 1:
                    code = parts[1]
                    
                    # Try to find an image tag inside the anchor
                    img_tag = a_tag.find('img')
                    img_url = img_tag.get('src') if img_tag else None
                    product_name = img_tag.get('alt') if img_tag else "Unknown Product"
                    
                    # If no image in anchor, sometimes it's a sibling or structured differently. 
                    # But for now assuming standard structure where <a> wraps the card.
                    
                    products.append({'code': code, 'image': img_url, 'name': product_name})
        
        # Regex Fallback: Scan text for any other Product/CODE patterns
        # This catches products in JSON blobs or non-standard tags
        import re
        # Pattern: /Product/ followed by alphanumeric code
        # We assume codes are at least 5 chars to avoid short noise if any
        regex_codes = re.findall(r'/Product/([A-Z0-9]+)', response.text)
        
        existing_codes = {p['code'] for p in products}
        
        for code in regex_codes:
            if code not in existing_codes:
                products.append({'code': code, 'image': None, 'name': "Detected by Text Scan"})
                existing_codes.add(code)
        
        # Deduplicate while preserving order (based on code)
        seen = set()
        unique_products = []
        for p in products:
            if p['code'] not in seen:
                unique_products.append(p)
                seen.add(p['code'])
                
        return unique_products or []

    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching URL: {e}")
        return []
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return []

def main():
    st.set_page_config(page_title="Kolon Mall Scraper", page_icon="🛍️", layout="centered")

    # Custom CSS for a simple, modern look
    st.markdown("""
        <style>
        .main {
            background-color: #f8f9fa;
        }
        .stButton>button {
            width: 100%;
            background-color: #007bff;
            color: white;
            border-radius: 8px;
            border: none;
            padding: 10px 20px;
        }
        .stButton>button:hover {
            background-color: #0056b3;
        }
        /* Target the Copy button explicitly if possible, or general iframe button */
        /* st-copy-to-clipboard renders inside an iframe, styling it from here is tricky. 
           However, we can try to style the container around it to be full width. */
           
        .result-row {
            background-color: white;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .product-code {
            font-family: monospace;
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }
        .product-name {
            font-size: 0.9em;
            color: #666;
            margin-top: 4px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🛍️ Product URL Extractor")
    st.markdown("Enter a **Kolon Mall** URL below to extract product links.")

    # Initialize session state for storing results
    if 'products' not in st.session_state:
        st.session_state.products = []
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 1
        
    if 'last_url' not in st.session_state:
        st.session_state.last_url = ""
        
    with st.form("search_form"):
        url_input = st.text_input("Kolon Mall URL", placeholder="https://www.kolonmall.com/...")
        submitted = st.form_submit_button("Extract URLs")

    if submitted:
        if not url_input.strip():
            st.warning("Please enter a valid URL.")
        elif "https://www.kolonmall.com/" not in url_input:
            st.warning("Please enter a valid URL containing 'https://www.kolonmall.com/'.")
        else:
            with st.spinner("Scanning page for products..."):
                # Simulate a slight delay for better UX if it's too fast
                time.sleep(0.5)
                # Store URL and reset page
                st.session_state.last_url = url_input
                st.session_state.current_page = 1
                
                products = extract_product_urls(url_input)
                st.session_state.products = products

            if not products:
                st.info("No products found. The page might use dynamic loading (Javascript) which this simple scraper cannot access, or there are no matched items.")

    # Always display results if they exist in session state
    if st.session_state.products:
        products = st.session_state.products
        st.success(f"Found {len(products)} product(s)!")
        
        # Display results
        st.markdown("### Extracted Product Paths")
        
        # Prepare text data for copy/download
        codes_only = [p['code'] for p in products]
        data_str_all = "\n".join(codes_only)
        
        # Action Buttons Row
        # Layout: [Download] [Total Copy] [Selected Copy]
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.download_button(
                label="Download List",
                data=data_str_all,
                file_name="product_urls.txt",
                mime="text/plain",
                width="stretch"
            )
            
        with col2:
            st_copy_to_clipboard(data_str_all, "전체 복사", "복사 완료! ✅")

        with col3:
            # Calculate selected codes first
            selected_codes = []
            for p in products:
                if st.session_state.get(f"select_{p['code']}", False):
                    selected_codes.append(p['code'])

            if selected_codes:
                data_str_selected = "\n".join(selected_codes)
                st_copy_to_clipboard(data_str_selected, "선택 복사", "복사 완료! ✅")
            else:
                st.button("선택 복사", disabled=True, key="copy_sel_disabled", help="선택된 상품이 없습니다.")

        st.markdown("---")

        # Pagination & Selection Bar
        # Layout: [ < ] [ 1 ] [ 2 ] ... [ 10 ] [ > ]
        # Checkbox below.
        
        # Custom CSS for Pagination
        # We target the buttons inside the pagination container.
        # To strictly scope, we can't easily without a parent container class in Streamlit, 
        # but we can try to rely on the fact that these are the only buttons in this specific arrangement 
        # or just style all secondary buttons in a certain way if acceptable, 
        # OR use specific keys if Streamlit supported ID selectors (it doesn't easily).
        # We will use a broad selector but try to be specific to 'primary' vs 'secondary' if we swap types.
        
        # Strategy:
        # Make Active Button -> kind="primary" -> Green Circle
        # Make Inactive/Arrows -> kind="secondary" -> Blue Rounded Square
        
        # Pagination & Selection Bar
        # Layout: [Select All (Left)] ... [ < ] [ > ] (Right)
        
        # Pagination Logic
        def set_page_rel(direction):
            new_page = st.session_state.current_page
            if direction == 'prev' and new_page > 1:
                new_page -= 1
            elif direction == 'next':
                new_page += 1
            
            if new_page != st.session_state.current_page:
                st.session_state.current_page = new_page
                # Re-fetch
                base_url = st.session_state.last_url
                import re
                clean_url = re.sub(r'[&?]page=\d+', '', base_url)
                sep = "&" if "?" in clean_url else "?"
                target_url = f"{clean_url}{sep}page={st.session_state.current_page}"
                
                st.toast(f"Loading page {st.session_state.current_page}...", icon="⏳")
                st.session_state.products = extract_product_urls(target_url)

        # Select All Logic
        def toggle_select_all():
             for p in st.session_state.products:
                 st.session_state[f"select_{p['code']}"] = st.session_state.select_all

        # Columns: [Select All (2)] [Spacer (8)] [Prev (1)] [Next (1)]
        col_select, col_space, col_prev, col_next = st.columns([2, 8, 1, 1])
        
        with col_select:
             st.checkbox("전체 선택", key="select_all", on_change=toggle_select_all)
             
        with col_prev:
            st.button("<", key="prev_page", disabled=st.session_state.current_page <= 1, on_click=set_page_rel, args=('prev',), width="stretch")
            
        with col_next:
            st.button(">", key="next_page", on_click=set_page_rel, args=('next',), width="stretch")
            
        st.markdown("---")

        # Display results list with thumbnails and checkboxes
        if st.session_state.products:
            for p in products:
                # Layout: [Checkbox] [Text] [Image]
                # Use columns to align
                c_check, c_text, c_img = st.columns([0.5, 3, 1])
                
                with c_check:
                    # Unique key for each checkbox
                    # Initialize matching Select All if it wasn't set locally yet
                    if f"select_{p['code']}" not in st.session_state:
                         st.session_state[f"select_{p['code']}"] = False
                         
                    st.checkbox("", key=f"select_{p['code']}")
                
                with c_text:
                    st.markdown(f"""
                        <div class='result-row' style='display:block;'>
                            <div class='product-code'>{p['code']}</div>
                            <div class='product-name'>{p.get('name', '')}</div>
                        </div>
                    """, unsafe_allow_html=True)
                
                with c_img:
                    if p['image']:
                        # Make image clickable
                        product_url = f"https://www.kolonmall.com/Product/{p['code']}"
                        # Use HTML to wrap image in anchor
                        st.markdown(
                            f"""
                            <a href="{product_url}" target="_blank">
                                <img src="{p['image']}" style="width: 100%; border-radius: 8px; transition: transform 0.2s;">
                            </a>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:
                        st.write("No Image")
        else:
             st.info("No products on this page.")

if __name__ == "__main__":
    main()
