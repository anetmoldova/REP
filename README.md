# RealEstatePricing AI Assistant (REP)

This is a Django-based web app with an OpenAI-powered chatbot (LangChain) and future support for database integration.

## Requirements

- Python 3.10+
- Virtualenv: `pip install virtualenv`
- OpenAI API key from https\://platform.openai.com/account/api-keys

## Setup

### 1. Clone and Enter Project

```bash
git clone https://github.com/anetmoldova/REP.git
cd REP
```

### 2. Set Up Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Environment Variable

```bash
export OPENAI_API_KEY='your-key'   # Mac/Linux
set OPENAI_API_KEY=your-key        # Windows
```

### 5. Run Django Migrations

```bash
python manage.py migrate
```

### 6. Start the App

```bash
python manage.py runserver
```

Visit [http://127.0.0.1:8000](http://127.0.0.1:8000) to use the app.

## Chatbot Logic (LangChain)

```python
from langchain_openai import ChatOpenAI 
from langchain.schema import HumanMessage
import os

llm = ChatOpenAI(temperature=0.5, api_key=os.getenv("OPENAI_API_KEY"))

def get_bot_response(prompt):
    return llm([HumanMessage(content=prompt)]).content
```

---

