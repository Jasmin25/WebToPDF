import os
import json
import base64
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from flask import Flask, render_template, request, send_from_directory

app = Flask(__name__)

chrome_bin = os.environ.get('GOOGLE_CHROME_BIN', './dist/chromedriver')
chrome_driver_path = os.environ.get('CHROMEDRIVER_PATH', './dist/chromedriver')

browser = None


@app.route('/', methods=['GET', 'POST'])
def index():
    """Render main page and process form data to generate PDF from URL."""
    if request.method == 'POST':
        url = request.form['url']
        pdf_path = generate_pdf(url)
        return send_from_directory(os.getcwd(), pdf_path, as_attachment=True)
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Render login page and process form data to set login session."""
    global browser

    if request.method == 'POST':
        login_url = request.form['login_url']

        if browser:
            browser.quit()

        browser = get_browser()
        browser.get(login_url)
        return "Logged in successfully!"

    return render_template('login.html')


def get_browser():
    """Initialize and return a browser instance."""
    wd_opts = webdriver.chrome.options.Options()
    wd_opts.add_argument('--headless')
    wd_opts.add_argument('--disable-gpu')
    wd_opts.add_argument("--no-sandbox")
    wd_opts.add_argument("--disable-dev-shm-usage")
    wd_opts.add_argument("--remote-debugging-port=9222")

    chr_svc = webdriver.chrome.service.Service(chrome_driver_path)
    return webdriver.Chrome(service=chr_svc, options=wd_opts, 
                            desired_capabilities=webdriver.DesiredCapabilities.CHROME.copy())


def generate_pdf(url):
    """Generate PDF from the provided URL using browser session."""
    global browser

    if not browser:
        browser = get_browser()

    try:
        browser.get(url)
        WebDriverWait(browser, timeout=30, poll_frequency=2).until(_waitForDocReady)
        
        # Assert the page loaded properly
        assert browser.page_source != '<html><head></head><body></body></html>', f"Url could not be loaded: {url}"
        
        result = send_cmd(browser, "Page.printToPDF")

        # Fetch the title and sanitize it to ensure it's safe for a filename
        safe_title = "".join(x for x in browser.title if x.isalnum() or x in [" ", "-"]).rstrip()
        timestamp = datetime.now().strftime("%y%m%d-%H%M%S")
        out_file = f"{safe_title}_{timestamp}.pdf"
        out_path = os.getcwd()
        out_path_full = f"{out_path}/{out_file}"

        with open(out_path_full, 'wb') as file:
            file.write(base64.b64decode(result['data']))

        if not os.path.isfile(out_path_full):
            raise Exception(f"PDF WAS NOT GENERATED: {out_path_full}")

        return out_file

    except Exception as e:
        print(f"Error encountered: {e}")
        return None


def _waitForDocReady(driver):
    """Wait until the page is completely loaded."""
    rs = driver.execute_script('return document.readyState;')
    return rs == 'complete'


def send_cmd(driver, cmd, params={}):
    """Send command to the browser and get the result."""
    response = driver.command_executor._request(
        'POST',
        f"{driver.command_executor._url}/session/{driver.session_id}/chromium/send_command_and_get_result",
        json.dumps({'cmd': cmd, 'params': params})
    )
    
    if response.get('status'):
        raise Exception(response.get('value'))

    return response.get('value')


@app.route('/download/<filename>')
def download(filename):
    """Serve the requested file as a download."""
    return send_from_directory(os.getcwd(), filename, as_attachment=True)


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
