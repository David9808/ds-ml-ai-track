import streamlit as st
import pandas as pd
import re
from llm import handle_query
from execute import execute_generated_code
import io

# Streamlit UI
st.set_page_config(page_title="Do It Yourself", page_icon="cropped_image.png")
st.title("DIY Analytics")

uploaded_file = st.file_uploader("Upload your CSV, EXCEL, TXT or JSON data set to get started!", type=["csv", "xlsx", "json","txt"])


if uploaded_file:
    file_extension = uploaded_file.name.split('.')[-1].lower()

    if file_extension == "csv":
        data = pd.read_csv(uploaded_file)

    elif file_extension == "json":
        data = pd.read_json(uploaded_file)

    elif file_extension == "xlsx":
        data = pd.read_excel(uploaded_file)  

    elif file_extension == "txt":
        try:
            lines = uploaded_file.getvalue().decode('utf-8').splitlines()
            raw = []
            date_pattern = r'\d+/\d+/\d+'  

            for line in lines:
                line = line.strip()
                match = re.search(r'(\d+/\d+/\d+),[\s\u202f]*(\d{1,2}:\d{2}[\s\u202f]*[AP]M)\s*-\s*([^:]*):\s*(.*)', line)

                if match:
                    raw.append([match.group(1), match.group(2), match.group(3), match.group(4).replace(",", " ")])
                elif raw and not re.match(date_pattern, line):
                    raw[-1][-1] += " " + line.replace(",", " ")

            data = pd.DataFrame(raw, columns=['Date', 'Time', 'Identifier', 'Content'])

        except Exception:
            print("Unsupported file format: Please upload a timestamped log file")
    
    else: 
        st.error(f"Unsupported file format: {file_extension}. Please upload a CSV, XLSX, or JSON file")
    
    st.write("#### Data Preview")
    st.dataframe(data.head())

    if st.checkbox("Show Data Summary"):
        missing_values, duplicated_values, num_statistics,cat_statistics  = st.tabs(["Missing Values", "Duplicated Values", "Summary Statistics(Numerical)","Summary Statistics(Categorical)"])
        total_missing_values_by_column = data.isnull().sum()
        missing_values.write(total_missing_values_by_column)
        missing_values.write(f"There are {total_missing_values_by_column.sum()} missing values in your dataset.")

        total_duplicated_values_by_column = data.duplicated().sum()
        duplicated_values.write(total_duplicated_values_by_column)
        duplicated_values.write(f"There are {total_duplicated_values_by_column.sum()} duplicated values in your dataset.")

        num_statistics.write("#### Summary Statistics")
        num_statistics.dataframe(data.describe())

        cat_statistics.write("#### Summary Statistics")
        cat_statistics.dataframe(data.describe(include=['object']))

    st.header("Chat with your data!")
    user_query = st.text_input("Ask a question about your dataset:")
    send, retry = st.columns(2)

    with send:
        send_button = st.button("Send")
    with retry:
        retry_button = st.button("Retry")


    with st.spinner("Insights cooking..."):
        if user_query or send_button or retry_button:
            code = handle_query(user_query, data)

            try:
                results, output = execute_generated_code(code, data)

                if output:
                    st.write(output)

                # Handle Matplotlib chart
                if "plt" in results:
                    st.pyplot(results["plt"].gcf())  

                # Handle string results (errors or other outputs)
                if isinstance(results, str): 
                    st.error(results)
                else:
                    st.toast("Code executed successfully.")
                    
            except Exception as e:
                st.error(f"Error executing code: {e}")

           # Optionally display the generated code
            if st.checkbox("Show code"):
                st.code(code, language="python")

            if st.checkbox("Download chart"):
                    format_options = ["PNG", "JPEG", "HTML"]
                    selected_format = st.selectbox("Select format:", format_options)

                    # Generate chart file in selected format
                    if selected_format in ["PNG", "JPEG"]:
                        buf = io.BytesIO()
                        results["plt"].savefig(buf, format=selected_format.lower())
                        buf.seek(0)
                        st.download_button(
                            label=f"Download Chart as {selected_format}",
                            data=buf,
                            file_name=f"chart.{selected_format.lower()}",
                            mime=f"image/{selected_format.lower()}",
                        )
                    elif selected_format == "HTML":
                        from matplotlib.backends.backend_svg import FigureCanvasSVG
                        buf = io.StringIO()
                        FigureCanvasSVG(results["plt"].gcf()).print_svg(buf)
                        html_content = f"<html><body>{buf.getvalue()}</body></html>"
                        st.download_button(
                            label="Download Chart as HTML",
                            data=html_content,
                            file_name="chart.html",
                            mime="text/html",
                        )
