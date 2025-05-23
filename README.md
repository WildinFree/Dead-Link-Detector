# Dead-Link-Detector
Simple tool to check if website links are working. Reads links from a file, checks them quickly, and saves working/broken links. Easy setup with a config file. Free to use and modify!
# Dead Link Detector

Dead Link Detector is a simple tool made with AI to check if a list of website links are working or not. It's built using Python and can handle many links quickly.

## What it does

* **Checks lots of links fast:** It uses a special method to check many links at the same time.
* **Reads links from a file:** You give it a text file with one link on each line.
* **Saves the results:** It tells you which links are working and which are not, and saves these lists in separate files.
* **Easy to set up:** You can change how it works using a simple `config.yaml` file. For example, you can set how long it should wait for a website to respond.
* **Tries different ways to check:** If a link doesn't work at first, it can try other methods to see if it's just a temporary issue.
* **Keeps track of what it's doing:** It shows you what's happening while it's checking the links.

## How to use it

1.  **Make sure you have Python:** This tool needs Python 3.6 or newer.
2.  **Get the files:** Download all the Python files (`main.py`, `verifier.py`, `chunk_reader.py`, `url_cleaner.py`, `logger.py`, `output_writer.py`, `result_folder.py`) and the `config.yaml` file. Also, make sure you have the `requirements.txt` file.
3.  **Install the needed tools:** Open a terminal or command prompt in the folder where you saved the files and run:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Put your links in a file:** Create a text file (like `urls.txt`) and put one website link on each line.
5.  **Tell the tool which file to use:** Open the `config.yaml` file. You'll see a line that says `input_file`. Change what's after the colon (`:`) to the name of your file (e.g., `urls.txt`).
6.  **Run the tool:** In the terminal or command prompt, in the same folder as the files, run:
    ```bash
    python main.py
    ```
7.  **See the results:** The tool will create a folder (probably called `results` or something similar based on your `config.yaml`) with two files inside: `working.txt` (links that work) and `notworking.txt` (links that don't work).

## Setting things up (config.yaml)

You can change how the tool works by editing the `config.yaml` file. Here are some things you can change:

* `timeout`: How many seconds to wait for a website to respond (e.g., `10`).
* `max_retries`: How many times to try checking a link again if it fails (e.g., `3`).
* `concurrency`: How many links to check at the same time (a higher number can be faster, but might use more computer resources).
* `status_codes`: The website codes that mean a link is working (usually `[200, 201, 202, 203, 204, 205, 206, 207, 208, 226]`). You probably don't need to change this.
* `input_file`: The name of the file with your links (e.g., `urls.txt`).
* `output_path`: Where to save the results (e.g., `results/`).
