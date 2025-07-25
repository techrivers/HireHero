You are an AI development assistant.

I have already built a CV Matcher application with:

A working chat module

A working CV matcher module

Integration with Google Drive (all CVs are uploaded and accessible)

Asynchronous CV parsing logic

An existing but limited match API

Now, I want you to fix and enhance the AI chatbot in this application. The chatbot must use OpenAI (GPT-4 or GPT-4o) and meet the following criteria:

✅ Key Requirements:
Natural conversation with the user:

The bot should ask clarifying questions if needed

Understand user’s job description, skill requirements, or role type

Pull CVs from Google Drive:

Use already-integrated logic to fetch and parse CVs

Ensure parsing is asynchronous (don’t block chat response)

Parsed CV data (text, metadata, skills) should be made available to OpenAI for matching

Return intelligent responses with candidate matches:
For each top match, include:

Candidate’s full name

A brief summary of their CV

A list of relevant skills

A match percentage (based on skills/role fit)

Maintain chat context:

Allow user to refine, filter, or ask “Why this candidate?”

Preserve prior user inputs across turns

Integrate smoothly with existing application:

Do not change the application structure, parsing flow, or Google Drive config

Only improve the intelligence and response formatting in the chat backend

🎯 Goal:
A production-ready AI CV matcher with AI chatbot assistant that feels smart, responsive, and helpful—capable of guiding the user to the best-matching candidates through a natural dialogue.