import firebase_admin
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
import os
from openai import OpenAI
from pinecone import ServerlessSpec
from pinecone.grpc import PineconeGRPC, GRPCClientConfig
from pinecone import ServerlessSpec


class MemeGenerator:
    def __init__(self):
        load_dotenv()
        openai_key = os.getenv("paid_key")
        pinecone_key = os.getenv("pinecone_key")
        self.firebase_init()
        self.openai_init(openai_key)
        self.pinecone_init(pinecone_key)
    
    def firebase_init(self):
        self.collection_name = "memes"
        try:
            self.cred = credentials.Certificate("semanticdissonance-firebase-adminsdk-fbsvc-6f5e815074.json")
            firebase_admin.initialize_app(self.cred)
            self.db = firestore.client()
            print("Firebase Admin SDK initialized successfully.")
        except FileNotFoundError:
            print("Error: serviceAccountKey.json not found. Please provide the correct path.")
            print("Download it from Firebase Console -> Project settings -> Service accounts -> Generate new private key.")
            exit()
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            exit()
    
    def openai_init(self, key):
        self.openai_client = OpenAI(api_key=key)

    def pinecone_init(self, key):
        self.pinecone_client = PineconeGRPC(api_key=key)
        self.index_name = "meme-index"
        assert(self.pinecone_client.has_index(self.index_name))
        self.index = self.pinecone_client.Index(self.index_name)

    def generate_best(self, query: str) -> str:
        """returns a URL of the best meme for a query"""
        query_vec = self.openai_client.embeddings.create(
                        model="text-embedding-3-small",
                        input=[query] ).data[0].embedding
        result = self.index.query(vector=query_vec, top_k=1, 
                                  include_values=False, 
                                  include_metadata=False).matches[0]
        best_ref = self.db.collection(self.collection_name).document(result.id)
        return best_ref.get().get("url")

    

if __name__=="__main__":
    gen = MemeGenerator()
    x = input("Enter a prompt: ")
    while x:
        print(gen.generate_best(x))
        x = input("Enter a prompt: ")