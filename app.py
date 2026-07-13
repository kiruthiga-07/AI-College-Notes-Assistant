import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

st.set_page_config(page_title="AI Notes Assistant", layout="centered")

# --- Security ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    st.error("Please add GOOGLE_API_KEY in Streamlit Secrets.")
    st.stop()

st.title("🎓 AI College Notes Assistant")
uploaded_file = st.file_uploader("Upload your lecture notes (PDF)", type="pdf")

if uploaded_file:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.spinner("Processing..."):
        loader = PyPDFLoader("temp.pdf")
        data = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        docs = text_splitter.split_documents(data)
        
        # Change the model string to this:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004", google_api_key=api_key)
        vectorstore = FAISS.from_documents(docs, embeddings)
    
    st.success("Notes indexed!")

    query = st.text_input("Ask a question:")
    if query:
        # Retrieve relevant chunks
        docs_relevant = vectorstore.similarity_search(query, k=3)
        context_text = "\n\n".join([d.page_content for d in docs_relevant])
        
        # Direct Prompting
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        prompt = f"Use the following context to answer the question. Context: {context_text} \n\n Question: {query}"
        
        response = llm.invoke(prompt)
        st.write("### Answer:")
        st.write(response.content)
