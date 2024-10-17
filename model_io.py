import sys
import logging
import embeddings_ctrl as ec
import ollama
import chromadb
import config

# Load settings from configuration file.
DEFAULT_SETTINGS_FILE = 'models.cfg'
cfg = config.Config(DEFAULT_SETTINGS_FILE)
EMBED_MODEL = cfg["embedmodel"]
MAIN_MODEL = cfg["mainmodel"]
USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
PRINT_CONTEXT = cfg['print_context']


def get_collection(collection_name: str = None) -> chromadb.Collection:
    """
    Creates and returns a Chroma collection. Collection contains reference
    documents and corresponding embeddings.

    Returns:
        chromadb.Collection: A Chroma collection.
    """

    chroma = chromadb.HttpClient(host="localhost", port=8000)
    collection = chroma.get_or_create_collection(collection_name)
    return collection


def build_prompt(user_query: str, rag_context: str) -> str:
    """Build prompt for LLM model."""

    prompt = BASE_FOR_PROMPT.replace('<user_query>', user_query)
    prompt = prompt.replace('<rag_context>', rag_context)

    #prompt = prompt.replace('<conversation_history>', ' '.join(flat_book))
    #logging.info('conversation_book: %s', conversation_book)
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
    return context


def log_rag_context(user_query: str, rag_context: str) -> None:

    if PRINT_CONTEXT is True:
        msg = ("\n----------------------Request-------------------------\n"
                     f"{user_query}"
                     "\n----------------------Context begin-------------------\n"
                     f"docs: {rag_context}"
                     "\n----------------------Context end---------------------\n")
        logging.info(msg)
    else:
        logging.info("Skipping printing context.")


def build_flat_book(user_query: str, prompt: str,
                    history_book: list[str]) -> list[str]:
    """ Build flat book."""
    flat_book = []
    for question, answer in history_book:
        flat_book.append(question)
        flat_book.append(answer)
    main_phrase = {
                   'role': 'user',
                   'content': user_query,
                   'prompt': prompt
                  }
    flat_book.append(main_phrase)
    logging.info("flat book %s", flat_book)
    logging.info("flat book size (bytes): %s", sys.getsizeof(flat_book))
    return flat_book


def get_answer(user_query: str, config_file: str,
               history_book: list[str]) -> str:
    """ Make single answer."""

    query = user_query
    rag_context = get_rag_context(query, config_file)
    if len(rag_context) == 0:
        log.info("RAG context is empty fo query: %s", query) 
     
    prompt = build_prompt(query, rag_context)
    log_rag_context(query, rag_context)
    flat_book = build_flat_book(query, prompt, history_book)

    if USE_CHAT is True:
        logging.info('<chat> mode')
        NUM_CTX = 4096 #2048
        opt = {"num_ctx": NUM_CTX}
        response = ollama.chat(model=MAIN_MODEL, messages=flat_book,
                                options=opt)
        res = response['message']['content']
    else:
        logging.info('<generate mode> mode')
        stream = ollama.generate(model=MAIN_MODEL, prompt=prompt,
                                 stream=True)
        res = ''
        for chunk in stream:
            if chunk["response"]:
                res += chunk['response']
    logging.info(res)
    return res


def main():
    """
    The main function.
    """

    run_flag = True
    logging.info("%s", f'Embedding model: {EMBED_MODEL}')
    logging.info("%s", f'Main model: {MAIN_MODEL}')

    logging.info('\nAssistant for bike Suzuki Djebel 200 service is running.\n'
                 'Enter your question or type "q" to exit.\n')

    if EMBED_MODEL == 'navec':
        logging.info('Navec embeddings selected.\nType questions in Russian.\n')

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
                ])

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
