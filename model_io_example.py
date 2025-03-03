import sys
import logging as log
import embeddings_ctrl as ec
import ollama
import chromadb
from chromadb.types import SegmentScope
import config
import gc
import os
import psutil

# Load settings from configuration file.
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
EMBED_MODEL = cfg["embedmodel"]
MAIN_MODEL = cfg["mainmodel"]
USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
PRINT_CONTEXT = cfg['print_context']
CHROMA_PORT = cfg['chroma_port']

opt = {"temperature": 0.4}

def bytes_to_gb(bytes_value):
    return bytes_value / (1024 ** 3)


def get_process_info():
    pid = os.getpid()
    p = psutil.Process(pid)
    with p.oneshot():
        mem_info = p.memory_info()
        # disk_io = p.io_counters()
    return {
        "memory_usage": bytes_to_gb(mem_info.rss),
    }


def unload_index(collection_name: str, chroma_client: chromadb.PersistentClient):
    """
    Unloads binary hnsw index from memory and removes both segments (binary and metadata) from the segment cache.
    """
    collection = chroma_client.get_collection(collection_name)
    collection_id = collection.id
    #segment_manager = chroma_client._server._manager
    segment_manager = chroma_client._server.chroma_segment_manager_impl
    for scope in [SegmentScope.VECTOR, SegmentScope.METADATA]:
        if scope in segment_manager.segment_cache:
            cache = segment_manager.segment_cache[scope].cache
            if collection_id in cache:
                segment_manager.callback_cache_evict(cache[collection_id])
    gc.collect()


def get_collection(collection_name: str = None) -> chromadb.Collection:
    """
    Creates and returns a Chroma collection. Collection contains reference
    documents and corresponding embeddings.

    Returns:
        chromadb.Collection: A Chroma collection.
    """

    chroma = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    collection = chroma.get_or_create_collection(collection_name)
    return collection


def free_mem_collection(collection_name: str = None) -> None:
    """
    Free memory from a Chroma collection.

    Args:
        collection_name (str, optional): Name of the Chroma collection. Defaults to None.
    """

    chroma_client = chromadb.HttpClient(host="localhost", port=CHROMA_PORT)
    unload_index(collection_name, chroma_client)


def build_prompt(rag_context: str) -> str:
    """Build prompt for LLM model."""

    #prompt = BASE_FOR_PROMPT.replace('<user_query>', user_query)
    prompt = BASE_FOR_PROMPT
    prompt = prompt.replace('<rag_context>', rag_context)

    #prompt = prompt.replace('<conversation_history>', ' '.join(flat_book))
    #log.info('conversation_book: %s', conversation_book)
    return prompt


def get_rag_context(query: str, config_file: str) -> str:
    """Get reference text."""

    cfg = config.Config(config_file)
    global EMBED_MODEL
    EMBED_MODEL = cfg["embedmodel"]
    global MAIN_MODEL
    MAIN_MODEL = cfg["mainmodel"]
    global USE_CHAT
    USE_CHAT = cfg['use_chat']
    global COLLECTION_NAME
    COLLECTION_NAME = cfg['collection_name']
    global PRINT_CONTEXT
    PRINT_CONTEXT = cfg['print_context']
    global BASE_FOR_PROMPT
    BASE_FOR_PROMPT = cfg['base_for_prompt']
    global CHROMA_PORT
    CHROMA_PORT = cfg['chroma_port']

    collection = get_collection(COLLECTION_NAME)
    print('config:', config_file)
    print(collection)
    if EMBED_MODEL == 'navec':
        emb = ec.navec_embeddings(query)
    else:
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    queryembed = emb["embedding"]
    relevant_docs = collection.query(
        query_embeddings=[queryembed], n_results=5)["documents"][0]
    context = "\n\n".join(relevant_docs)
    # free_mem_collection(COLLECTION_NAME)

    log.info("RAG context size (bytes): %s", sys.getsizeof(context))
    return context


def log_rag_context(user_query: str, rag_context: str) -> None:

    if PRINT_CONTEXT is True:
        msg = ("\n----------------------Request-------------------------\n"
                     f"{user_query}"
                     "\n----------------------Context begin-------------------\n"
                     f"docs: {rag_context}"
                     "\n----------------------Context end---------------------\n")
        log.info(msg)
    else:
        log.info("Skipping printing context.")


def build_flat_book(user_query: str, prompt: str,
                    history_book: list[str]) -> list[str]:
    """ Build flat book."""
    sytem_msg = {
                 'role': 'system',
                 'content': prompt
                }
    flat_book = [sytem_msg]
    for question, answer in history_book:
        flat_book.append(question)
        flat_book.append(answer)
    main_phrase = {
                   'role': 'user',
                   'content': user_query
                  }
    flat_book.append(main_phrase)
    #log.info("flat book %s", flat_book)
    log.info("Flat book size (bytes): %s", sys.getsizeof(flat_book))
    return flat_book


def get_answer(user_query: str, config_file: str,
               history_book: list[str]) -> str:
    """ Make single answer."""

    log.info("History book size (bytes): %s", sys.getsizeof(history_book))
    query = user_query
    rag_context = get_rag_context(query, config_file)
    if len(rag_context) == 0:
        log.info("RAG context is empty fo query: %s", query)

    prompt = build_prompt(rag_context)
    log_rag_context(query, rag_context)
    flat_book = build_flat_book(query, prompt, history_book)

    if USE_CHAT is True:
        log.info('mode: <chat>')
        # NUM_CTX = 4096 #2048
        # opt = {"num_ctx": NUM_CTX}
        #response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt)
        if query == "Привет!":
            res = "Привет!" 
        else:    
            response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt )
            res = response['message']['content']
            low_res = res.lower()
            if ' бот' in low_res:
                res = "Мне не совсем понятен ваш вопрос."
            if ('языков' in low_res) and ('модел' in low_res):
                res = "Мне не совсем понятен ваш вопрос." 
            if ('искусственн' in low_res) and ('интеллек' in low_res):
                res = "Мне не совсем понятен ваш вопрос."
            #s = {"role": "user", "content": f'Напиши этот текст предложение в женском роде:"{res}"'}     
            #response = ollama.chat(model=MAIN_MODEL, messages=flat_book, options=opt )
    else:
        log.info('mode: <generate>')
        response = ollama.generate(model=MAIN_MODEL, prompt=f'{prompt}\n Ответь на вопрос:{query}')
        res = response["response"]

    log.info("Answer: %s", res)
    log.info("Answer size (bytes): %s", sys.getsizeof(res))
    return res


def main():
    """
    The main function.
    """

    run_flag = True
    log.info("%s", f'Embedding model: {EMBED_MODEL}')
    log.info("%s", f'Main model: {MAIN_MODEL}')

    log.info('\nAssistant for bike Suzuki Djebel 200 service is running.\n'
                 'Enter your question or type "q" to exit.\n')

    if EMBED_MODEL == 'navec':
        log.info('Navec embeddings selected.\nType questions in Russian.\n')

    answer_tag = ">>> "
    query_tag = "<<< "

    while run_flag is True:
        query = input(query_tag)
        if query.capitalize() != 'Q' and query.capitalize() != 'Й':
            context = get_rag_context(query, DEFAULT_SETTINGS_FILE)
            modelquery = build_prompt(query, context)
            log_rag_context(query, context)

            if USE_CHAT is True:
                response = ollama.chat(model=MAIN_MODEL, messages=[
                    {
                        'role': 'user',
                        'content': query,
                        'prompt': modelquery
                    },
                ], options=opt)

                print(response['message']['content'])
            else:
                stream = ollama.generate(model=MAIN_MODEL, prompt=modelquery,
                                         stream=True)
                print(f'{answer_tag} Thinking...', end="", flush=True)
                shift_back_cursor = True
                for chunk in stream:
                    if chunk["response"]:
                        if shift_back_cursor is True:
                            print(f'\r{answer_tag}', end="", flush=True)
                            shift_back_cursor = False
                        print(chunk["response"], end="", flush=True)

            print("\n")
        else:
            print("Exit.")
            run_flag = False


if __name__ == "__main__":
    main()
