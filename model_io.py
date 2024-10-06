import logging
import embeddings_ctrl as ec
import ollama
import chromadb
import config


# Load settings from configuration file.
cfg = config.Config('models.cfg')
EMBED_MODEL = cfg["embedmodel"]
MAIN_MODEL = cfg["mainmodel"]
USE_CHAT = cfg['use_chat']
COLLECTION_NAME = cfg['collection_name']
PRINT_CONTEXT = cfg['print_context']


def get_collection() -> chromadb.Collection:
    """
    Creates and returns a Chroma collection. Collection contains reference
    documents and corresponding embeddings.

    Returns:
        chromadb.Collection: A Chroma collection.
    """
    chroma = chromadb.HttpClient(host="localhost", port=8000)
    collection = chroma.get_or_create_collection(COLLECTION_NAME)
    return collection


def build_prompt(user_query: str, rag_context: str) -> str:
    """Build prompt for LLM model."""

    prompt_old = ("You consultant for motorbike 'Suzuki Djebel 200 service'"
              f"Answer in Russian to question:  {user_query}."
              " Every time point source, chapter number and page number"
              " where answer info was found."
              " Use as reference a following text from service manual:"
              f"{rag_context}"
              )
    prompt = ("You consultant for motorbike 'Suzuki Djebel 200 service'"
              f"Answer in Russian to question:  {user_query}."
              " Every time point source, chapter number and page number"
              " where answer info was found."
              " In anwer use point as a decimal separator in float point numbers."
              " Use as reference a following text from service manual:"
              f"{rag_context}"
              
              )              

    return prompt

def get_rag_context(query: str) -> str:
    """Get reference text."""

    collection = get_collection()
    if EMBED_MODEL == 'navec':
        emb = ec.navec_embeddings(query)
    else:
        emb = ollama.embeddings(model=EMBED_MODEL, prompt=query)
    queryembed = emb["embedding"]
    relevantdocs = collection.query(
        query_embeddings=[queryembed], n_results=5)["documents"][0]
    context = "\n\n".join(relevantdocs)
    return context


def make_answer(user_query: str) -> str:
    """ Make single answer."""

    query = user_query
    context = get_rag_context(query)
    modelquery = build_prompt(query, context)

    if PRINT_CONTEXT is True:
        msg = ("\n----------------------Request-------------------------\n"
               f"{query}"
               "\n----------------------Context begin-------------------\n"
               f"docs: {context}"
               "\n----------------------Context end---------------------\n")
        logging.info(msg)

    if USE_CHAT is True:
        response = ollama.chat(model=MAIN_MODEL, messages=[
            {
                'role': 'user',
                'content': query,
                'prompt': modelquery
            },
        ])

        res = response['message']['content']
    else:
        stream = ollama.generate(model=MAIN_MODEL, prompt=modelquery,
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
            context = get_rag_context(query)
            modelquery = build_prompt(query, context)
            if PRINT_CONTEXT is True:
                logging.info("%s",
                             "\n----------------------Request-------------------------\n"
                             f'{query}'
                             "\n----------------------Context begin-------------------\n"
                             f'{context}'
                             "\n----------------------Context end---------------------\n"
                             )

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
