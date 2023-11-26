# Webpage PDF Generator :page_with_curl:

Webpage PDF Generator is a Flask web application that converts any Webpage URLs into PDF files. It can also handle user authentication for protected pages that require login before content can be accessed.

## Features :sparkles:

- Rudimentary user login system to protect the app access.
- URL to PDF generation with a headless Chrome browser.
- Session management for login into websites whose content is to be converted to PDF.
- A scheduler to keep login sessions alive.

## Deployment :rocket:

This app is designed for Heroku as the preferred deployment platform because Heroku supports the chromedriver required for the PDF generation feature by default.

To deploy this project on Heroku, follow these steps:

1. Create an app on Heroku.
2. Fork this GitHub repository.
3. In the Heroku dashboard for your app, connect your Heroku app with your forked GitHub repository.
4. Under the "Settings" tab in your Heroku app dashboard, add the following Buildpacks in the given order:
    - `heroku/python`
    - `https://github.com/heroku/heroku-buildpack-google-chrome`
    - `https://github.com/heroku/heroku-buildpack-chromedriver`
5. Set the following config vars in the "Settings" tab under "Config Vars":
    - `CHROMEDRIVER_PATH`: Set this variable to `/app/.chromedriver/bin/chromedriver`.
    - `FLASK_SECRET_KEY`: This is a secret key used for session management in Flask. It should be a random secret string.
    - `GOOGLE_CHROME_BIN`: Set this variable to `/app/.apt/usr/bin/google-chrome`.
    - `PASSWORD`: This password will be used for the login system of the web app.

## Usage :computer:

After successful deployment:

1. Access the web application's URL provided by Heroku.
2. Log in using the password you set in `PASSWORD` config var.
3. Use the app interface to generate PDFs from URLs.
4. For URLs requiring user authentication through a specific sign-in link, use the /site-login page to log into the website (by pasting sign-in link) before proceeding with PDF generation.

## Contributions :handshake:

Feel free to fork the project, submit pull requests or issues if you have suggestions or improvements.

## License :page_facing_up:

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
