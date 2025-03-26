from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

template = """
You are an AI that strictly determines whether a given post is about specified topics.  
Return only `True` or `False` with no explanations.

Post: "{post}"  
Topics: "{topics}"  

Answer:
"""
model = OllamaLLM(model = "llama3.2", cache = False)

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def check_topic(topics, post):
    res = chain.invoke({"topics":str(topics), "post":post})
    return res

test_prompt = """Rheinmetall’s Lynx KF41 is one of the most advanced infantry fighting vehicles in the world. A German TV documentary is now exclusively covering production, testing and capabilities of the IFV.
 
“The Lynx – High-Tech from Germany” will be aired as a world premiere on Friday, March 28, 2025, at 10:05 p.m. CET on German TV channel WELT TV. The 50-minute program is set to be repeated an hour later on the N24 Doku channel.
 
For the first time, a TV crew was given in-depth access to production and testing of the Lynx in Unterluess, Germany and in Zalaegerszeg, Hungary. The documentary is also covering in-house construction of the electro-optical components and testing of the first Lynx simulator. The rollout of the first vehicle built in Hungary will also be shown, testifying to Rheinmetall’s expertise in setting up most modern production sites in record time.
 
The Lynx documentary is the third film by WELT TV about a Rheinmetall vehicle. Click below to watch the documentaries about the Puma infantry fighting vehicle (joint program) and the HX81 “Elefant” heavy equipment transporter:
 
Puma Infantry Fighting Vehicle (2015), German: https://lnkd.in/e47hGpKT
 
HX81 Heavy Equipment Transporter (2022), German: https://lnkd.in/ep84qciP"""

if __name__ == "__main__":
    print(check_topic(topics= "AI, LLMS, ENGINEERING, LEADERSHIP", post = test_prompt))