import streamlit as st
import pandas as pd
from PIL import Image
import os
st.title("FootpathFix Bengaluru")

tab1, tab2=st.tabs(["Report Obstruction","Public Dashboard"])

# citizen reporting tab
with tab1:
    st.header("Report a Foothpath Blockage")
    uploaded_file=st.file_uploader("Upload Obstruction Photo",type=["jpg","jpeg","png"])
    category = st.selectbox("Obstruction Type", ["Construction Debris", "Illegal Parking", "Garbage Dumping", "Broken Pavement", "Vendor Encroachment","Others"])
    description = st.text_area("Additional Details / Landmark")
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Evidence", use_column_width=True)
        if st.button("Submit Report"):
            # Save report to a local CSV file as a simple prototype database
            new_data = pd.DataFrame([{
                "Category": category,
                "Description": description,
                "Status": "Pending",
                "Image": uploaded_file.name
            }])
            
            if os.path.exists("reports.csv"):
                new_data.to_csv("reports.csv", mode='a', header=False, index=False)
            else:
                new_data.to_csv("reports.csv", index=False)
                
            st.success("Report submitted successfully! Routed to GBA local ward.")
    # tab for dashboard
    with tab2:
        st.header("Pending & Completed Works")
            
        if os.path.exists("reports.csv"):
            df = pd.read_csv("reports.csv")
                
            # Metrics summary
            total = len(df)
            pending = len(df[df["Status"] == "Pending"])
            completed = len(df[df["Status"] == "Resolved"])
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Reports", total)
            col2.metric("Pending", pending)                            
            col3.metric("Resolved", completed)                            
                            
            st.dataframe(df                )
        else:
            st.info("No reports submitted yet. Be the first to report an obstruction!")
                
                