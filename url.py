import streamlit as st
import requests
from bs4 import BeautifulSoup
import time
import json
import re

def parse_apollo_data(soup):
    """
    Parses ApolloSSRDataTransport scripts to extract product data.
    Returns a dict: {code: {'code': str, 'name': str, 'image': str}}
    """
    products_db = {}
    scripts = soup.find_all('script')
    # Filter valid scripts first
    apollo_scripts = [s for s in scripts if s.string and 'ApolloSSRDataTransport' in s.string]
    
    for script in apollo_scripts:
        content = script.string
        try:
            # Find start of push(
            start_idx = content.find('.push(')
            if start_idx == -1: continue
            
            start_json = start_idx + 6
            end_json = content.rfind(')')
            
            json_str = content[start_json:end_json]
            # Fix JS object literal to valid JSON
            json_str = json_str.replace('undefined', 'null')
            
            data = json.loads(json_str)
            
            # Recursive search for products
            def search_for_products(obj):
               if isinstance(obj, dict):
                    if '__typename' in obj and obj['__typename'] == 'Product':
                         code = obj.get('code')
                         name = obj.get('name')
                         img = obj.get('representationImage')
                         
                         if code:
                             products_db[code] = {'code': code, 'name': name, 'image': img}
                             
                    for k, v in obj.items():
                        search_for_products(v)
               elif isinstance(obj, list):
                    for item in obj:
                        search_for_products(item)
                        
            search_for_products(data)
            
        except Exception as e:
            continue
            
    return products_db

def extract_product_urls(url):
    """
    Extracts product URLs and thumbnails from the given Kolon Mall URL.
    Returns a list of dictionaries: {'code': str, 'image': str, 'name': str}.
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
        response.encoding = 'utf-8' # Force generic UTF-8 encoding to fix Mojibake
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Parse Apollo Data (Client Side State)
        apollo_products = parse_apollo_data(soup)
        
        # 2. Parse HTML Data (Server Side Rendered Links)
        html_products = {}
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
                    
                    # Accumulate (using code as key prevents duplicates locally)
                    html_products[code] = {'code': code, 'image': img_url, 'name': product_name}
        
        # 3. Merge Strategies
        # Convert HTML map to list to preserve server-render order if possible, 
        # but inject Apollo data where missing.
        final_list = []
        html_codes = set(html_products.keys())
        apollo_codes = set(apollo_products.keys())
        
        # If Apollo has significantly more items, use Apollo as base but try to respect HTML order?
        # Actually, if Top items are missing from HTML, we should use Apollo source as primary for those.
        
        # Simple Merge: Use Apollo as master source if available, otherwise HTML.
        # Use HTML keys order + Apollo-only keys appended?
        # OR just use Apollo keys if Apollo is successful (since it likely has everything).
        
        if apollo_products:
            # Apollo usually contains everything.
            # But we don't know the sort order in Apollo dict (it's insertion order of recursion).
            # Let's assume recursion order is reasonably page-order.
            return list(apollo_products.values())
        else:
            return list(html_products.values())

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
            if st.button("전체 복사", width="stretch"):
                try:
                    import pyperclip
                    pyperclip.copy(data_str_all)
                    st.toast("결과값 전체 보고사 완료", icon="✅")
                except ImportError:
                    st.error("pyperclip module not installed.")
                except Exception as e:
                    st.error(f"Copy failed: {e}")
                    
        with col3:
            if st.button("선택 복사", width="stretch"):
                # Filter selected products based on session state
                # keys are like "select_{code}"
                selected_codes = []
                for p in products:
                    if st.session_state.get(f"select_{p['code']}", False):
                        selected_codes.append(p['code'])
                
                if selected_codes:
                    data_str_selected = "\n".join(selected_codes)
                    try:
                        import pyperclip
                        pyperclip.copy(data_str_selected)
                        st.toast("결과값 선택 복사 완료", icon="✅")
                    except Exception as e:
                        st.error(f"Copy failed: {e}")
                else:
                    st.warning("선택된 상품이 없습니다.")

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

import streamlit as st

# 프로필 아이콘(Lower right), 햄버거 메뉴, 푸터 숨기기
hide_streamlit_style = """
<style>
    /* 프로필 아이콘 및 우측 하단 요소 숨기기 */
    [data-testid="stStatusWidget"] {visibility: hidden; height: 0%;}
    
    /* 햄버거 메뉴 숨기기 */
    #MainMenu {visibility: hidden; height: 0%;}
    
    /* "Made with Streamlit" 푸터 숨기기 */
    footer {visibility: hidden; height: 0%;}
    
    /* 상단 헤더 숨기기 */
    header {visibility: hidden; height: 0%;}
</style>

st.title("프로필 숨긴 화면")

