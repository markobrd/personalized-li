import openai
import yaml

with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)
openai.api_key = config['API_KEY']

def call_chatgpt_api(post_text):
    
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Determine if the following post is on an approved topic: {post_text}",
        max_tokens=10
        
    )
    # Simplified example; adjust based on actual API response
    return "approved" in response.choices[0].text.lower()
