import openai

openai.api_key = 'YOUR_OPENAI_API_KEY'

def call_chatgpt_api(post_text):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Determine if the following post is on an approved topic: {post_text}",
        max_tokens=10
    )
    # Simplified example; adjust based on actual API response
    return "approved" in response.choices[0].text.lower()
