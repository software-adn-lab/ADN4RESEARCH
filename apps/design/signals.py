# diseno/signals.py
from config.events import bus

def on_research_question_created(data):
    print(f"New question: {data['title']}")

bus.subscribe("research_question_created", on_research_question_created)
