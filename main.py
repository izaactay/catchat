import os
import requests
from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI
from openai import AssistantEventHandler
from typing_extensions import override
from openai.types.beta.threads import Text, TextDelta

load_dotenv()

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CAT_API_URL = os.getenv('CAT_API_URL')
CAT_API_KEY = os.getenv('CAT_API_KEY')

def get_cat(breeds=None):
    url = CAT_API_URL
    res = requests.get(url)
    return res.json()[0]['url']

function_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_cat",
            "description": "Get an image of a cat",
            "parameters": {
            
            },
        }
    }
]
 
# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):
    """
    Event handler for the assistant stream
    """

    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == 'thread.run.requires_action':
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)

    @override
    def on_text_created(self, text: Text) -> None:
        """
        Handler for when a text is created
        """

        st.session_state.assistant_text = [""]
        

    @override
    def on_text_delta(self, delta: TextDelta, snapshot: Text):
        """
        Handler for when a text delta is created
        """
        
        if delta.value:
            st.session_state.assistant_text[-1] += delta.value
        
        st.write(st.session_state.assistant_text[-1])

    def on_text_done(self, text: Text):
        """
        Handler for when text is done
        """

        st.write("".join(st.session_state["assistant_text"][-1]))
        st.session_state.chat_history.append(("assistant", text.value))
        
    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "get_cat":
                try:

                    cat = get_cat()
                    # Append tool output in the required format
                    tool_outputs.append({"tool_call_id": tool.id, "output": f"{cat}"})
                except ValueError as e:
                    # Handle any errors when getting cat
                    tool_outputs.append({"tool_call_id": tool.id, "error": str(e)})
                    
        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs)

    def submit_tool_outputs(self, tool_outputs):
        # Use the submit_tool_outputs_stream helper
        with client.beta.threads.runs.submit_tool_outputs_stream(
                thread_id=self.current_run.thread_id,
                run_id=self.current_run.id,
                tool_outputs=tool_outputs,
                event_handler=EventHandler(),
        ) as stream:
            # for text in stream.text_deltas:
            #     print(text, end="", flush=True)

            stream.until_done()









# Set OpenAI API key from Streamlit secrets
client = OpenAI(api_key=OPENAI_API_KEY)


assistant = client.beta.assistants.create(
    name="Cat Chatbot",
    description="You are great at finding images of cats on the internet.",
    model="gpt-4o-mini",
    tools=function_tools
    )

st.title("CatChat")

# Initialize chat history
if "thread" not in st.session_state:
    st.session_state['thread'] = client.beta.threads.create()
     
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if "assistant_text" not in st.session_state:
    st.session_state.assistant_text = [""]

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "text_boxes" not in st.session_state:
    st.session_state.text_boxes = []
    
def display_chat_history():
    for role, content in st.session_state.chat_history:
        if role == "user":
            st.chat_message("User").write(content)
        else:
            st.chat_message("Assistant").write(content)

display_chat_history()

# Accept user input
if prompt := st.chat_input("What cat?"):
    
    # Add user message to chat history
    st.session_state.chat_history.append(("user", prompt))
    
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
        )

    # Display user message in chat message container
    with st.chat_message("user"):
        st.markdown(prompt)
        
    
    with st.chat_message("Assistant"):
        with st.empty():
            with client.beta.threads.runs.stream(
                thread_id=st.session_state.thread_id,
                assistant_id=assistant.id,
                instructions="Please help the user find cats.",
                event_handler=EventHandler(),
                ) as stream:
                
                stream.until_done()
        

        