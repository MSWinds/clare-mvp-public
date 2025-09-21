import streamlit as st

st.title("Hello Streamlit!")
st.write("This is a minimal test app.")

if st.button("Click me"):
    st.write("Button clicked!")

st.write("Current time:", st.empty())
