# ReelScout

On my Instagram account I have quite a few Collections of saved posts, mostly reels. Most of these are for travel.

The idea is that with this tool I can login to my insta, pick a named collection that I have saved in my account, and then use AI to make a list of the locations mentioned in each post, as well as other useful information about this. The end product should have a frontend to make this easy to use (but don't work on the front end yet until told to do so! this is just to keep in mind)

## Collecting the Videos

The backend should consist of using python and instagrapi library (its docs are located in `./3rdparty/instagrapi-docs`)

It should be able to login with my account with a session file (file in the root of this project called `./auth/session.json`)

Get a list of my saved collections, then let me pick from one of them

Then I want to compile a list of the URLs of all the posts.

Once I have that I want another module using the same library to be able to handle the downloading of each item from that list. The videos would be saved locally in a folder in the project, under the name of the colleciton its a part of. In that same folder, store a JSON file with the relative path of the downloaded video, the caption, and the url per entry.

## Video Processing

Once I have all the videos and their corresponding data I want to parse out information from the video / post. 

I will be using Gemini API for this and the flash model that can also handle video. I have included the Gemini python library docs in `3rdparty/python-genai-docs` as well as a direct example of how to process video using Gemini in `3rdparty/gemini_video.ipynb`. My API key is located in `auth/.env` as an environment variable.

The goal in this step is to first submit the caption of the video to the llm, using some prompt to ask if the caption has a specific location (or multiple ones) listed. It should return some structured output, first to confirm whether there is any specific location (usually a restaurant, POI, not just a general area), if yes then return the location (or multiple) listed.

If the caption does not contain this information then proceed to do the same but this time upload the video to the llm to run the same test. 

If there is no location data that it can extrapolate then just make sure to make note of it later

The final output should be some csv that includes the post url, and the locations mentioned in the post.

## Data Cleanup 

As a bonus last step we want to the Google Maps url of the places mentioned, it doesn't have to be perfect just return the most likely relevant url for each location. We can use the Gemini API with search grounding to return the URL as structured output or we can implement with the google maps places api

## UI 

Again don't implement the UI until told to do so, but we would like to create a UI for this, assume the server provides its own session file for now but we should be able to select from a drop down the collection, and then have it perform all the steps mentioned with the end result being a table of sort for each post with the location, what the recomendation was, the type of place suggested, and if possible the video embedded in the table row to make it easy to access

There should also be a way to load up existing downloaded collections 
Include progress bars for each step as it performs the actions


# Notes 

- Everything should still be able to be used via the terminal (CLI or TUI)
- Modules should be seperated into its own files where it makes sense to keep the code clean
