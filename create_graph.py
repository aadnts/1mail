from neo4j import GraphDatabase
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
import json
import os
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Set up Neo4J connection
class Neo4JConnector:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        with self.driver.session() as session:
            result = session.run(query, parameters)
            return result.data()

def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

def create_knowledge_graph(connector, json_data):
    # Define nodes and relationships based on JSON structure
    for entry in json_data:
        if 'document_name' in entry:
            doc_name = entry['document_name']
            query = """
            MERGE (d:Document {name: $doc_name})
            """
            connector.execute_query(query, {'doc_name': doc_name})

            if 'sender' in entry:
                sender_name = entry['sender'].get('name')
                if sender_name:
                    query = """
                    MERGE (s:Sender {name: $sender_name})
                    MERGE (d:Document {name: $doc_name})
                    MERGE (s)-[:SENT]->(d)
                    """
                    connector.execute_query(query, {'sender_name': sender_name, 'doc_name': doc_name})

            # Add more relationships based on the structure of your JSON data
            if 'company' in entry:
                company_name = entry['company'].get('name')
                if company_name:
                    query = """
                    MERGE (c:Company {name: $company_name})
                    MERGE (d:Document {name: $doc_name})
                    MERGE (c)-[:RELATED_TO]->(d)
                    """
                    connector.execute_query(query, {'company_name': company_name, 'doc_name': doc_name})

def initialize_model(api_key):
    model = ChatOpenAI(api_key=api_key, model="gpt-3.5-turbo")
    return model

def generate_structured_data(model, document_text, json_template):
    prompt_template = PromptTemplate(
        template=json_template, input_variables=["document"]
    ).format(document=document_text)

    messages = [
        SystemMessage(content="Extract structured information from the document."),
        HumanMessage(content=prompt_template),
    ]

    result = model.invoke(messages)
    return json.loads(result.content)

def process_files_in_folder(folder_path, model, connector, systemPrompt, json_template):
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith('.json'):
            json_data = load_json(file_path)
            create_knowledge_graph(connector, json_data)
        elif filename.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as file:
                document_text = file.read()
                structured_data = generate_structured_data(model, document_text, json_template)
                create_knowledge_graph(connector, [structured_data])

def main():
    # Load environment variables
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Initialize model and Neo4J connector
    model = initialize_model(api_key)
    connector = Neo4JConnector("bolt://localhost:7687", "neo4j", "topsecret")

    # Read system message
    with open("./prompts/system_message.txt", "r") as file:
        systemMessage = file.read()

    systemPrompt = PromptTemplate(template=systemMessage, input_variables=[])

    # JSON template for ChatGPT prompt
    json_template = """
    {
        "document_name": "{document_name}",
        "sender": "{sender}",
        "date": "{date}"
    }
    """

    # Process Documents folder
    documents_folder = "./Documents"
    process_files_in_folder(documents_folder, model, connector, systemPrompt, json_template)

    # Process threads folder
    threads_folder = "./threads"
    for thread_folder in os.listdir(threads_folder):
        thread_path = os.path.join(threads_folder, thread_folder)
        if os.path.isdir(thread_path):
            for email_folder in os.listdir(thread_path):
                email_path = os.path.join(thread_path, email_folder)
                if os.path.isdir(email_path):
                    process_files_in_folder(email_path, model, connector, systemPrompt, json_template)

    connector.close()

if __name__ == "__main__":
    main()
