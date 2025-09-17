# FoodieBot – Database-Driven Conversational Fast Food System

##  Overview
FoodieBot is an AI-powered conversational recommender system that suggests fast food products in real-time.  
It uses a SQLite database of food items, an interest scoring mechanism, and a Streamlit interface to deliver personalized recommendations and analytics.

##  Features
- Conversational interface to capture user cravings and moods
- Interest score calculation (0–100%) based on preferences, budget, and enthusiasm
- Database-driven recommendations with product filtering
- Analytics dashboard with interest score progression
- Product cards with details (name, price, description)
- Logs conversations with user queries, bot responses, and scores

##  Tech Stack
- *Python*
- *Streamlit* (frontend)
- *SQLite* (database)
- *Pandas & Plotly* (analytics & visualization)

##  Project Structure

FoodieBot/
│── foodbot.py          # Main Streamlit app
│── requirements.txt    # Dependencies
│── README.md           # Project guide
│── FoodieBot_Project_Report.pdf  # Project Report


##  Installation & Setup
1. Clone the project or download the files.
2. Install dependencies:
   bash
   pip install -r requirements.txt
   
3. Run FoodieBot with Streamlit:
   bash
   streamlit run foodbot.py
   

##  Usage
- Type your cravings in the chat input (e.g., "spicy burger under $10").
- Get food recommendations with interest scores.
- View analytics in real-time.

##  Example Queries
- "Show me a vegan pizza"
- "I want something spicy and adventurous under $15"
- "Best dessert for comfort mood"

##  Future Improvements
- Integration with advanced LLM APIs (Hugging Face, Groq, etc.)
- Real-time collaborative filtering ("Customers also liked...")
- Larger dataset with 100+ products
- Multi-language support

---
 Developed by Sneha  
