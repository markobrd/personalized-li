import openai
import yaml

with open('config.yaml') as config_file:
    config = yaml.safe_load(config_file)

client = openai.AsyncOpenAI(api_key=config['API_KEY'])


async def check_topic(post_text, id):

    prompt = f"Is the following post relevant to any of these topics: {config['topics']}? Answer only True or False.\n\nPost: {post_text}"

    messages = [{"role": "user", "content": prompt}]
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=10
    )
    print(response.choices[0].message.content.lower() +"\n\n")
    # Simplified example; adjust based on actual API response
    if "true" in response.choices[0].message.content.lower():
        return id
    else:
        return -1

if __name__ == "__main__":
    print("started")
    post = """🚀 𝗣𝗲𝗿𝘀𝗶𝘀𝘁𝗲𝗻𝗰𝗲 𝗜𝘀𝗻’𝘁 𝗝𝘂𝘀𝘁 𝗮 𝗩𝗶𝗿𝘁𝘂𝗲—𝗜𝘁’𝘀 𝗦𝗰𝗶𝗲𝗻𝗰𝗲. 𝗛𝗲𝗿𝗲’𝘀 𝗪𝗵𝘆.Ever wanted to quit? 😤 So did NASA. They failed 𝟱 𝘁𝗶𝗺𝗲𝘀 before landing the Perseverance rover on Mars. But guess what?
    Today, it’s sending us breathtaking photos of alien sunsets. 🌌 Moral? 𝗧𝗵𝗲 𝘂𝗻𝗶𝘃𝗲𝗿𝘀𝗲 𝗿𝗲𝘄𝗮𝗿𝗱𝘀 𝘁𝗵𝗼𝘀𝗲 𝘄𝗵𝗼 𝗿𝗲𝗳𝘂𝘀𝗲 𝘁𝗼 𝗴𝗶𝘃𝗲 𝘂𝗽.Let’s get real:🧠 𝗚𝗿𝗶𝘁 > 𝗧𝗮𝗹𝗲𝗻𝘁. A study by UPenn found th
    at people with perseverance (not just smarts) are 60% more likely to crush their long-term goals.💼 𝟴𝟲% 𝗼𝗳 𝗹𝗲𝗮𝗱𝗲𝗿𝘀 say resilience is THE top skill for success… yet 72% of us almost quit when things get tough (Edelman,
    2023).𝗛𝗲𝗿𝗲’𝘀 𝘁𝗵𝗲 𝘁𝗲𝗮 ☕:Life’s like a video game 🎮—you beat one boss, another appears. But quitting? That’s like unplugging the controller right before the final level. 🛑𝗥𝗲𝗺𝗲𝗺𝗯𝗲𝗿:✨ Thomas Edison “failed” 1,0
    00 times before inventing the lightbulb. His take? “I didn’t fail. I discovered 1,000 ways that don’t work.”✨ 𝟴𝟬% 𝗼𝗳 “𝗼𝘃𝗲𝗿𝗻𝗶𝗴𝗵𝘁 𝘀𝘂𝗰𝗰𝗲𝘀𝘀𝗲𝘀” took 8+ years of grinding in the shadows (Stanford). Your moment mi
    ght be one step away.𝗦𝗼… 𝗳𝗲𝗲𝗹𝗶𝗻𝗴 𝘀𝘁𝘂𝗰𝗸?Ask yourself:❓ “What if I’m closer than I think?”❓ “Will quitting SOLVE my problem… or just delay it?”❓ “What’s ONE tiny win I can chase today?” (Example: Send that email. M
    ake that call. Fix one slide. 🎯)𝗕𝗼𝘁𝘁𝗼𝗺 𝗹𝗶𝗻𝗲:Life doesn’t hand out trophies for “almost.” 🏆 It’s not about avoiding storms—it’s about learning to dance in the rain, then building a boat, and maybe inventing waterproof
    shoes along the way. ⛈️⛵👟𝗧𝗮𝗴 𝘀𝗼𝗺𝗲𝗼𝗻𝗲 𝘄𝗵𝗼 𝗡𝗘𝗩𝗘𝗥 𝗾𝘂𝗶𝘁𝘀 👇Let’s cheer for the fighters, the scrappy dreamers, and the ones who turn “I can’t” into “Watch me.” 🙌FollowGaurav Tomar 🇮🇳for more.hashtag#Resili
    enceMattershashtag#SuccessIsAParadeNotASprinthashtag#KeepGoinghashtag#NoExcuseshashtag#YouGotThis…more"""
    print(check_topic(post))