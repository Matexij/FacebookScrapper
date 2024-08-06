import json
import requests
from datetime import datetime, timedelta
import os
import random
import signal
import time
import sys
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from apscheduler.schedulers.background  import BackgroundScheduler

PAUSE_TIME = 60*2
CHECKING_TIME = 60*20#every 15minut
NIGHT_INTERVAL = 6*3600  # 6 hours in seconds
HOW_MANY_SCROLLS = 3 #how many scrolls on facebook to read posts
INTERNET_CHECK_INTERVAL = 60*10  # 5 minutes in seconds

load_dotenv()  # Load environment variables from .env file

username = os.getenv('SCRAPER_USERNAME')
password = os.getenv('SCRAPER_PASSWORD')

scheduler = BackgroundScheduler()
options = webdriver.ChromeOptions()
options.add_argument('--disable-notifications') 
driver = webdriver.Chrome(options=options)
group_url = 'https://www.facebook.com/groups/chatyachalupynaprenajom/?sorting_setting=CHRONOLOGICAL'

TASK_FILE = 'tasks.json'
POSTS_FILE = 'posts.json'
TASKS_FLAG = False
message='Dobrý deň, videl som váš prípevok a chceli by sme vám ponúknuť našu chatu Maru pri Oravskej priehrade https://www.hauzi.sk/chata-mara-namestovo'

def get_tasks():
    if not os.path.exists(TASK_FILE):
        return []
    
    try:
        with open(TASK_FILE, 'r') as file:
            # Read and decode the JSON data
            content = file.read().strip()
            if not content:  # Check if file is empty
                return []
            return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file {TASK_FILE}: {e}")
        return []  # Return an empty list in case of JSON error
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []  # Return an empty list in case of any other error

def update_tasks(tasks):
    with open(TASK_FILE, 'w') as file:
        json.dump(tasks, file, indent=4)

def get_posts():
    if not os.path.exists(POSTS_FILE):
        return []
    with open(POSTS_FILE, 'r') as file:
        return json.load(file)

def check_and_process_tasks():
    tasks = get_tasks()
    if tasks:
        # List to keep track of tasks to remove
        tasks_to_remove = []

        TASKS_FLAG = True
        # Process all tasks
        for task in tasks:
            if not task.get('processed', False):
                process_task(task)
                # Add to list of tasks to remove after processing
                tasks_to_remove.append(task['id'])
        TASKS_FLAG = False

        # Remove processed tasks from the list
        tasks = [task for task in tasks if task['id'] not in tasks_to_remove]
    
        # Update the tasks file with processed tasks
        update_tasks(tasks)
    else:
        print('No new tasks!')

def process_task(task):
    driver.switch_to.window(driver.window_handles[0])
    # Load posts
    posts = get_posts()
    
    # Find the post with the matching id
    post = next((post for post in posts if post['id'] == task['id']), None)
    
    if post and 'href' in post:
        url = post['href']
        print(f"Navigating to {url}")
        
         # Get the current window handle
        original_window = driver.current_window_handle

        # Open the href in a new tab
        driver.execute_script(f"window.open('{url}', '_blank');")
        driver.switch_to.window(driver.window_handles[-1])  # Switch to the new tab
            
        # Wait for the page to load
        time.sleep(10)  # Adjust this delay as needed

        # Find and click the "Message" button
        try:
            message_button = driver.find_element(By.XPATH, "//div[@aria-label='Message' and @role='button']")
            ActionChains(driver).move_to_element(message_button).click().perform()
            print("Message button clicked.")
        except Exception as e:
            print(f"Error finding or clicking the message button: {e}")
            driver.close()
            driver.switch_to.window(original_window)
            return

        # Wait for the chat input to appear
        time.sleep(3)  # Adjust this delay as needed
        
        # Find the chat input element
        try:
            chat_input = driver.find_element(By.XPATH, "//div[@aria-label='Message' and @role='textbox']")
            # Click on the chat input element to focus on it
            chat_input.click()
            print("Chat input clicked.")
            
            # Use ActionChains to type the message into the chat input
            actions = ActionChains(driver)
            actions.move_to_element(chat_input).click().send_keys(message).perform()
            # Final Enter key to send the message
            actions.send_keys(Keys.RETURN).perform()
            print("Message text entered.")
            time.sleep(5)
        except Exception as e:
            print(f"Error finding or setting the message text: {e}")

        # Optional: Send the message if there's a send button
        # You can use a similar approach to locate and click the send button if required

        # Close the new tab
        driver.close()
        # Switch back to the original tab
        driver.switch_to.window(original_window)
        # Mark the task as processed
        task['processed'] = True
    else:
        print("No href found for the post.")

def check_internet_and_reschedule():
    if is_connected():
        print("Internet connection restored. Resuming normal schedule.")
        schedule_next_tick()
    else:
        print(f"No internet connection. Checking again in {INTERNET_CHECK_INTERVAL} seconds.")
        next_run_time = datetime.now() + timedelta(seconds=INTERNET_CHECK_INTERVAL)
        scheduler.add_job(check_internet_and_reschedule, 'date', run_date=next_run_time)

def tick(first_scroll = HOW_MANY_SCROLLS):
    if is_connected():
        print('Tick! The time is: %s' % datetime.now())
        if TASKS_FLAG:
            print('Doing tasks, generate the new tick!')
        else:
            open_group(group_url) 
            posts = scrape_posts(first_scroll)
            print(posts)
            send_posts_to_server(posts)
        schedule_next_tick()
    else:
        print(f"No internet connection. Checking again in {INTERNET_CHECK_INTERVAL} seconds.")
        next_run_time = datetime.now() + timedelta(seconds=INTERNET_CHECK_INTERVAL)
        scheduler.add_job(check_internet_and_reschedule, 'date', run_date=next_run_time)

def is_connected():
    """Check internet connection by pinging Google DNS."""
    try:
        requests.get("http://www.google.com", timeout=5)
        return True
    except requests.ConnectionError:
        return False
    
def send_posts_to_server(posts):
    url = 'http://localhost:8000/chataMaraServer.php'
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(url, headers=headers, data=json.dumps(posts))
        if response.status_code == 200:
            print("Posts successfully sent to the server.")
        else:
            print(f"Failed to send posts. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

def get_random_interval(mean=60, variance=15):
    interval = random.gauss(mean, variance)
    interval = max(mean*0.5, interval)  # Minimum 30 seconds
    interval = min(mean*1.5, interval)  # Maximum 90 seconds
    return interval

def get_random_interval(base_time, variability):
    return base_time + random.uniform(-variability, variability)

def schedule_next_tick():
    now = datetime.now()
    current_hour = now.hour

    if 22 <= current_hour or current_hour < 8:  # 10 PM to 8 AM
        print('NIGHT TIME')
        interval = NIGHT_INTERVAL
    else:  # 8 AM to 10 PM
        interval = get_random_interval(CHECKING_TIME, CHECKING_TIME * 0.25)

    next_run_time = datetime.now() + timedelta(seconds=interval)
    scheduler.add_job(tick, 'date', run_date=next_run_time)
    print(f"Next tick scheduled in {interval:.2f} seconds.")

def shutdown_scheduler(signum, frame):
    print("Shutting down scheduler...")
    scheduler.shutdown()
    sys.exit(0)


# Function to log into Facebook
def login():
    print('Login')
    driver.get('https://www.facebook.com')
    email_input = driver.find_element(By.ID, 'email')
    password_input = driver.find_element(By.ID, 'pass')
    email_input.send_keys(username)
    password_input.send_keys(password)
    password_input.send_keys(Keys.RETURN)
    time.sleep(5)  # Wait for the page to load

def open_group(group_url):
    print('Open group')
    driver.get(group_url)
    time.sleep(5)  # Wait for the page to load

def truncate_url(url):
    # Find the index of the '/user/' segment
    user_segment_index = url.find('/user/')
    
    if user_segment_index == -1:
        # Return the original URL if '/user/' is not found
        return url
    
    # Extract the part of the URL before '/user/' segment
    truncated_url = url[:user_segment_index + len('/user/')]
    
    # Find the index of the next '/' after '/user/' segment
    next_slash_index = url.find('/', user_segment_index + len('/user/') + 1)
    
    if next_slash_index != -1:
        # Include the user ID part
        truncated_url += url[user_segment_index + len('/user/'):next_slash_index]
    
    return truncated_url

# Function to scrape posts from the group
def scrape_posts(howmuch):
    print('scraping the website')
    posts = []
    seen_texts = set()
    exclusion_keywords = ["Reels", "lajkujte", "zdieľajte", "Uvoľnený", "zľava", "Uvoľnené"]  # List of keywords to exclude
    last_height = driver.execute_script("return document.body.scrollHeight")
    howmuch_int = 0

    while howmuch_int<howmuch:
        elements = driver.find_elements(By.XPATH, "//div[@class='x1yztbdb x1n2onr6 xh8yej3 x1ja2u2z']")
        for element in elements:
            try:
                main_div = element.find_element(By.XPATH, ".//div[@class='html-div xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd']")
                #print(main_div.text)
                #posts.append(post_content)
                #print(main_div.text)
                if not any(keyword in main_div.text for keyword in exclusion_keywords):
                    name = ""
                    try:
                        name = main_div.find_element(By.XPATH, ".//span[@class='html-span xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x1hl2dhg x16tdsg8 x1vvkbs']").text
                    except:
                        try:
                            name = main_div.find_element(By.XPATH, ".//div[@class='x1i10hfl xjbqb8w x1ejq31n xd10rxx x1sy0etr x17r0tee x972fbf xcfux6l x1qhh985 xm0m39n x9f619 x1ypdohk xt0psk2 xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd x16tdsg8 x1hl2dhg xggy1nq x1a2a7pz x1sur9pj xkrqix3 xzsf02u x1s688f']").text
                        except:
                            pass  # Continue without a name if not found

                    # Extract href from <a> inside <span> with class xt0psk2
                    href = ""
                    try:
                        span_with_href = main_div.find_element(By.XPATH, ".//span[@class='xt0psk2']")
                        a_tag = span_with_href.find_element(By.XPATH, ".//a")
                        href = truncate_url(a_tag.get_attribute('href'))

                    
                        # Extract user ID from href
                        user_id_match = re.search(r'/user/(\d+)/', href)
                        user_id = user_id_match.group(1) if user_id_match else ""

                    except:
                        pass  # Continue without href if not found
                    
                    # Try multiple XPath options for extracting the text   
                    text = ""
                    try:
                        text = main_div.find_element(By.XPATH, ".//div[@class='xdj266r x11i5rnm xat24cr x1mh8g0r x1vvkbs x126k92a']").text
                    except:
                        try:
                            text_div = main_div.find_element(By.XPATH, ".//div[@class='html-div xe8uvvx xdj266r x11i5rnm xat24cr x1mh8g0r xexx8yu x4uap5 x18d9i69 xkhd6sd']")
                            text = text_div.text
                        except:
                            pass  # Continue without text if not found
                            
                    # Check if the text is already in the seen_texts set
                    if text not in seen_texts:
                        # Add the text to the seen_texts set
                        seen_texts.add(text)
                        
                        if "Anonymous participant" in text:
                            name = "Anonymous participant"
                            text = text_div.find_element(By.XPATH, ".//div[@class='x6s0dn4 x78zum5 xdt5ytf x5yr21d xl56j7k x10l6tqk x17qophe x13vifvy xh8yej3']").text

                        if name in text:
                            text = text_div.find_element(By.XPATH, ".//div[@class='x6s0dn4 x78zum5 xdt5ytf x5yr21d xl56j7k x10l6tqk x17qophe x13vifvy xh8yej3']").text
                            
                        # Append the post to the posts list
                        posts.append({
                            "name": name,
                            "href": href,
                            "text": text,
                        })
                
            except Exception as e:
                #print(f"Error: {e}")
                continue

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(8)  # Wait for new posts to load
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
        howmuch_int = howmuch_int + 1

    return posts

if __name__ == '__main__':
    print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
    time.sleep(5)  
    login()
    time.sleep(5) 
    
    tick(8)  # Schedule the first tick

    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, shutdown_scheduler)
    signal.signal(signal.SIGTERM, shutdown_scheduler)

    scheduler.start()

    try:
        while True:
            print(f"sleep {PAUSE_TIME}s...")
            time.sleep(PAUSE_TIME)
            if not TASKS_FLAG:
                print('Checking for new tasks...')
                check_and_process_tasks()
    except (KeyboardInterrupt, SystemExit):
        pass