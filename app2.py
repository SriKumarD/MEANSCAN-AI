from dotenv import load_dotenv
import os
import streamlit as st
from PIL import Image
import google.generativeai as genai
import openai
import re
import json
import pandas as pd
# Load environment variables
load_dotenv()

# Configure Google Gemini Pro Vision API and OpenAI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
openai_api_key = os.getenv('OPENAI_API_KEY')


# Function to recursively flatten a dictionary
def flatten_dict(d, parent_key='', sep=' '):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def wide_space_default():
    st.set_page_config(page_title="MealScan AI",layout='wide')

wide_space_default()



## Function to get response from Google Gemini Pro Vision API
def get_gemini_response(input_prompt, image):
    model = genai.GenerativeModel('gemini-pro-vision')
    response = model.generate_content([input_prompt, image[0]])
    return response.text

def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        # Read the file into bytes
        bytes_data = uploaded_file.getvalue()

        image_parts = [
            {
                "mime_type": uploaded_file.type,  # MIME type of the file
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")



st.header("MealScan AI")
col1, col2 = st.columns(2)

with col1:
   # Add user input fields
    age = st.number_input("Enter your age:", min_value=1, max_value=120,value=25)
    weight = st.number_input("Enter your weight in kilograms:", min_value=10.0, max_value=200.0,value=85.0)
    height_ft_in = st.text_input("Enter your height (feet,inches):", '5,7')
    hba1c = st.number_input("Enter your HbA1c level:", min_value=4.0, max_value=14.0, format="%.1f",value=5.0)
    uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])
    button = st.button('Get Calories Details')


if uploaded_file is not None and (button):
    image = Image.open(uploaded_file)
    st.sidebar.header("Uploaded Image")
    st.sidebar.image(image, caption="", use_column_width=True)



    input_prompt = """
    Imagine you are a renowned expert in identifying foods from images alone.
    People from all around the world send you pictures of various dishes, and you are able to
    determine what each dish is with remarkable accuracy. Guess the food size and portion be more catious.
    """


    image_data = input_image_setup(uploaded_file)
    gemini_response = get_gemini_response(input_prompt, image_data)
    system_message="""You are a nutrition expert tasked with extracting detailed nutritional information from provided text about a dish that contains multiple food items. Your task is to identify and sum up the values for calories, glycemic index, glycemic load, total sugars, carbohydrates, fiber, and fats for each food item in the dish. Then, provide the total amounts for each nutritional category in a structured JSON format
    
   Generate only json respose as Expected Output. Dont give any other text:
    {
    "item1": {
        "Calories": "total_calories_value",
        "Glycemic Index": "average_glycemic_index_value",  // Assuming an average might be more appropriate
        "Glycemic Load": "total_glycemic_load_value",
        "Total Sugars": "total_sugars_value",
        "Carbohydrates": "total_carbohydrates_value",
        "Fiber": "total_fiber_value",
        "Fats": "total_fats_value"
        "Carbohydrates": {
            "Simple": "10g",
            "Complex": "8g"
        }
    },
    ....
    "itemN": {
        "Calories": "total_calories_value",
        "Glycemic Index": "average_glycemic_index_value",
        "Glycemic Load": "total_glycemic_load_value",
        "Total Sugars": "total_sugars_value",
        "Carbohydrates": "total_carbohydrates_value",
        "Fiber": "total_fiber_value",
        "Fats": "total_fats_value"
        "Carbohydrates": {
            "Simple": "10g",
            "Complex": "8g"
        }
    },

    }

    
    """
    user_message=f"""The dish is {gemini_response}. Provide detailed nutritional data in json format includes calories, glycemic index, glycemic load, total sugars, carbohydrates, fiber, and fats."""

    client = openai.OpenAI(api_key=openai_api_key)
    response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_message.strip()},
                {"role": "user", "content": user_message.strip()}
            ],
            temperature=0
        )
        
    Food_Data = response.choices[0].message.content
    
    system_message= """

###Role: Food Advisory Expert

###Objective: Analyze user health metrics and dietary preferences to recommend suitable food choices.

###Details: As a food advisory expert, your role is to assess individual health profiles based on specific metrics such as age, height, weight, HbA1c levels. Utilizing this data, determine whether certain foods are advisable for consumption. Highlight the recommended dietary advice using HTML formatting for visual emphasis.
 
### A sugar patient can eat fruits and healthy food. 'good' sugars are found in healthy whole foods, while 'bad' sugars are commonly found in highly refined, processed foods. So If it is good sugar tell user that they can consume the food. Keep in mind about Glycemic Index in given data. But if the user health is good and hba1c is in healthy rage suggets them to consuem sugar.

###Instructions:



-Red Text (Health Caution): If either the user's BMI is outside the healthy range and their HbA1c levels are higher than 5.5, advise against the consumption of certain foods using red text to indicate a potential health risk. If it is fruits or healthy food suggest them to eat. Dont be too strong on sugar but tell based on meal health too.

        Example: <p style="color:red;">If a user's  HbA1c levels are high or mention BMI if not in healthy level. It is recommended to avoid {food iteam} which has high sugar intake. If not to suggest. Suggest only if user has bad bmi or hba1c</p>

-Green Text (Healthy Recommendation): If a user's BMI is between 18.5 to 24.9 and their HbA1c levels are within a healthy range less than 5.5, Must recommend the consumption of sugars in moderation. Display this advice in green text to signify a healthy choice. 

        Example: <p style="color:green;">Your BMI and HbA1c levels are within a healthy range. It is safe to consume {food iteam} in moderation.</p>
-General Advice: Provide a concise explanation focusing on how the food impacts specific health conditions, particularly HbA1c levels. If a food is suitable, suggest a daily consumption limit.

###Response Format: 
-Responses must be provided in a single paragraph, with HTML color coding for clarity. The advice should be practical and cautiously framed, taking into account both BMI and HbA1c levels. Other than text in color dont give any other text in resposne.

"""

    user_message =f"""
    please Analyse wheather i can consume food. Here are my details:
        User Profile:
        - Age: {age}
        - Weight: {weight}
        - Height (ft): {height_ft_in}
        - Latest HbA1c Level: {hba1c}

        Food Details:
        ```{Food_Data}```
    """


    response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": system_message.strip()},
                {"role": "user", "content": user_message.strip()}
            ],
            temperature=0
        )


    Summary = response.choices[0].message.content

    

    with col2:    
        st.subheader("Detailed Analysis")
        st.markdown(Summary, unsafe_allow_html=True)
        if Summary:
            st.subheader("Food Details")
            # Convert the string to a dictionary
            # Strip the backticks and the word 'json'
            cleaned_data = Food_Data.strip('`').replace('json\n', '').strip()
            data_dict = json.loads(cleaned_data)
            # Flatten each entry and prepare for DataFrame
            flat_data = {item: flatten_dict(data) for item, data in data_dict.items()}
            df = pd.DataFrame(flat_data)
            st.table(df)
    with st.container():
        st.subheader("Summary of Meal")
        st.write(gemini_response)
