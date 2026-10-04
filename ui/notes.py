"""notes.py - upload your own notes and ask questions answered only from them."""
import streamlit as st

from core import ai, config, retrieval
from core import database as db
from ui.common import show_ai_error


def render(user: dict):
    uid = user["id"]
    st.title("My notes")
    st.write("Upload notes (.txt, .md or text-based .pdf). Aura finds the matching passages and "
             "answers using only those.")

    with st.form("upload_form", clear_on_submit=True):
        file = st.file_uploader("Choose a file", type=["txt", "md", "pdf"])
        submitted = st.form_submit_button("Add to my notes")
    if submitted:
        if file is None:
            st.warning("Please choose a file first.")
        elif file.size > config.MAX_UPLOAD_MB * 1024 * 1024:
            st.error(f"That file is larger than {config.MAX_UPLOAD_MB} MB.")
        else:
            try:
                text = retrieval.extract_text(file.name, file.getvalue())
                chunks = retrieval.chunk_text(text)
                if not chunks:
                    st.error("That file has no text in it.")
                else:
                    db.add_document(uid, file.name, chunks)
                    st.success(f"Added {file.name} ({len(chunks)} passages).")
            except ValueError as exc:
                st.error(str(exc))

    docs = db.list_documents(uid)
    if docs:
        st.subheader("Your files")
        for doc in docs:
            left, right = st.columns([4, 1])
            left.write(doc["filename"])
            right.button("Delete", key=f"deldoc_{doc['id']}",
                         on_click=db.delete_document, args=(uid, doc["id"]))

    st.subheader("Ask your notes")
    with st.form("notes_question"):
        question = st.text_input("Your question")
        asked = st.form_submit_button("Ask")
    if asked:
        if not question.strip():
            st.warning("Please type a question.")
        elif not docs:
            st.warning("Upload a file first.")
        else:
            best = retrieval.top_chunks(question, db.get_all_chunks(uid), k=4)
            if not best:
                st.info("I found no matching passage in your notes. Try different keywords.")
            else:
                try:
                    with st.spinner("Reading your notes..."):
                        answer = ai.answer_from_notes(question.strip(), best, user)
                    st.markdown(answer)
                    with st.expander("Passages used"):
                        for i, chunk in enumerate(best, 1):
                            st.markdown(f"**[{i}] {chunk['filename']}**")
                            st.write(chunk["text"])
                except ai.AIError as exc:
                    show_ai_error(exc)
