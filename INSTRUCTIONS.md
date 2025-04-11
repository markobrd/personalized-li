## Step 1 
-Downlaod all dependencies

## Step2 
- Fill out the config file
    - The template should be already in the git repository.
    - The username and password should be the ones of a troughaway acc.
    - Urls and timeout don't matter right now

## Step3 
- Run the scrape_linkedin.py file
    - After that flask server should start automatically
- You can run the flask_server.py file to see the feeds
    - The feeds are automatically sorted from the newest to the oldest

## Other useful info
- You may need to pass a CAPCHA the first time you run the script
- The post data is saved into the JSON_DATA folder
- Right now the script scrapes all the data before gpt processing 