from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv, find_dotenv
from doctr.io import DocumentFile
from doctr.models import ocr_predictor

load_dotenv(find_dotenv())

def process_text_file(file_path):
    with open(file_path, 'r', encoding='UTF-8') as file:
        return file.read()

def process_pdf_or_image(file_path, predictor):
    try:
        doc = DocumentFile.from_pdf(file_path) if file_path.endswith('.pdf') else DocumentFile.from_images(file_path)
        result = predictor(doc)
        raw_export = result.render()
        if len(raw_export.strip()) < 20:
            return None
        return raw_export
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def create_folder_and_save_outputs(json_output, raw_text=None, original_text=None, output_dir="./outputs"):
    document_name = json_output.get("document_name", "Unknown")
    date = json_output.get("date", "")

    if document_name is None:
        document_name = "Unknown"
    if date is None:
        date = ""

    folder_name = f"{document_name}:{date}" if date else document_name
    folder_path = os.path.join(output_dir, folder_name.replace(" ", "_").replace("/", "_"))
    os.makedirs(folder_path, exist_ok=True)

    if raw_text:
        with open(os.path.join(folder_path, "raw_text.txt"), 'w', encoding='UTF-8') as file:
            file.write(raw_text)
    if original_text:
        with open(os.path.join(folder_path, "original_text.txt"), 'w', encoding='UTF-8') as file:
            file.write(original_text)
    
    with open(os.path.join(folder_path, "json_output.json"), 'w', encoding='UTF-8') as file:
        json.dump(json_output, file, ensure_ascii=False, indent=4)

def main():
    # Load environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize model and predictor
    model = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    predictor = ocr_predictor(pretrained=True)

    # Read prompt and system messages
    with open("./prompts/chatgpt_prompt.txt", "r") as file:
        prompt = file.read()
    
    with open("./prompts/system_message.txt", "r") as file:
        systemMessage = file.read()

    systemPrompt = PromptTemplate(template=systemMessage, input_variables=[])

    with open('./prompts/json_data.json', 'r', encoding="UTF-8") as file:
        json_data = json.load(file)
        
    with open('./prompts/json_data1.json', 'r', encoding="UTF-8") as file:
        json_data1 = json.load(file)
        
    with open('./prompts/json_data2.json', 'r', encoding="UTF-8") as file:
        json_data2 = json.load(file)

    with open('./prompts/json_data3.json', 'r', encoding="UTF-8") as file:
        json_data3 = json.load(file)
    
    documents_folder = "./Documents"
    for filename in os.listdir(documents_folder):
        file_path = os.path.join(documents_folder, filename)
        raw_text = None
        original_text = None

        if filename.endswith('.txt'):
            original_text = process_text_file(file_path)
        elif filename.endswith('.pdf') or filename.endswith(('.png', '.jpg', '.jpeg')):
            raw_text = process_pdf_or_image(file_path, predictor)
            if not raw_text:
                continue
        else:
            continue

        document_text = original_text if original_text else raw_text
        prompt_template = PromptTemplate(template=prompt, input_variables=["json_data", "document"]).format(json_data=str(json_data),json_data1=str(json_data1),json_data2=str(json_data2),json_data3=str(json_data3), document=document_text)
        
        messages = [
            SystemMessage(content=systemPrompt.format()),
            HumanMessage(content=prompt_template)
        ]

        result = model.invoke(messages)
        json_output = json.loads(result.content)
        
        create_folder_and_save_outputs(json_output, raw_text=raw_text, original_text=original_text)

    threads_folder = "./threads"
    for thread_folder in os.listdir(threads_folder):
        thread_path = os.path.join(threads_folder, thread_folder)
        if os.path.isdir(thread_path):
            for email_folder in os.listdir(thread_path):
                email_path = os.path.join(thread_path, email_folder)
                if os.path.isdir(email_path):
                    for filename in os.listdir(email_path):
                        file_path = os.path.join(email_path, filename)
                        raw_text = None
                        original_text = None

                        if filename.endswith('.txt'):
                            original_text = process_text_file(file_path)
                        elif filename.endswith('.pdf') or filename.endswith(('.png', '.jpg', '.jpeg')):
                            raw_text = process_pdf_or_image(file_path, predictor)
                            if not raw_text:
                                continue
                        else:
                            continue

                        document_text = original_text if original_text else raw_text
                        prompt_template = PromptTemplate(template=prompt, input_variables=["json_data", "document"]).format(
                            json_data=str(json_data),
                            json_data1=str(json_data1),
                            json_data2=str(json_data2),
                            json_data3=str(json_data3),
                            document=document_text
                        )

                        messages = [
                            SystemMessage(content=systemPrompt.format()),
                            HumanMessage(content=prompt_template)
                        ]

                        result = model.invoke(messages)
                        json_output = json.loads(result.content)

                        create_folder_and_save_outputs(json_output, raw_text=raw_text, original_text=original_text, output_dir="./outputs")
                        
if __name__ == "__main__":
    main()