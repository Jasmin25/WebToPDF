from flask import Flask, request, send_from_directory, render_template
import os
import pdfkit
from bs4 import BeautifulSoup
import requests

app = Flask(__name__)

# Read the whitelist domains from whitelist.txt into a set
with open('whitelist.txt', 'r') as f:
    DOMAIN_WHITELIST = {line.strip() for line in f}

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        domain = url.split('://')[-1].split('/')[0]

        if domain not in DOMAIN_WHITELIST:
            return "This app does not support downloading PDFs from this domain."

        pdf_path = get_pdf_from_url(url)

        if not pdf_path:
            return "Error generating PDF."

        return send_from_directory(directory=os.path.dirname(pdf_path), path=os.path.basename(pdf_path))

    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        login_url = request.form['login_url']
        driver.get(login_url)  # The global driver will use this login link to login
        return "Logged in successfully!"

    return render_template('login.html')

def get_pdf_from_url(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else "untitled"
        
        # Clean the title for characters that might cause issues in filenames
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            title = title.replace(char, '_')

        config = pdfkit.configuration(wkhtmltopdf=os.environ.get('WKHTMLTOPDF_BINARY', 'wkhtmltopdf'))
        pdf_path = os.path.join(os.getcwd(), f"{title}.pdf")
        pdfkit.from_url(url, pdf_path, configuration=config, options={'no-check-certificate': ''})

        if os.path.exists(pdf_path):
            return pdf_path
    except Exception as e:
        print(f"Error: {e}")

    return None


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
