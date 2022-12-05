# GwenBot

### ! ***Currently in testing - will be invite only until testing is complete*** !

A custom Discord music bot themed around a very cute cat :smile_cat:

![guen_v_small](https://user-images.githubusercontent.com/21161138/205741226-ddacc6c3-0d59-4083-95a6-7141fd4eb61e.jpg)

---

#### Current Features
- "Shipping" feature (mention one or two people and you'll get a random compatibility number that changes each day)
- Ability to search for videos on YouTube
  - Results are shown in pages, each page has a forward and backward button
  - Each video included in the results can be either played or added to the current queue
- Ability to play audio by directly giving GwenBot a youtube video link
- Audio can be stopped at any time ether with a command or by clicking the "Stop" button that GwenBot provides
- All important commands have shorter, easier to type aliases
- Detailed descriptions of all available commands
  - /gwen_help for a shorter list
  - /gwen help or /g:help for more detailed information
  - /gwen help *<category>* or /g:help *<category>* for specific category help
  - /gwen help *<command>* or /g:help *<command>* for help with a specific command


#### Help Command Screenshot Examples
##### /gwen help
![image](https://user-images.githubusercontent.com/21161138/205742152-e4a6b36c-514d-47cf-aa2f-a88abcd8a9b4.png)

##### /gwen help Music OR /g:help Music
![image](https://user-images.githubusercontent.com/21161138/205742195-e52f7b24-371c-4a4b-8543-010fbd7cc44e.png)

##### /gwen help search OR /g:help search
![image](https://user-images.githubusercontent.com/21161138/205742425-0e117ff5-44d0-4df5-8ece-6459e103e60f.png)


#### Requirements
- A "discord_secrets.json" file must be placed in the root directory
  - To obtain begin my reading the intro on the [Discord Developer Portal](https://discord.com/developers/docs)
  - Must contain:
    - app_id
    - public_key
    - permissions_int
    - token
 
- An "api_key.secret" file in must be placed the root directory
  - Must contain a valid YouTube Data V3 API Key
  - This can be obtained by following the instructions [here](https://developers.google.com/youtube/v3/getting-started)
