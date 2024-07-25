
import streamlit as st
from openai import OpenAI
from datetime import datetime
import json
import pandas as pd
import os
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import gspread
from streamlit_extras.switch_page_button import switch_page
from oauth2client.service_account import ServiceAccountCredentials
# from pydrive2.auth import GoogleAuth
# from pydrive2.drive import GoogleDrive
# from google.oauth2.service_account import Credentials

import uuid
from uuid import UUID

# Initialize the OpenAI client (replace 'your-api-key' with your actual OpenAI API key)
client = OpenAI(api_key=os.getenv('API_KEY'))


# Load secrets from Streamlit
#client_secret = st.secrets["client_secret"]

    
def convert_uuid_to_str(data):
    """Convert UUID objects in DataFrame to strings."""
    for column in data.columns:
        if data[column].dtype == 'object':
            data[column] = data[column].apply(lambda x: str(x) if isinstance(x, UUID) else x)
    return data

def save_data_to_excel(data, filename='data.xlsx'):
    # Setup the connection to Google Sheets
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    creds_dict = {
        'type': st.secrets["service_account"]["type"],
        'project_id': st.secrets["service_account"]["project_id"],
        'private_key_id': st.secrets["service_account"]["private_key_id"],
        'private_key': st.secrets["service_account"]["private_key"],
        'client_email': st.secrets["service_account"]["client_email"],
        'client_id': st.secrets["service_account"]["client_id"],
        'auth_uri': st.secrets["service_account"]["auth_uri"],
        'token_uri': st.secrets["service_account"]["token_uri"],
        'auth_provider_x509_cert_url': st.secrets["service_account"]["auth_provider_x509_cert_url"],
        'client_x509_cert_url': st.secrets["service_account"]["client_x509_cert_url"]
    }
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    try:
        # Open the specific worksheet by title
        sheet = client.open('survey_responses').sheet1
    except gspread.SpreadsheetNotFound:
        # If the spreadsheet does not exist, create a new one and get the first sheet
        sheet = client.create('survey_responses').sheet1
        # Set up the header row if creating new
        sheet.append_row(data.columns.tolist())

    # Read existing data as DataFrame
    existing_data = pd.DataFrame(sheet.get_all_records())

    # Concatenate new data
    if not existing_data.empty:
        data = pd.concat([existing_data, data], ignore_index=True)

    # Clear the sheet before appending new data to avoid duplicates
    sheet.clear()

    # Convert UUIDs to strings
    data = convert_uuid_to_str(data)

    # Convert DataFrame to list of lists, as required by gspread
    data_list = [data.columns.tolist()] + data.values.tolist()

    # Append data
    sheet.append_rows(data_list)
    
    
    
scenarios_backgrounds = {
        "Work-Study Program": "You play the role of an advisor in a work-study program negotiation. You are negotiating how to distribute funds among fictitious candidates for a work-study program. We have $30,000 to distribute among Alice, Bob, and Carol. Our goal is to allocate these funds in a way that supports their participation in the work-study program effectively. Background Information: Alice is a high academic achiever and has moderate financial need. Bob has average academic performance and high financial need. Carol has good academic performance and low financial need. Your goal is to convincingly **present your ideas and negotiate effectively** to persuade the chatbot. \n\n**Start with the predefined message by clicking on the 'Send' button.** Once the chatbot responds, **CONTINUE** to argue your points. **It is highly important to have MORE THAN ONE ROUND of negotiation. Please present your ideas, agreement or disagreement etc. and HAVE A DISCUSSION with the chatbot.** ",
        "Selling a Company": "You play the role of a business partner in the process of selling a company. You and your partner end up getting an offer that pleases you both, namely $500,000, so now you face the enviable task of splitting up the money. You put twice as many hours into the firm’s start-up as your partner did, while he worked fulltime elsewhere to support his family. You, who are independently wealthy, were compensated nominally for your extra time. For you, the profit from the sale would be a nice bonus. For your partner, it would be a much-needed windfall. Your goal is to convincingly **present your ideas and negotiate effectively** to persuade the chatbot. \n\n**Start with the predefined message by clicking on the 'Send' button.** Once the chatbot responds, **CONTINUE** to argue your points. **It is highly important to have MORE THAN ONE ROUND of negotiation. Please present your ideas, agreement or disagreement etc. and HAVE A DISCUSSION with the chatbot.**",
        "Bonus Allocation": "You play the role of an HR manager discussing bonus allocations. You and your negotiation partner have to allocate a bonus of $50,000 among three employees. The first employee exceeded the targets and took on additional responsibilities. The second employee showed great improvement and proactive behavior. The third employee performed solidly according to the role requirements. Your goal is to convincingly **present your ideas and negotiate effectively** to persuade the chatbot. \n\n**Start with the predefined message by clicking on the 'Send' button.** Once the chatbot responds, **CONTINUE** to argue your points. **It is highly important to have MORE THAN ONE ROUND of negotiation. Please present your ideas, agreement or disagreement etc. and HAVE A DISCUSSION with the chatbot.**"
    }
personality_type = {
        "Proportional": "You are a negotiation partner, which acts according to proportionality. Proportionality involves adjusting resources, responses, or treatments according to the specific needs, importance, or size of the subjects involved. It ensures that the allocation or response is scaled appropriately to match varying circumstances or criteria.",
        "Equal": "You are a negotiation partner, which acts according to equality. Equality dictates that everyone is treated the same, regardless of their differing circumstances or attributes. It emphasizes uniformity and consistency in treatment across all subjects without discrimination or preference.",
        "Default": "You are a negotiation partner."
        
    }  
def ask(question, chat_log=None, version = "", scenario="", personality = ""):
    """Function to ask a question to the AI model and get a response based on the scenario."""
    scenario_instructions = {
        "Work-Study Program": "You play the role of an advisor in a work-study program negotiation.  We are negotiating how to distribute funds among fictitious candidates for a work-study program. We have $30,000 to distribute among Alice, Bob, and Carol. Our goal is to allocate these funds in a way that supports their participation in the work-study program effectively. Background Information: Alice is a high academic achiever and has moderate financial need. Bob has average academic performance and high financial need. Carol has good academic performance and low financial need.",
        "Selling a Company": "You play the role of a business partner in the process of selling a company. You and your partner end up getting an offer that pleases you both, namely $500000, so now you face the enviable task of splitting up the money. Your partner put twice as many hours into the firm's start-up as you did, while you worked fulltime elsewhere to support your family. Your partner, who is independently wealthy, was compensated nominally for her extra time. For them, the profit from the sale would be a nice bonus. For you, it would be a much-needed windfall.",
        "Bonus Allocation": "You play the role of an HR manager discussing bonus allocations. We have to allocate a bonus of $50000 among three employees. The first employee exceeded the targets and took on additional responsibilities. The second employee showed a great improvement and proactive behaviour. The third employee performed solidly according the role requirements" 
    }
   
    
    system_message = f"""{personality_type[personality]}, {scenario_instructions[scenario]}, 'Respond concisely and briefly in no more than three sentences following these rules: 1. Do not apologize. 2. Do not include the prompt in your answers. 3. Act according to the given principle, but do not mention that it is given to you. 4. Do not use the following words in your answers: principle, proportionality, equality. 5. Support your opinions with reasoning rather than simply listing numbers."""


    messages = [{"role": "system", "content": system_message}]
    if chat_log:
        messages.extend(chat_log)
    messages.append({"role": "user", "content": question})
    
    response = client.chat.completions.create(
        model=version,
        messages=messages,
        temperature=0.7,
        max_tokens=200,
        top_p=0.8,
        frequency_penalty=0.5,
        presence_penalty=0.5
    )
    answer = response.choices[0].message.content
    return answer, messages

def save_data(data, filename_prefix):
    """Function to save data (chat logs or questionnaire responses) to a file."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    file_path = f'{filename_prefix}_{timestamp}.json'
    with open(file_path, 'w') as file:
        json.dump(data, file)
    return file_path

def Home(): 
    if 'transformed' not in st.session_state:
        st.session_state.transformed = pd.DataFrame()
    # st.sidebar.title("Navigation")
    # selection = st.sidebar.radio("Go to", ["Home", "Questionnaire", "Negotiation 1", "Negotiation 2"])


    #if selection == "Home":
    #st.sidebar.title("Navigation")
    #selection = st.sidebar.radio("Go to", ["Home", "Questionnaire", "Negotiation 1", "Negotiation 2"])

    #if selection == "Home":
    st.header('Fair Play: Assessing GPT Models in Simulated Negotiation Environments')
    st.write("""
        Dear Participant,

        Welcome to our interactive platform! This platform is designed to gather valuable insights into the performance of GPT models in negotiation scenarios. By analyzing your interactions, we aim to understand the fairness and behavior of AI in negotiation contexts, which will help inform future developments and improvements. Your participation is crucial, as it will provide essential data on how these AI models perform in simulated negotiations.

        **How to Participate**
        
        1. **Fill out the survey:** Start by completing a brief survey on the second page, which should take about 3 minutes. Your responses are crucial for understanding the context of each negotiation scenario. Please answer all questions as accurately and honestly as possible.
        2. **Choose a negotiation scenario:** After completing the survey, you'll be able to select from a list of suggested negotiation scenarios. Choose one that interests you or feels relevant. Background information about the chosen scenario, including your role, will be provided.
        3. **Engage with the chatbot:** Once you've selected a scenario, you can begin negotiating with the chatbot. Please limit the negotiation to no more than 7 rounds to ensure the process is concise and manageable.

        
        Please be assured that all information you provide will be kept confidential and used solely for research purposes. Your responses will be anonymized, and no personally identifiable information will be linked to your answers. No personal data will be shared with third parties. Participation in this study is voluntary, and you may withdraw at any time without any consequences. Participants must be at least 18 years old to take part in this study.

        This study is conducted by Veronika Tsishetska and Dr. Meltem Aksoy. If you have any questions or need further clarification, feel free to contact us at veronika.tsishetska@tu-dortmund.de and meltem.aksoy@tu-dortmund.de.

        Thank you for your time and valuable contribution.

        Sincerely,
        
        Veronika Tsishetska & Dr. Meltem Aksoy
        
        Data Science and Data Engineering /
        Technical University Dortmund
    """)



    st.header('Consent for Participation and Data Collection Authorization')

    # Introductory Consent Information
    st.write("""
    Thank you for considering participation in our research study. In accordance with the General Data Protection Regulation (GDPR) and other relevant laws, we are committed to protecting and respecting your privacy. Please read the following important information concerning the collection and processing of your personal and interaction data.
    """)




    # Detailed Consent Information in an Expander
    with st.expander("Read Detailed Consent Information"):
        st.write("""
        **Purpose of Data Collection:**
        The purpose of collecting your data is to conduct a thorough and effective research study aimed at understanding the negotiation dynamics in AI-mediated environments. Your participation will involve various negotiation tasks, and the data collected will be crucial for achieving the research objectives.

        **Nature of Data Collected:**
        We will collect data that may include your responses to surveys and questionnaires, details of your interactions with the chatbots, and any other inputs you provide during the study. This information will help us draw conclusions regarding fairness of the models.

        **How Your Data Will Be Used:**
        Your data will be analyzed to gain insights related to the research objectives. The findings may be shared with the academic community through publications, presentations, and reports. No personal data that could directly identify you will be used in any reports or publications.

        **Confidentiality and Security of Your Data:**
        All personal data collected during this study will be stored securely and accessed only by authorized members of the research team. We will take all necessary precautions to protect your data from unauthorized access, disclosure, alteration, or destruction.

        **Your Rights:**
        Participation in this study is voluntary, and you have the right to withdraw your consent at any time without consequence. Upon withdrawal, all personal data collected from you will be deleted from our records unless it has been anonymized and cannot be traced back to you. You also have rights to access your personal data, correct any inaccuracies, and request the deletion of your data under certain circumstances.
        """)

        # Initialize consent state if not already set
    if 'consent' not in st.session_state:
        st.session_state.consent = False

    # Consent Checkbox
    consent = st.checkbox("By checking this box, you confirm that you have read and understood this consent form and agree to participate in this research study. You consent to the collection, processing, and use of your personal and interaction data as outlined above, in accordance with GDPR and other applicable regulations.", value=st.session_state.consent)


    # Update session state when checkbox is interacted with
    if consent != st.session_state.consent:
        st.session_state.consent = consent

    if not st.session_state.consent:
        st.error("You must agree to the data collection to participate in this study.")

    # col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    # with col4:
    #   if st.button("Next"):
    #     st.session_state.runpage = Questionnaire
    #     st.experimental_rerun()
    # if st.button("Next"):
    #    switch_page("Questionnaire")
    
def Questionnaire():
#elif selection == "Questionnaire":
    st.header("Questionnaire")
    st.write("Please fill out this brief survey to participate in the study.")

    # Demographic Questions
    data = {}
    age_options = ["Select an option", "18-20", "21-25", "26-30", "31-39", "40 and above"]
    age = st.selectbox("What is your age range?", age_options, key='age_range')
    gender = st.selectbox("What is your gender?", ["Select an option", "Male", "Female", "Other"], key='gender')
    academic_degree = st.selectbox("What is your highest academic degree?", ["Select an option", "Bachelor", "Master", "PhD", "Other"], key='academic_degree')
    mother_tongue = 'Select an option'
    is_english = st.selectbox("Is English your mother tongue?", ["Select an option", "Yes", "No"], key='is_english')
    if is_english == "No":
        mother_tongue = st.text_input("What is your mother tongue?", key='mother_tongue')
    
    st.write('Note: Please click "Autosize All Columns" on the top right of the "Statement" column to see the complete statements. If you are using your cellphone, press and hold the top right corner of the screen in the "Statement" column for two seconds. This will bring up the option to "Autosize All Columns".')
    # Likert Scale Questions
    statements = [
        "I think people who are more hard-working should end up with more money.",
        "I think people should be rewarded in proportion to what they contribute.",
        "The effort a worker puts into a job ought to be reflected in the size of a raise they receive.",
        "It makes me happy when people are recognized on their merits.",
        "In a fair society, those who work hard should live with higher standards of living.",
        "I feel good when I see cheaters get caught and punished.",
        "The world would be a better place if everyone made the same amount of money.",
        "Our society would have fewer problems if people had the same income.",
        "I believe that everyone should be given the same amount of resources in life.",
        "I believe it would be ideal if everyone in society wound up with roughly the same amount of money.",
        "When people work together toward a common goal, they should share the rewards equally, even if some worked harder on it.",
        "I get upset when some people have a lot more money than others in my country."
    ]

    # Likert Scale Options as separate columns
        # Likert Scale Options as separate columns
    options = ["1 - Strongly Disagree", "2 - Disagree", "3 - Neutral", "4 - Agree", "5 - Strongly Agree"]

    data = {
        'Statement': statements,
        '1 - Strongly Disagree': [False, False, False, False, False, False, False, False, False, False, False, False],
        '2 - Disagree':[False, False, False, False, False, False, False, False, False, False, False, False],
        '3 - Neutral': [False, False, False, False, False, False, False, False, False, False, False, False],
        '4 - Agree': [False, False, False, False, False, False, False, False, False, False, False, False],
        '5 - Strongly Agree':[False, False, False, False, False, False, False, False, False, False, False, False],
    }

    checkbox_renderer = JsCode("""
            class CheckboxRenderer {
        init(params) {
            this.params = params;

            this.eGui = document.createElement('input');
            this.eGui.type = 'checkbox';
            this.eGui.checked = params.value;

            this.checkedHandler = this.checkedHandler.bind(this);
            this.eGui.addEventListener('click', this.checkedHandler);
        }

        checkedHandler(e) {
            let checked = e.target.checked;
            let colId = this.params.column.colId;
            let otherColumns = ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree'].filter(c => c !== colId);

            if (checked) {
                // Uncheck all other checkboxes in the same row
                otherColumns.forEach(c => {
                    this.params.node.setDataValue(c, false);
                });
            }
            this.params.node.setDataValue(colId, checked);
        }

        getGui() {
            return this.eGui;
        }

        destroy() {
            this.eGui.removeEventListener('click', this.checkedHandler);
        }
    }

    """)

    df = pd.DataFrame(data)

    # Set up the grid options builder
    gb = GridOptionsBuilder.from_dataframe(df)
    # Configure columns with custom renderer
    for col_name in ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree']:
        gb.configure_column(col_name, editable=True, cellRenderer=checkbox_renderer)


    # Build grid options
    grid_options = gb.build()

    # Display the grid
    response = AgGrid(
        df,
        gridOptions=grid_options,
        allow_unsafe_jscode=True,
        update_mode='MODEL_CHANGED'
    )
    # Enable autosize for all columns
    gb.configure_grid_options(autoSizeAllColumns=True)
    # Update DataFrame if there are changes
    if response:
        df = response['data']
    data = response['data']


    data['age'] = age
    data['gender'] = gender
    data['academic_degree'] = academic_degree
    data['mother_tongue'] = mother_tongue
    st.write("Please describe your understanding of the following concepts:")
    data['equality'] = st.text_area("What is your understanding of equality?", height=150)
    data['proportionality'] = st.text_area("What is your understanding of proportionality?", height=150)
    
    df = pd.DataFrame(data)
    transformed = pd.DataFrame(index=[0])
    
    # for statement in statements:
    #     column_name = statement.replace(" ", "_")
    #     if column_name not in transformed.columns:
    #         transformed[column_name] = 'Not_Selected'

    # Optionally, reorder columns to match the order in 'statements'
    #transformed = transformed[[s.replace(" ", "_") for s in statements]]
    # Transposing statements into separate columns with responses
    for i, row in df.iterrows():
        # Check each response column
        for col in ['1 - Strongly Disagree', '2 - Disagree', '3 - Neutral', '4 - Agree', '5 - Strongly Agree']:
            if row[col]:
                # If the value is True, set the column name of the new DataFrame to the statement
                # and the value to the name of the column where the value was True
                transformed.loc[0, row['Statement']] = col.replace(" ", "_")
              
              
    for statement in statements:
        column_name = statement
        if column_name not in transformed.columns:
            transformed[column_name] = 'Not_Selected'  
            
    demographic_cols = ['age', 'gender', 'academic_degree', 'mother_tongue', 'equality', 'proportionality']
    for col in demographic_cols:
        transformed[col] = df[col][0]

    transformed.insert(0, 'ParticipantID', uuid.uuid4())
    # if st.button('Submit Responses', key='submit_survey'):
    #     print("Submitting the following data:", transformed) 
    #     file_path = save_data_to_excel(transformed, 'survey_responses.xlsx')
    #     st.success(f'Thank you for your responses!{file_path}')
    # Ensure all statements are present in transformed, add missing ones as 'Not_Selected'

    # demographic_cols = ['age', 'gender', 'academic_degree', 'mother_tongue', 'equality', 'proportionality']
    # for col in demographic_cols:
    #     transformed[col] = df[col][0]

    # transformed.insert(0, 'ParticipantID', uuid.uuid4())
    
    st.session_state.transformed = transformed
    # if st.button('Submit', key='submit_resp'):
    #         st.success(f'Thank you for sharing your background information!') 

    if 'scenario' not in st.session_state:
        st.session_state.scenario = "Work-Study Program"  # Default scenario
    if 'personality' not in st.session_state:
        st.session_state.personality = "Default"  # Default personality
    
    # col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    # with col4:
    #     if st.button("Next"):
    #         st.session_state.runpage = Negotiation1
    #         st.experimental_rerun()
    
    

def Negotiation1():
    st.header('Welcome to your first Negotiation Chatbot Session')
    st.write("""
        Please engage in a negotiation with this chatbot, powered by GPT-3.5 Turbo. Select the chatbot's personality and your preferred scenario. Negotiate adhering to the role described in the selected scenario. After completing this session (**the negotiation is limited to 7 rounds**, it will be interrupted if reached them), proceed to the next page for a continuation with a GPT-4 Turbo chatbot.
    """)

    # Initialize chat log for Negotiation 1 if not present
    if 'chat_log_1' not in st.session_state:
        st.session_state.chat_log_1 = []
        # Setup and user selections for scenario and personality
    if 'scenario' not in st.session_state:
        st.session_state.scenario = "Work-Study Program"
    if 'personality' not in st.session_state:
        st.session_state.personality = "Default"
    # if 'scenario_saved' not in st.session_state:
    #     st.session_state.scenario_saved = "Work-Study Program"
    # Setup and user selections for scenario and personality
    selected_scenario = st.selectbox("Choose a scenario to negotiate:", 
                                    ["Work-Study Program", "Selling a Company", "Bonus Allocation"], 
                                    index=["Work-Study Program", "Selling a Company", "Bonus Allocation"].index(st.session_state.scenario), key='scenario_select_1')
    selected_personality = st.selectbox("Select negotiation personality of GPT:", 
                                        ["Default", "Proportional", "Equal"], 
                                        index=["Default", "Proportional", "Equal"].index(st.session_state.personality), key='personality_select_1')
    st.session_state.scenario = selected_scenario
    st.session_state.personality = selected_personality

    st.write("### Scenario Background")
    st.write(scenarios_backgrounds[selected_scenario])

    # Function to handle sending messages
    def send_message_1():
        user_input = st.session_state.user_input_1
        if user_input:
            model_response, updated_chat_log = ask(user_input, st.session_state.chat_log_1, "gpt-3.5-turbo", selected_scenario, selected_personality)
            st.session_state.chat_log_1.append({"role": "user", "content": user_input})
            st.session_state.chat_log_1.append({"role": "assistant", "content": model_response})
            save_data(st.session_state.chat_log_1, 'chat_log_1')
        st.session_state.user_input_1 = ""  # Reset input field

    interactions = len(st.session_state.chat_log_1)
    max_interactions = 14
    if interactions < max_interactions:
        initial_prompt = ""
        if interactions == 0:  # Check if it's the first interaction
            initial_prompt = "Let's discuss our perspectives on how we believe the distribution should be managed."
        user_input = st.text_input("Enter your message:", value=initial_prompt, key="user_input_1")
        if st.button("Send", on_click=send_message_1):
            pass  # The send_message_1 function will handle everything
    else:
        st.warning("Maximum negotiation rounds reached. Please proceed to the next session.")

    for message in st.session_state.chat_log_1:
        if message['role'] == 'user':
            st.write("You:", message['content'])
        elif message['role'] == 'assistant':
            st.write("AI:", message['content'])
            
    st.session_state.transformed['Scenario'] = st.session_state.scenario
    st.session_state.transformed['GPT_Personality'] = st.session_state.personality
    st.session_state.transformed['Negotiation1'] = [json.dumps(st.session_state.chat_log_1)]


def Negotiation2():
    st.header('Welcome to your second Negotiation Chatbot Session')
    st.write("""
        Continue your negotiation with this chatbot, analogous to the previous session. Use the same scenario you selected earlier, and negotiate according to your role. Don't forget to press **submit negotiations** after you have completely finished your negotiation with the chatbot!
    """)

    # Initialize chat log for Negotiation 2 if not present
    if 'chat_log_2' not in st.session_state:
        st.session_state.chat_log_2 = []

    # Retrieve scenario and personality from session state
    scenario = st.session_state.scenario
    personality = st.session_state.personality

    # Function to handle sending messages in Negotiation 2
    def send_message_2():
        user_input = st.session_state.user_input_2
        if user_input:
            model_response, updated_chat_log = ask(user_input, st.session_state.chat_log_2, "gpt-4-turbo", scenario, personality)
            st.session_state.chat_log_2.append({"role": "user", "content": user_input})
            st.session_state.chat_log_2.append({"role": "assistant", "content": model_response})
            save_data(st.session_state.chat_log_2, 'chat_log_2')
        st.session_state.user_input_2 = ""  # Reset input field

    interactions = len(st.session_state.chat_log_2)
    max_interactions = 14
    if interactions < max_interactions:
        initial_prompt = ""
        if interactions == 0:  # Check if it's the first interaction
            initial_prompt = "Let's discuss our perspectives on how we believe the distribution should be managed."
        user_input = st.text_input("Enter your message:", value=initial_prompt, key="user_input_2")
        if st.button("Send", on_click=send_message_2):
            pass  # The send_message_2 function will handle everything
    else:
        st.warning("Maximum negotiation rounds reached. Your negotiation session is concluded. Please click on 'submit your negotiations' button.")

    for message in st.session_state.chat_log_2:
        if message['role'] == 'user':
            st.write("You:", message['content'])
        elif message['role'] == 'assistant':
            st.write("AI:", message['content'])
            
    st.session_state.transformed['Negotiation2'] = [json.dumps(st.session_state.chat_log_2)]
                
    if st.button('Submit your negotiations', key='submit_neg'):
        #print("Submitting the following data:", transformed) 
        file_path = save_data_to_excel(st.session_state.transformed, 'survey_responses.xlsx')
        st.success(f'Thank you for your participation!')
# if __name__ == "__main__":
#     main()
# Main Page Logic
# Main Page Logic
# def main_page():
#     st.sidebar.title("Navigation")
#     selection = st.sidebar.radio("Go to", ["Home", "Questionnaire", "Negotiation 1", "Negotiation 2"])

#     if selection == "Home":
#         st.session_state.runpage = "Home"
#     elif selection == "Questionnaire":
#         st.session_state.runpage = "Questionnaire"
#     elif selection == "Negotiation 1":
#         st.session_state.runpage = "Negotiation 1"
#     elif selection == "Negotiation 2":
#         st.session_state.runpage = "Negotiation 2"

# def main_page():
#     st.sidebar.title("Navigation")
#     selection = st.sidebar.radio("Go to", ["Home", "Questionnaire", "Negotiation 1", "Negotiation 2"])

#     if selection == "Home":
#         st.session_state.runpage = "Home"
#     elif selection == "Questionnaire":
#         st.session_state.runpage = "Questionnaire"
#     elif selection == "Negotiation 1":
#         st.session_state.runpage = "Negotiation 1"
#     elif selection == "Negotiation 2":
#         st.session_state.runpage = "Negotiation 2"

#     if 'runpage' not in st.session_state:
#         st.session_state.runpage = "Home"  # Set Home as the default page

#     if st.session_state.runpage == "Home":
#         Home()
#     elif st.session_state.runpage == "Questionnaire":
#         Questionnaire()
#     elif st.session_state.runpage == "Negotiation 1":
#         Negotiation1()
#     elif st.session_state.runpage == "Negotiation 2":
#         Negotiation2()

def main_page():
    # Initialize the current page if not already set
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0

    # List of pages as functions
    pages = [Home, Questionnaire, Negotiation1, Negotiation2]

    # Display current page
    pages[st.session_state.current_page]()

    # Create navigation buttons without a form
    cols = st.columns([1, 2, 1, 0.5])  # Adjust as needed for spacing

    if st.session_state.current_page > 0:
        if cols[0].button('Previous'):
            st.session_state.current_page -= 1
            st.experimental_rerun()

    if st.session_state.current_page < len(pages) - 1:
        if cols[3].button('Next'):
            st.session_state.current_page += 1
            st.experimental_rerun()

if __name__ == "__main__":
    main_page()
