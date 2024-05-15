from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Give document to OCR
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

doc = DocumentFile.from_pdf("Contrat.pdf")
print(f"Number of pages: {len(doc)}")

# Instantiate a pretrained model
predictor = ocr_predictor(pretrained=True)

result = predictor(doc)

# JSON export
raw_export = result.render()
print(raw_export)

json_data = None

with open("./prompts/json_data.json", "r", encoding="UTF-8") as file:
    json_data = json.load(file)

# Read the prompt
prompt = ""
systemMessage = ""

with open("./prompts/chatgpt_prompt.txt", "r") as file:
    prompt = file.read()

prompt_template = PromptTemplate(
    template=prompt, input_variables=["json_data", "document"]
).format(json_data=str(json_data), document=raw_export)

with open("./prompts/system_message.txt", "r") as file:
    systemMessage = file.read()

# Specify input_variables as an empty list if there are no variables to format
systemPrompt = PromptTemplate(template=systemMessage, input_variables=[])

messages = [
    SystemMessage(content=systemPrompt.format()),
    HumanMessage(content=prompt_template),
]

model = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-3.5-turbo")

result = model.invoke(messages)

with open("./prompts/json_output.json", "w", encoding="UTF-8") as file:
    file.write(result.content)
