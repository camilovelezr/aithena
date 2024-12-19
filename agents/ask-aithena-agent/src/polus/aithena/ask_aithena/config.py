"""Configuration for Ask Aithena Agent."""
from polus.aithena.common.logger import get_logger
import os
from dotenv import find_dotenv, load_dotenv

# Load the environment variables from the .env file in the folder hierarchy.
# The values from the .env file will override the system environment variables.
load_dotenv(find_dotenv(), override=True)

logger = get_logger(__name__)

AITHENA_SERVICE_URL = os.environ.get(
    "AITHENA_SERVICES_URL", default="http://localhost:31111"
)
CHAT_MODEL = os.environ.get("CHAT_MODEL", default="llama3.1:8b")
EMBED_MODEL = os.environ.get("EMBED_MODEL", default="nomic-embed-text")
TIMEOUT = int(os.environ.get("TIMEOUT") or "180")

EMBEDDING_TABLE = os.environ.get("EMBEDDING_TABLE", "openalex.nomic_embed_text_768")
SIMILARITY_N = int(os.environ.get("SIMILARITY_N", default=10))

logger.debug(f"Using Aithena service at {AITHENA_SERVICE_URL}")
logger.debug(f"Using chat model {CHAT_MODEL}")
logger.debug(f"Using embedding model {EMBED_MODEL}")
logger.debug(f"aithena services timeout {TIMEOUT}")
logger.debug(f"Using embedding table {EMBEDDING_TABLE}")
logger.debug(f"Using similarity n {SIMILARITY_N}")

CONTEXT_TAG = "context"
DOCUMENT_TAG = "doc"
TEXT_TAG = "text"
ID_TAG = "id"

SYSTEM_PROMPT = f"""
You are a helpful assistant that is provided documents to a question to answer.
Your entire answer should be in a conversational tone and use only the documents
to create your answer. Begin your answer with a short paragraph summarizing the
 documents.
In subsequent paragraphs, provide additional details from the documents that
support the summary answer. When a detail is referenced from the documents,
provide a numbered reference at the end of the sentence indicating which
document a statement is supported by. This numbered reference must correspond
to the order of the documents as they are provided to you.
If the documents do not help you answer the question, say that the documents
does not provide the information needed to answer the question.
Do not include a references section in your answer.
Documents will be provided below as a context.
Do not let users know that you are referring documents,
so do not mention things like 'According to document 1'.
Instead, just state the information and provide the reference number in parentheses.
Context will be enclosed in XML tags <{CONTEXT_TAG}>...</{CONTEXT_TAG}>.
Context will contain all the documents, each document will follow this format:
```
<{DOCUMENT_TAG}>
<{ID_TAG}>Document ID</{ID_TAG}>
<{TEXT_TAG}>Content of the document</{TEXT_TAG}>
</{DOCUMENT_TAG}>
```

Example:
<context>
<doc>
<id>6ab-gdfd</id>
<text>Dogs are great pets to have at home.</text>
</doc>
<doc>
<id>7cd-ab</id>
<text>Horses are not meant to be kept at home.</text>
</doc>
</context>
I am looking for a pet.

Good Response:
If you are looking for a pet, dogs are perfect since they
are great pets to have at home (1).
However, horses are not suitable for home environments (2).

CLARIFICATIONS:
NEVER cite documents by their id, like (6ab-gdfd).
I REPEAT, NEVER CITE DOCUMENTS BY THEIR ID.
Instead of writing something like: According to document 1,
AudioBERT is quite effective, achieving superior performance on the AuditoryBench.
You MUST write: AudioBERT is quite effective, achieving superior performance
on the AuditoryBench (1).
NEVER write: According to document 1... instead write: The Earth is not flat... (1).
"""
