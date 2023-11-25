import base64
import json
import os
from datetime import datetime
from urllib.parse import urlparse

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_apscheduler import APScheduler
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait

# Instantiate a Flask application and APScheduler for job scheduling
app = Flask(__name__)
scheduler = APScheduler()
scheduler.init_app(app)

# Set a secret key for the Flask session and define a preset password for application login
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersecretkey")
PASSWORD = os.environ.get("PASSWORD", "yourpassword")


@app.route('/login', methods=['GET', 'POST'])
def login():
  """
    Handle logging into the application.

    GET: Renders the login page.
    POST: Validates the provided password against the environment's PASSWORD, and logs the user in if correct.

    Returns:
      On GET: Rendered login page.
      On POST: Redirect to the index page if the password is correct, otherwise an error message and 401 status.
    """
  if request.method == 'POST':
    password = request.form['password']
    if password == PASSWORD:
      session['logged_in'] = True
      return redirect(url_for('index'))
    return "Wrong password!", 401
  return render_template('login.html')


def check_login():
  """
    Check if a user is logged in and redirect to login page if not.

    Returns:
      Redirect to the login page if the user is not logged in; otherwise, no value is returned.
    """
  if 'logged_in' not in session:
    return redirect(url_for('login'))


# Configuration for the Chrome driver paths
chrome_bin = os.environ.get('GOOGLE_CHROME_BIN', './dist/chromedriver')
chrome_driver_path = os.environ.get('CHROMEDRIVER_PATH', './dist/chromedriver')

# Initialize global variable for the web browser instance
browser = None


@app.route('/logout')
def logout():
  """
    Log out the user by clearing their session and redirecting to the login page.

    Returns:
      Redirect to the login page after logging out.
    """
  session.pop('logged_in', None)
  return redirect(url_for('login'))


@app.route('/', methods=['GET', 'POST'])
def index():
  """
    Handle the main page of the application.

    GET: Renders the main application page where users can generate a PDF from a URL.
    POST: Processes the provided URL and returns the generated PDF file as a download.

    Returns:
      On GET: Rendered main page.
      On POST: The generated PDF file for download.
    """
  response = check_login()
  if response: return response

  if request.method == 'POST':
    url = request.form['url']
    pdf_path = generate_pdf(url)
    return send_from_directory(os.getcwd(), pdf_path, as_attachment=True)
  return render_template('index.html')


@app.route('/site-login', methods=['GET', 'POST'])
def site_login():
  """
    Handle login to external sites for PDF generation and maintain session.

    GET: Render the site login page.
    POST: Process the provided login URL, use a browser session to log into the site, and record the domain.

    Returns:
      On GET: Rendered site login page.
      On POST: A success message upon logging into the site.
    """
  global browser

  response = check_login()
  if response: return response

  if request.method == 'POST':
    login_url = request.form['login_url']

    if not browser:
      browser = get_browser()

    browser.get(login_url)

    # Add domain to a file after successful login
    domain = extract_domain(login_url)
    write_domain_to_file(domain)

    return "Logged in successfully!"

  return render_template('site_login.html')


def get_browser():
  """
    Initialize a headless Chrome browser instance for the application.

    Returns:
      The initialized WebDriver instance for a Chrome browser.
    """
  # Set Chrome driver options for a headless web browser operation, suitable for server environments
  wd_opts = webdriver.chrome.options.Options()
  wd_opts.add_argument('--headless')
  wd_opts.add_argument('--disable-gpu')
  wd_opts.add_argument("--no-sandbox")
  wd_opts.add_argument("--disable-dev-shm-usage")
  wd_opts.add_argument("--remote-debugging-port=9222")

  # Create a Chrome Service with the specified path
  chr_svc = webdriver.chrome.service.Service(chrome_driver_path)
  return webdriver.Chrome(
      service=chr_svc,
      options=wd_opts,
      desired_capabilities=webdriver.DesiredCapabilities.CHROME.copy())


def generate_pdf(url):
  """
  Generate a PDF from the provided URL using the headless browser session.

  Args:
      url (str): The URL of the webpage to be converted to a PDF.

  Returns:
      str: File name of the generated PDF, or None if an error occurs.
  """
  global browser

  if not browser:
    browser = get_browser()

  try:
    browser.get(url)
    WebDriverWait(browser, timeout=30,
                  poll_frequency=2).until(_waitForDocReady)

    # Assert that the page loaded correctly
    assert browser.page_source != '<html><head></head><body></body></html>', f"Url could not be loaded: {url}"

    result = send_cmd(browser, "Page.printToPDF")

    # Sanitize the page title to create a safe file name
    safe_title = "".join(x for x in browser.title
                         if x.isalnum() or x in [" ", "-"]).rstrip()
    timestamp = datetime.now().strftime("%y%m%d-%H%M%S")
    out_file = f"{safe_title}_{timestamp}.pdf"
    out_path = os.getcwd()
    out_path_full = f"{out_path}/{out_file}"

    # Write the PDF to a file
    with open(out_path_full, 'wb') as file:
      file.write(base64.b64decode(result['data']))

    if not os.path.isfile(out_path_full):
      raise Exception(f"PDF WAS NOT GENERATED: {out_path_full}")

    return out_file

  except Exception as e:
    print(f"Error encountered: {e}")
    return None


def _waitForDocReady(driver):
  """
  Private function to wait for the document to be fully loaded in the browser.

  Args:
      driver (selenium.webdriver.Chrome): The browser driver instance.

  Returns:
      bool: True if the document state is 'complete', False otherwise.
  """
  rs = driver.execute_script('return document.readyState;')
  return rs == 'complete'


def send_cmd(driver, cmd, params={}):
  """
  Send a command to the browser instance and retrieve the result.

  Args:
      driver (selenium.webdriver.Chrome): The browser driver instance.
      cmd (str): The command to send.
      params (dict, optional): Parameters for the command, if required.

  Returns:
      dict: The result of the command from the browser.

  Raises:
      Exception: If the command's response indicates a status error.
  """
  response = driver.command_executor._request(
      'POST',
      f"{driver.command_executor._url}/session/{driver.session_id}/chromium/send_command_and_get_result",
      json.dumps({
          'cmd': cmd,
          'params': params
      }))

  if response.get('status'):
    raise Exception(response.get('value'))

  return response.get('value')


def extract_domain(login_url):
  """
  Extract the domain from a given URL and return it.

  Args:
      login_url (str): URL from which to extract the domain.

  Returns: 
      str: The domain extracted from the login_url.
  """
  parsed_url = urlparse(login_url)
  return parsed_url.netloc


def write_domain_to_file(domain):
  """
  Write the domain to the 'sites.txt' file if it does not exist already.

  Args:
      domain (str): The domain to write to the file.
  """
  with open("sites.txt", "a+") as file:
    file.seek(0)
    if domain not in file.read().splitlines():
      file.write(domain + "\n")


def keep_session_alive_for_domain(domain):
  """
  Visit a domain to keep the session alive.

  Args:
      domain (str): The domain to visit to keep the session alive.
  """
  global browser
  if not browser:
    browser = get_browser()
  try:
    keep_alive_url = f"https://{domain}"
    browser.get(keep_alive_url)
  except Exception as e:
    print(f"Error keeping session alive for {domain}: {e}")


def trigger_keep_alive_for_sites():
  """
  Trigger site visits to keep sessions alive for all domains listed in 'sites.txt'.
  """
  try:
    with open("sites.txt", "r") as file:
      for domain in file:
        keep_session_alive_for_domain(domain.strip())
  except FileNotFoundError:
    print("The sites.txt file does not exist. No action taken.")
  except Exception as e:
    print(f"An error occurred while trying to read sites.txt: {e}")


# Setup the job in the scheduler to keep the sessions alive
scheduler.add_job(id='SessionKeepAlive',
                  func=trigger_keep_alive_for_sites,
                  trigger='interval',
                  hours=3)

# Start the scheduler if the app is not in debug mode or when running in the Werkzeug reloader process
if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
  scheduler.start()


@app.route('/download/<filename>')
def download(filename):
  """
  Serve a file as a download when requested with its filename.

  Args:
      filename (str): The name of the file being requested for download.

  Returns:
      Response: The requested file as an HTTP attachment, triggering download.
  """
  return send_from_directory(os.getcwd(), filename, as_attachment=True)


if __name__ == '__main__':
  # Run the web server on the specified port, defaulting to port 5000
  port = int(os.environ.get("PORT", 5000))
  app.run(host='0.0.0.0', port=port)
