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

def create_folder_and_save_outputs(ttl_content, raw_text=None, original_text=None, output_dir="./outputs", email_processing=False, file_name=None):
    if email_processing:
        if file_name.endswith('.txt'):
            folder_name = "email_output"
            original_text = None
        else:
            document_name = os.path.splitext(file_name)[0]
            folder_name = f"output_{document_name}"
    else:
        # Extract document name from TTL content
        doc_name_start = ttl_content.find("ex:") + 3
        doc_name_end = ttl_content.find(" ", doc_name_start)
        document_name = ttl_content[doc_name_start:doc_name_end]
        folder_name = document_name

    folder_path = os.path.join(output_dir, folder_name.replace(" ", "_").replace("/", "_"))
    os.makedirs(folder_path, exist_ok=True)

    if raw_text:
        with open(os.path.join(folder_path, "raw_text.txt"), 'w', encoding='UTF-8') as file:
            file.write(raw_text)
    if original_text:
        with open(os.path.join(folder_path, "original_text.txt"), 'w', encoding='UTF-8') as file:
            file.write(original_text)
    
    with open(os.path.join(folder_path, "rdf_output.ttl"), 'w', encoding='UTF-8') as file:
        file.write(ttl_content)

def generate_ttl_data(model, document_text, prompt_template):
    prompt = prompt_template.format(document=document_text)

    messages = [
        SystemMessage(content="Extract structured information from the document."),
        HumanMessage(content=prompt),
    ]

    result = model.invoke(messages)
    return result.content

def process_files_in_folder(folder_path, predictor, model, systemPrompt, prompt_template, email_processing=False):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
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
        ttl_content = generate_ttl_data(model, document_text, prompt_template)

        create_folder_and_save_outputs(ttl_content, raw_text=raw_text, original_text=original_text, output_dir=folder_path, email_processing=email_processing, file_name=filename)

def main():
    # Load environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize model and predictor
    model = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    predictor = ocr_predictor(pretrained=True)

    # Read prompt and system messages from graph_prompts folder
    with open("./graph_prompts/system_message.txt", "r") as file:
        systemMessage = file.read()

    systemPrompt = PromptTemplate(template=systemMessage, input_variables=[])

    with open("./graph_prompts/chatgpt_prompt.txt", "r") as file:
        chatgptPrompt = file.read()

    # Process Documents folder
    documents_folder = "./Documents"
    process_files_in_folder(documents_folder, predictor, model, systemPrompt, chatgptPrompt)

    # Process threads folder
    threads_folder = "./threads"
    for thread_folder in os.listdir(threads_folder):
        thread_path = os.path.join(threads_folder, thread_folder)
        if os.path.isdir(thread_path):
            for email_folder in os.listdir(thread_path):
                email_path = os.path.join(thread_path, email_folder)
                if os.path.isdir(email_path):
                    process_files_in_folder(email_path, predictor, model, systemPrompt, chatgptPrompt, email_processing=True)

if __name__ == "__main__":
    main()
