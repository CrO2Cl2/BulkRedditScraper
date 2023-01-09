import os
import praw
import requests
import time
import slugify
from threading import Thread
from PIL import Image
from io import BytesIO
import json
import sys

import tkinter as tk

# Create the main window
window = tk.Tk()
window.title("BulkRedditScraper")

# Create a frame for the output box
output_frame = tk.Frame(window)
output_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

# Create a scrollbar for the output box
scrollbar = tk.Scrollbar(output_frame)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Create the output box
output_box = tk.Text(output_frame, yscrollcommand=scrollbar.set)
output_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Configure the scrollbar to work with the output box
scrollbar.config(command=output_box.yview)

# Create a frame for the input fields and radio buttons
input_frame = tk.Frame(window)
input_frame.pack(side=tk.BOTTOM, fill=tk.X)

# Create a label and an input field
input_label = tk.Label(input_frame, text="Number of Images:")
input_field = tk.Entry(input_frame)
input_label.pack(side=tk.LEFT)
input_field.pack(side=tk.LEFT, fill=tk.X, expand=True)

# Create some checkmark buttons
check_var1 = tk.IntVar()
check_var2 = tk.IntVar()
check_button1 = tk.Checkbutton(input_frame, text="Skip NSFW", variable=check_var1)
check_button2 = tk.Checkbutton(input_frame, text="Option 2", variable=check_var2)
check_button1.pack(side=tk.LEFT)
check_button2.pack(side=tk.LEFT)


# Set up Reddit API client
reddit = praw.Reddit(client_id='rU2ONrIRZ_Jd70K8u0TlAA', client_secret='Pg5uw5CwI2S7evS4Yc90kGx4tYBXUA', user_agent='ChromiumGuardian_scraper:V0.5')

# List of subreddit names to scrape
subreddit_names = ['pics', 'funny', 'aww', 'photo', 'fountainpens', 'images', 'Art', 'drawings', 'DigitalArt', 'blender', 'Watercolor',
                   'NatureIsFuckingLit', 'DesirePaths', 'whatisthisthing', 'cocktails', 'mildlyinfuriating', 'Wellthatsucks', 'sketches', 'memes', 'dankmemes'] 

# Number of images to scrape from each subreddit
for i in range(50):
  try:
    num_images = int(input_field.get())
  except ValueError:
    output_box.insert(tk.END, "---------------please enter a valid number-----------------\n triying again in 5 seconds \n")
    time.sleep(5)
  else:
    break
# time to sleep between scrapes 
sleeptime = 360
#skip NSFW
#size of the desired image
size = (128, 128)
# Directory to save images to
save_dir = 'picture_data'
# directory to save the "index"to
saved_data_file_path = "saved_data.json"
#maximum size of the 'index' file in MB. This also is how much disk RAM is allocated to  the indexing of posts. 
# It is usually not necessary to allocate more than the space needed by 2/3 cycles of scraping data
desired_size = 7
#initializing variables
# Check if the file exists
if not os.path.exists(saved_data_file_path):
  # If the file does not exist, create an empty list
  saved_data = []
  # Open the file in write mode
  output_box.insert(tk.END, "saved_data file not found|... creating file...\n")
  with open(saved_data_file_path, "w") as file:
    # Dump the empty list to the file as JSON
    json.dump(saved_data, file)
else:
  # If the file exists, open it in read mode
  output_box.insert(tk.END, "saved_data file found|...opening...\n")
  with open(saved_data_file_path, "r") as file:
    # Load the list from the file
    saved_data = json.load(file)
# Function to scrape and save images in 128p resolution from a subreddit
def scrape_subreddit(subreddit_name):
  global saved_data
  global count
  global errorcount
  global tokens

  # Set the maximum rate at which requests can be made
  max_rate = 40

  # Set the size of the token bucket
  bucket_size = max_rate
  # Rate at which the tokens are added to the bucket
  refill_rate = max_rate / 60
  # Initialize the number of tokens in the bucket to the maximum value
  tokens = bucket_size
  refill_time = time.time()
  # Get the subreddit
  subreddit = reddit.subreddit(subreddit_name)

  # Create the directory to save images to, if it doesn't already exist
  subreddit_save_dir = os.path.join(save_dir, subreddit_name)
  if not os.path.exists(subreddit_save_dir):
    os.makedirs(subreddit_save_dir)

  # Scrape the images
  for submission in subreddit.new(limit=num_images):
    # Skip non-image submissions
    if submission.id in saved_data:
      output_box.insert(tk.END, "data already processed\n")
      continue
    else:
      saved_data.append(submission.id)
    if not submission.url.endswith(('.jpg', '.png',)):
      output_box.insert(tk.END, "not an image|| skipping\n")
      continue

    if tokens == 0:
      # If there aren't enough tokens, refill the bucket gradually
      tokens += refill_rate * (time.time() - refill_time)
      refill_time = time.time()
    else:
      # If there are enough tokens, decrease the number of tokens by 1
      tokens -= 1



    # Download the image
    for i in range(3):
      try:
        response = requests.get(submission.url)
      except requests.exceptions.SSLError:
        # If an SSLError occurs, print an error message and skip this submission
        output_box.insert(tk.END, f"An SSLError occurred while scraping {submission.url}. Triying again.\n")
        errorcount += 1
        time.sleep(0.8)
        continue
      except requests.exceptions.ConnectionError as e:
        if "getaddrinfo failed" in str(e):
          output_box.insert(tk.END, "Error: getaddrinfo failed. Waiting and triying again\n")
          print()
          errorcount += 1
          time.sleep(0.8)
          continue
      else:
        break
    else:
      output_box.insert(tk.END, "Networking errors could not be solved skipping submission\n")
      break


    if response.status_code != 200:
      continue
    if check_var1.get() == 1:
      if submission.over_18:
        # If the submission is NSFW, skip this submission
        output_box.insert(tk.END, f"Submission {submission.id} is marked as NSFW. Skipping this submission.\n")
        continue

    # Resize the image
    image = Image.open(BytesIO(response.content))
    image = image.resize(size)
    
    #checking if the author is valid
    if submission.author is None:
      author = "unknown_user"
    else:
      author = submission.author.name
      
    # Create a file name for the image using the submission title, the original poster's username, and a slugified version of the subreddit name
    file_name = slugify.slugify(submission.title) + '_' + slugify.slugify(author) + '_' + slugify.slugify(subreddit_name) + os.path.splitext(submission.url)[1]

    # Save the image
    for i in range(2):
      try:
        file_path = os.path.join(subreddit_save_dir, file_name)
        image.save(file_path)
      except OSError as e:
        if e.errno == 22:
          output_box.insert(tk.END, "invalid File Name, slugifiying name\n")
          file_name = slugify.slugify(file_name)
          continue
        else:
          raise
      except ValueError as e:
        if str(e) == "unknown file extension: {ext}":
          output_box.insert(tk.END, "Invalid File extention, skipping submission\n")
          errorcount += 1
          break
        
      else: 
        break
    else:
      output_box.insert(tk.END, "slugificatin was not succesfull in handling the error. Skipping submission.\n")
     

    # Increment the counter
    count += 1
    output_box.insert(tk.END, "saved  new image number: " + str(count) + " made by " + author + "\n")

# Scrape the images in each subreddit in a separate thread
def scrape_subreddits():
  start_time = time.perf_counter()
  global count
  global errorcount
  count = 0
  errorcount = 0
  threads = []
  for subreddit_name in subreddit_names:
    thread = Thread(target=scrape_subreddit, args=(subreddit_name,))
    thread.start()
    threads.append(thread)

  # Wait for all threads to complete
  for thread in threads:
    thread.join()
  end_time = time.perf_counter()
  elapsed_time = end_time - start_time
  output_box.insert(tk.END, "----------------------------------------------------------------\n")
  output_box.insert(tk.END, f"this cycle took {elapsed_time} seconds\n")
  countmin = count /  ( elapsed_time / 60 )
  output_box.insert(tk.END, f"Scraped {count} images in this cycle|{countmin}/minute\n")
  output_box.insert(tk.END, f"{errorcount} errors were encuntered while scraping\n")
#Indexing cylclenumber

# Run the scraping function every 10 minutes indefinitely
def scrape():
  cyclenumber = 0
  while True:
    start_time_total = time.perf_counter()
    cyclenumber += 1
    output_box.insert(tk.END, "scraping cycle started...\n")
    scrape_subreddits()
    output_box.insert(tk.END, "----------------------------------------------------------------\n")
    output_box.insert(tk.END, f"scrape cylcle number {cyclenumber} finished...\n")
    try:
      totalrate = count / (elapsed_time_total / 60 / 60 ) 
      output_box.insert(tk.END, f"the total scraping rate is {totalrate}/hour\n")
    except NameError:
      output_box.insert(tk.END, "the total scraping rate cannot be calculated on the first round of the scrape\n")
    output_box.insert(tk.END, "----------------------------------------------------------------\n")
    output_box.insert(tk.END, "saving already processed data for the next run\n")
    #script to shorten the index data if needed
    list_size = sys.getsizeof(saved_data)
    output_box.insert(tk.END, f"the index data is currently consuming: {list_size} Bytes\n ")
    desired_size_raw = desired_size * 1024 * 1024
    if list_size > desired_size_raw:
      output_box.insert(tk.END, "Shortening the list to the desired size...\n") 
      while list_size > desired_size_raw:
        # Remove the oldest entry from the list
        saved_data.pop(0)
        # Recalculate the size of the list in bytes
        list_size = sys.getsizeof(saved_data)
      output_box.insert(tk.End, "Done! Saving Data to disk \n")
    else:
      output_box.insert(tk.END, "No shortening of the list is necessary. Saving Data to disk \n")
        
  
    with open("saved_data.json", "w") as file:
    # Dump the list to the file as JSON
      json.dump(saved_data, file)
    output_box,insert(tk.END,"Done \n ---------------------------------------------------------------- \n waiting for the next scrape to start...")
    time.sleep(sleeptime)
    stop_time_total = time.perf_counter()
    elapsed_time_total = stop_time_total - start_time_total
    
start_button = tk.Button(input_frame, text="Start", command=scrape)
start_button.pack(side=tk.RIGHT)    
    
window.mainloop()
