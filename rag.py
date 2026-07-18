from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import os


embedding = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-mpnet-base-v2"
)


def create_vectorstore(
    pdf_path,
    user_id,
    thread_id
):

    try:

        # Load PDF
        loader = PyPDFLoader(pdf_path)

        docs = loader.load()

        print("PDF pages loaded:", len(docs))


        # Check PDF
        if not docs:

            print("ERROR: PDF contains no pages.")

            return False


        # Remove empty pages
        docs = [
            doc
            for doc in docs
            if doc.page_content
            and doc.page_content.strip()
        ]


        print(
            "Pages containing text:",
            len(docs)
        )


        # If PDF has no extractable text
        if not docs:

            print(
                "ERROR: PDF contains no extractable text."
            )

            return False


        # Split documents
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )


        chunks = splitter.split_documents(
            docs
        )


        # Remove empty chunks
        chunks = [
            chunk
            for chunk in chunks
            if chunk.page_content
            and chunk.page_content.strip()
        ]


        print(
            "Chunks created:",
            len(chunks)
        )


        # IMPORTANT:
        # Prevent FAISS embeddings[0] error
        if not chunks:

            print(
                "ERROR: No text chunks were created."
            )

            return False


        # Create FAISS
        db = FAISS.from_documents(
            chunks,
            embedding
        )


        # User + thread specific path
        save_path = os.path.join(
            "vectorstore",
            str(user_id),
            str(thread_id)
        )


        os.makedirs(
            save_path,
            exist_ok=True
        )


        # Save vector database
        db.save_local(
            save_path
        )


        print(
            "Vectorstore created:",
            save_path
        )


        return True


    except Exception as e:

        print(
            "CREATE VECTORSTORE ERROR:",
            repr(e)
        )

        return False


def get_retriever(user_id, thread_id):

    db = FAISS.load_local(

        os.path.join(
            "vectorstore",
            str(user_id),
            thread_id
        ),

        embedding,

        allow_dangerous_deserialization=True

    )

    return db.as_retriever(
        search_kwargs={"k": 4}
    )


def vectorstore_exists(user_id, thread_id):

    return os.path.exists(

        os.path.join(
            "vectorstore",
            str(user_id),
            thread_id
        )

    )