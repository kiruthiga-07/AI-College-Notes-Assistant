import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain

st.set_page_config(page_title="AI Notes Assistant", layout="centered")

st.title("🎓 AI College Notes Assistant")
st.sidebar.header("Configuration")
api_key = st.sidebar.text_input("Enter your Google Gemini API Key", type="password")

uploaded_file = st.file_uploader("Upload your lecture notes (PDF)", type="pdf")

if uploaded_file and api_key:
    # Save uploaded file temporarily
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # 1. Load and Split
    loader = PyPDFLoader("temp.pdf")
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs = text_splitter.split_documents(data)
    
    # 2. Embed and Store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vectorstore = FAISS.from_documents(docs, embeddings)
    
    st.success("Notes processed! You can now ask questions.")

    # 3. Chat Interface
    query = st.text_input("Ask a question about your notes:")
    if query:
        # Use the modern Retrieval Chain
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        
        # Define a prompt template
        prompt = ChatPromptTemplate.from_template("""
        Answer the following question based only on the provided context:
        <context>
        {context}
        </context>
        Question: {input}
        """)
        
        # Create chains
        combine_docs_chain = create_stuff_documents_chain(llm, prompt)
        retriever = vectorstore.as_retriever()
        retrieval_chain = create_retrieval_chain(retriever, combine_docs_chain)
        
        # Invoke
        response = retrieval_chain.invoke({"input": query})
        
        st.write("### Answer:")
        st.write(response["answer"])
