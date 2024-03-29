# importing packets
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
import tqdm


# Set up Reddit API client
reddit = praw.Reddit(client_id='ID', client_secret='secret', user_agent='Bulk_scraper:V2.6')
# List of subreddit names to scrape
saving_method = "per_subreddit_name" #valid options are: "per_subreddit_name", "all_together"
subreddit_names = ['pics', 'funny', 'aww', 'photo'] 
# Number of images to scrape from each subreddit
num_images = 200
# time to sleep between scrapes 
sleeptime = 360
#skip NSFW
skipNSFW = True
#size of the desired image
size = (128, 128)
# Directory to save images to
save_dir = 'picture_data'
# directory to save the "index"to
saved_data_file_path = "saved_data.json"
#maximum size of the 'index' file in MB. This also is how much disk RAM is allocated to  the indexing of posts. 
desired_size = 7
#initializing variables



# Check if the file exists
if not os.path.exists(saved_data_file_path):
  # If the file does not exist, create an empty list
  saved_data = []
  # Open the file in write mode
  print("saved_data file not found|... creating file...")
  with open(saved_data_file_path, "w") as file:
    # Dump the empty list to the file as JSON
    json.dump(saved_data, file)
else:
  # If the file exists, open it in read mode
  print("saved_data file found|...opening...")
  with open(saved_data_file_path, "r") as file:
    # Load the list from the file
    saved_data = json.load(file)
# Function to scrape and save images in 128p resolution from a subreddit
def scrape_subreddit(subreddit_name):
  global saved_data
  global count
  global errorcount
  # Get the subreddit
  subreddit = reddit.subreddit(subreddit_name)

  # Create the directory to save images to, if it doesn't already exist
  if saving_method == "per_subreddit_name":
    subreddit_save_dir = os.path.join(save_dir, subreddit_name)
    if not os.path.exists(subreddit_save_dir):
      os.makedirs(subreddit_save_dir)
  elif saving_method == "all_together":
    subreddit_save_dir = save_dir 
  else:
    print("ERROR!saving menthod does not corrispond to any of the valid values")
    print("--------------------------------------------------------")
    print("defaulting to per_subreddit_name")
    subreddit_save_dir = os.path.join(save_dir, subreddit_name)
    if not os.path.exists(subreddit_save_dir):
      os.makedirs(subreddit_save_dir)
    


  # Scrape the images
  #checks if the data has already been processed
  for submission in tqdm(subreddit.new(limit=num_images), desc="scraping data from: "+ str(subreddit)):
    # rest of your code

    if submission.id in saved_data:
      print("data already processed")
      continue
    else:
      saved_data.append(submission.id)
    # Skip non-image submissions
    if not submission.url.endswith(('.jpg', '.png',)):
      print("not an image|| skipping")
      continue
    if submission.over_18 and skipNSFW is True:
      # If the submission is NSFW, skip this submission
      print(f"Submission {submission.id} is marked as NSFW. Skipping this submission.")
      continue
    # Download the image
    for i in range(3):
      try:
        response = requests.get(submission.url)
      except requests.exceptions.SSLError:
        # If an SSLError occurs, print an error message and skip this submission
        print(f"An SSLError occurred while scraping {submission.url}. Triying again.")
        errorcount += 1
        time.sleep(0.8)
        continue
      except requests.exceptions.ConnectionError as e:
        if "getaddrinfo failed" in str(e):
          print("Error: getaddrinfo failed. Waiting and triying again")
          errorcount += 1
          time.sleep(0.8)
          continue
      else:
        break
    else:
      print("Networking errors could not be solved skipping submission")
      break

    response_code = response.status_code
    if response_code != 200:
      print(f"Networking error has occurred. reddit returned {response_code}")
      print("skipping submission and waiting out")
      errorcount += 1
      time.sleep(2)
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
          print("invalid File Name, slugifiying name")
          file_name = slugify.slugify(file_name)
          continue
        else:
          raise
      except ValueError as e:
        if str(e) == "unknown file extension: {ext}":
          print("Invalid File extention, skipping submission")
          errorcount += 1
          break
        
      else: 
        break
    else:
      print("slugificatin was not succesfull in handling the error. Skipping submission.")	

    # Increment the counter
    count += 1
    print("saved  new image number: " + str(count) + " made by " + author)

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
  print("----------------------------------------------------------------")
  print(f"this cycle took {elapsed_time} seconds")
  countmin = count /  ( elapsed_time / 60 )
  print(f"Scraped {count} images in this cycle|{countmin}/minute")
  print(f"{errorcount} errors were encuntered while scraping")
#Indexing cylclenumber
cyclenumber = 0

# Run the scraping function indefinitely
while True:
  start_time_total = time.perf_counter()
  cyclenumber += 1
  print ("scraping cycle started...")
  scrape_subreddits()
  print("----------------------------------------------------------------")
  print (f"scrape cylcle number {cyclenumber} finished...")
  try:
    totalrate = count / (elapsed_time_total / 60 / 60 ) 
    print(f"the total scraping rate is {totalrate}/hour")
  except NameError:
    print("the total scraping rate cannot be calculated on the first round of the scrape")
  print("----------------------------------------------------------------")
  print("saving already processed data for the next run")
  #script to shorten the index data if needed
  list_size = sys.getsizeof(saved_data)
  print(f"the index data is currently consuming: {list_size} Bytes ")
  desired_size_raw = desired_size * 1024 * 1024
  if list_size > desired_size_raw:
    print("Shortening the list to the desired size...") 
    while list_size > desired_size_raw:
      # Remove the oldest entry from the list
      saved_data.pop(0)
      # Recalculate the size of the list in bytes
      list_size = sys.getsizeof(saved_data)
    print("Done! Saving Data to disk")
  else:
    print("No shortening of the list is necessary. Saving Data to disk")
      
  with open("saved_data.json", "w") as file:
  # Dump the list to the file as JSON
    json.dump(saved_data, file)
  print("Done")
  print("----------------------------------------------------------------")
  print ("waiting for the next scrape to start...")
  time.sleep(sleeptime)
  stop_time_total = time.perf_counter()
  elapsed_time_total = stop_time_total - start_time_total
