from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential, TokenCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.core.credentials import AzureKeyCredential
 
# Replace these values with your actual Key Vault URL and secret name
keyvault_url = "https://<vaultname>.vault.azure.net/"
secret_name = "secretname"
 
# Create a SecretClient using Azure Identity credentials
credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
token = credential.get_token("https://vault.azure.net/.default")
# print("token", token)
client = SecretClient(vault_url=keyvault_url, credential=credential)
 
# Retrieve the secret value
secret = client.get_secret(secret_name)
cognitive_search_key = secret.value
 
print(f"Cognitive Search Key: {cognitive_search_key}")

credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
token = credential.get_token("https://cognitiveservices.azure.com/.default")
endpoint = "https://<cogsearchname>.search.windows.net/"
index_name = "<indexname>"
print(token.token)
client = SearchIndexClient(endpoint=endpoint, index_name=index_name, credential=credential)
client = SearchIndexClient(endpoint=endpoint, credential=AzureKeyCredential(cognitive_search_key))
index = SearchIndex(
    name=index_name,
    fields=[
        {"name": "page_no", "type": "Edm.String", "key": True, "filterable": True},
        {"name": "id", "type": "Edm.String", "filterable": True},
        {"name": "text", "type": "Edm.String", "searchable": True, "sortable": True},
        # Add more fields as needed
    ]
)
client.create_index(index)
print("index created")

import fitz  # PyMuPDF
 
def extract_text_from_pdf(pdf_path):
    pdf_document = fitz.open(pdf_path)
    text_data = []
 
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        text_data.append({"page_no": str(page_num+1), "text": text+str({"metadata":[{"page_no":str(page_num+1),"filename":"file1"}]})})
 
    return text_data

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
 
search_service_name = "cogsearchname"

 
endpoint = f"https://{search_service_name}.search.windows.net/"
admin_key = AzureKeyCredential(cognitive_search_key)
client = SearchClient(endpoint=endpoint, index_name=index_name, credential=admin_key)
 
documents = extract_text_from_pdf(r"sample.pdf")
print(documents) 
result = client.upload_documents(documents)
print(f"Uploaded documents")


# from azure.search.documents import SearchClient
# from azure.identity import DefaultAzureCredential
# credential = DefaultAzureCredential(exclude_managed_identity_credential=True)
# token = credential.get_token("https://cognitiveservices.azure.com/.default")
# endpoint = "https://nassurancesearchuse2.search.windows.net/"
# search_client = SearchClient(endpoint=endpoint,index_name=index_name,credential=credential)
# search_text = "Gross direct (Scope 1) GHG emissions in metric tons of CO2 equivalent"
# results = search_client.search(search_text=search_text)
# for result in results:
#     print(result)
    
    
import os
import openai
import dotenv
import requests
dotenv.load_dotenv()
import re
import json
import ast
from django.conf import settings

def get_openai_credentials():
    """
    The function `get_openai_credentials` retrieves OpenAI credentials from a JSON configuration file
    and returns the API key, base URL, API type, and API version.
    :return: The function `get_openai_credentials()` returns the following values:
    """
    from azure import identity
    import importlib
    importlib.reload(identity)

    credential = identity.DefaultAzureCredential(exclude_managed_identity_credential=True)
    token = credential.get_token("https://cognitiveservices.azure.com/.default")

    openai.api_type = "azuread"
    openai.api_key = token.token
    openai.api_base = "https://<openainame>.openai.azure.com/"
    openai.api_version = "2023-03-15-preview"

    return openai.api_key, openai.api_base, openai.api_type, openai.api_version
def setup_byod(deployment_id: str) -> None:
    """Sets up the OpenAI Python SDK to use your own data for the chat endpoint.
    :param deployment_id: The deployment ID for the model to use with your own data.
    To remove this configuration, simply set openai.requestssession to None.
    """
    class BringYourOwnDataAdapter(requests.adapters.HTTPAdapter):
     def send(self, request, **kwargs):
         request.url = f"{openai.api_base}/openai/deployments/{deployment_id}/extensions/chat/completions?api-version={openai.api_version}"
         return super().send(request, **kwargs)
    session = requests.Session()
    # Mount a custom adapter which will use the extensions endpoint for any call using the given `deployment_id`
    session.mount(
        prefix=f"{openai.api_base}/openai/deployments/{deployment_id}",
        adapter=BringYourOwnDataAdapter()
    )
    openai.requestssession = session 

def openai_suggestion_main(requirement_desc,file_uq_name):
    openai.api_key, openai.api_base, openai.api_type, openai.api_version = get_openai_credentials()
    openai.api_version = "2023-08-01-preview"
    aoai_deployment_id = "gpt-4-32k-0613"
    setup_byod(aoai_deployment_id)
    query = requirement_desc
    req_id = "111"
    formating = """The output should be a markdown code snippet formatted in the following schema, including the leading and trailing "```json" and "```":

            ```json
           {
                "generated_answer": string /AI generated answer by following below steps,
                "Citations": [```{
                'citation': string /Exact sentence from context which is used to get or generate the answer
                'page_no': integer /page no of citation
                }```] /list of dictionary
            }
            ```"""
    prompt_answer_gen = f"""
            requirement_description:{query}
            
            ### Instruction  ###
            -Strictly do not provide any explanation or justification.
            -Do not provide any junk data in the response.
            -Follow the below steps in sequential order. 
            -Response should strictly follow the below format.

            Response Format:
            {formating}

            Step 1: Convert the above provided requirement_description into question.
            Step 2: Answer the generated question with the best relevant context with above mentioned format.           
            
    """
    print(f"index-{file_uq_name}")
    completion = openai.ChatCompletion.create(
        messages=[ {"role": "system", "content": "You are an useful assitent to provide me the answer for given question and possible citation with exact sentence"},
            {"role": "user", "content": prompt_answer_gen}
            ],
        deployment_id="gpt-4-32k-0613",
        dataSources=[
            {
                "type": "AzureCognitiveSearch",
                "parameters": {
                    "endpoint": "https://<cogsearchname>.search.windows.net/",
                    "key": "<cogsearchkey>",
                    "indexName": index_name,
                }
            }
        ]
    )
    print(completion)
    return completion

completion_result = openai_suggestion_main("Name of the organaization","test")

print(completion_result)
print(completion_result["choices"][0]["message"]["content"])