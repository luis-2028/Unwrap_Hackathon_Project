import os
import json, ndjson
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

load_dotenv()

# CONSTANTS
INPUT_FILE = "test.ndjson" #FILTERED ONLY PLZZZ

OPENAI_MODEL = "text-embedding-3-small"
VECTOR_DIM = 1536
EMBEDDING_BATCH_SIZE = 150

# KEYS
openai_key = os.getenv("paid_key")
pinecone_key = os.getenv("pinecone_key")

openai_client = OpenAI(api_key=openai_key)


try:
    cred = credentials.Certificate("semanticdissonance-firebase-adminsdk-fbsvc-6f5e815074.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK initialized successfully.")
except FileNotFoundError:
    print("Error: serviceAccountKey.json not found. Please provide the correct path.")
    print("Download it from Firebase Console -> Project settings -> Service accounts -> Generate new private key.")
    exit()
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")
    exit()

# Define your collection name
collection_name = 'memes'


# PINECONE SETUP
pc = Pinecone(api_key=pinecone_key)
index_name = "meme-index"
if not pc.has_index(index_name):
    print(f"Creating Pinecone index '{index_name}' (serverless: aws/us-east-1)...")
    pc.create_index(name=index_name, 
                    dimension=VECTOR_DIM, 
                    metric="cosine", 
                    spec= ServerlessSpec(cloud="aws", region="us-east-1")
                    )
index = pc.Index(index_name)

doc_ids = []

with open(INPUT_FILE, "r") as in_file:
    data = ndjson.load(in_file)
    for row in data:
        new_url = row['url']

        # 2. Perform a Create Operation with an auto-generated ID
        try:
            # When you call .add() with just the data, Firestore automatically generates a unique document ID.
            doc_ref = db.collection(collection_name).add({
                'url': new_url
            })

            # Access and print the auto-generated ID
            document_id = doc_ref[1].id # doc_ref is a tuple: (update_time, document_reference)
            print(f"\nSuccessfully added URL: '{new_url}'")
            print(f"Auto-generated Document ID: {document_id}")
            doc_ids.append(document_id)




        except Exception as e:
            print(f"Error adding document to Firestore: {e}")



    print("\nGenerating embeddings...")
    for i in range(0, len(data), EMBEDDING_BATCH_SIZE):
        ids = doc_ids[i:(i+EMBEDDING_BATCH_SIZE)]
        embeddings = openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[row['text'] for row in data[i:i+EMBEDDING_BATCH_SIZE]]
        ).data

        assert(len(embeddings) == len(doc_ids[i:(i+EMBEDDING_BATCH_SIZE)]))
        vectors = [{"id": doc_id, "values":e.embedding} 
                    for (e, doc_id) in zip(embeddings, doc_ids[i:(i+EMBEDDING_BATCH_SIZE)])]
 
        print(f"Upserting from idx {i} to {i+EMBEDDING_BATCH_SIZE}, a total of {len(vectors)} vectors...")
        index.upsert(
            vectors=vectors, #namespace= needed?
        ) 


