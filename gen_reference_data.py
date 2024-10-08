import embeddings_ctrl as ec
import os
import ollama, chromadb, time
from mattsollamatools import chunk_text_by_sentences
import config
from os import listdir
from os.path import isfile, join


# Load settings from configuration file.
cfg = config.Config('models.cfg')
EMBED_MODEL = cfg["embedmodel"]
COLLECTION_NAME = cfg['collection_name']
REF_DOCS_PATH = cfg['reference_docs_path']
BEGIN_TAG = cfg['begin_tag']
CHUNKING = cfg['chunking']  


def chunk_text_by_tags(
        source_text, tag_of_begin: str, tag_of_end: str = '',
        overlap: int = 0) -> list[str]:

    data = source_text.split(tag_of_begin)
    cleaned_data = [item for item in data if item]
    return cleaned_data


def build_collection() -> int:
    chroma = chromadb.HttpClient(host="localhost", port=8000)
    print(chroma.list_collections())
    if any(
        collection.name == COLLECTION_NAME
        for collection in chroma.list_collections()
    ):
        print("deleting collection")
        chroma.delete_collection(COLLECTION_NAME)
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    print(f'{EMBED_MODEL} embeddings selected.')

    files = [f for f in listdir(REF_DOCS_PATH) if isfile(join(REF_DOCS_PATH, f))]
    text = ''
    chunks_counter = 0
    for path in files:
        if not path.endswith(".txt"):
            continue
        relative_path = REF_DOCS_PATH + '/' + path
        filename = os.path.abspath(relative_path)
        print(f"\nDocument: {filename}")
        with open(filename, "rb") as f:
            text = f.read().decode("utf-8")

        if CHUNKING == 'by_sentences':
            chunks = chunk_text_by_sentences(
                source_text=text, sentences_per_chunk=7, overlap=0)
        elif CHUNKING == 'by_tags':
            chunks = chunk_text_by_tags(
                source_text=text, tag_of_begin=BEGIN_TAG)
        else:
            raise Exception(
                f"CHUNKING must be 'by_sentences' or 'by_tags', not {CHUNKING}"
            )

        print(f"{len(chunks)} chunks")
        for ch in chunks:
            print(ch)
            print('\n------------------------')
        chunks_counter += len(chunks)
        for index, chunk in enumerate(chunks):
            if EMBED_MODEL == "navec":
                embed = ec.navec_embeddings(chunk)["embedding"]
            else:
                embed = ollama.embeddings(model=EMBED_MODEL, prompt=chunk)[
                    "embedding"
                ]
            print(".", end="", flush=True)

            collection.add(
                [filename + str(index)],
                [embed],
                documents=[chunk],
                metadatas={"source": filename},
                )
    return chunks_counter

start_time = time.time()
chunks = build_collection()
print(f"\n{chunks} chunks found.")
print(f"\n--- {time.time() - start_time} seconds ---")
