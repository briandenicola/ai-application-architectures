import os
import sys
import openai
from datetime import datetime

from langchain_community.document_loaders.parsers.audio import AzureOpenAIWhisperParser
from langchain_core.documents.base import Blob

config = {
    "name": "whisper",
    "version": "2024-06-01",
    "key": os.environ['AZURE_OPENAI_API_KEY'],
    "endpoint": os.environ['AZURE_OPENAI_ENDPOINT'],
}

def main():
    if len(sys.argv) != 2:
        print("Usage: python transcribe.py <path_to_audio_file>")
        sys.exit(1)

    audio_path = sys.argv[1]
    audio_blob = Blob(path=audio_path)

    parser = AzureOpenAIWhisperParser(
        api_key=config["key"], azure_endpoint=config["endpoint"], api_version=config["version"], deployment_name=config["name"]
    )

    print(f"Transcribing {audio_path} using Azure OpenAI Whisper Parser...")

    documents = parser.lazy_parse(blob=audio_blob)
    for doc in documents:
        print(doc.page_content)
    
    
if __name__ == "__main__":
    main()