from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
import os
import openai
import aiohttp
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("WARNING: OPENAI_API_KEY environment variable not set.")
    # Consider raising an error in a real app: raise ValueError("Missing OpenAI API Key")
    client = None  # Or handle appropriately
else:
    client = openai.AsyncOpenAI(api_key=openai_api_key)

# Initialize Google Books API key
google_books_api_key = os.getenv("GOOGLE_BOOKS_API_KEY")
if not google_books_api_key:
    print("WARNING: GOOGLE_BOOKS_API_KEY environment variable not set.")
    # Consider raising an error in a real app or disabling functionality

# Initialize Webhook Secret
webhook_secret = os.getenv("WEBHOOK_SECRET")
if not webhook_secret:
    print("WARNING: WEBHOOK_SECRET environment variable not set.")
    # Consider raising an error in a real app or disabling functionality

# Initialize Amazon Associate Tag
amazon_associate_tag = os.getenv("AMAZON_ASSOCIATE_TAG")
if not amazon_associate_tag:
    print("WARNING: AMAZON_ASSOCIATE_TAG environment variable not set.")
    # Consider raising an error in a real app or disabling functionality

class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    user_id: str
    bot_message: str
    suggestions: List[str] = []
    books: List[dict] = []  # Placeholder for book data

app = FastAPI()

# In-memory session state management
session_states: Dict[str, Dict[str, Any]] = {}

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8081", 
    "https://bookgpt.vercel.app",  # Main Vercel deployment URL
    "https://bookgpt-*.vercel.app",  # Preview deployments
    "*",  # Allow all origins - will be restricted by the webhook secret
    "null"  # Allow local file:// origin
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

async def process_nlp(text: str, current_stage: str) -> dict:
    """
    Placeholder for NLP processing (Intent Recognition & Entity Extraction).
    Currently uses basic keywords, will be replaced by an LLM call.
    Input: user message, current conversation stage.
    Output: dict e.g., {'intent': 'REQUEST_RECOMMENDATION', 'entities': {'genre': 'sci-fi'}, 'refined_message': '...'}
    """
    print(f"NLP Placeholder: Processing text: '{text}' in stage: {current_stage}")
    intent = "UNKNOWN"
    entities = {}
    
    # Special case for empty messages or very short initial messages at INIT stage
    if (not text or text.strip() == "") and current_stage == "INIT":
        intent = "GREETING"
        print("NLP: Empty message in INIT stage interpreted as GREETING")
    else:
        # --- Simple Keyword Logic (Replace with LLM in Prompt 9/Integration) ---
        lower_text = text.lower()
        
        # IMPROVED: Greatly expanded list of recommendation keywords to match more user inputs
        # Especially from the suggestion buttons
        if any(word in lower_text for word in ["book", "recommend", "read", "suggest", "mystery", "fantasy", 
                                             "sci-fi", "fiction", "novel", "like", "books", "thriller", "genre",
                                             "bestseller", "this year", "bestsellers", "historical", "female",
                                             "contemporary", "popular", "author", "hobbit"]):
            intent = "REQUEST_RECOMMENDATION"
            print(f"NLP: Intent set to REQUEST_RECOMMENDATION based on keywords in: '{lower_text}'")
        elif any(word in lower_text for word in ["similar", "another"]):
            intent = "REQUEST_SIMILAR" # Could be used later
        elif any(word in lower_text for word in ["hi", "hello", "hey"]):
            intent = "GREETING"

        # Basic entity extraction (very rudimentary)
        # IMPROVED: Extract more entities from button suggestions
        if "sci-fi" in lower_text or "science fiction" in lower_text:
            entities["genre"] = "Science Fiction"
        if "fantasy" in lower_text:
            entities["genre"] = "Fantasy"
        if "thriller" in lower_text:
            entities["genre"] = "Thriller"
        if "mystery" in lower_text:
            entities["genre"] = "Mystery"
        if "bestseller" in lower_text or "this year" in lower_text:
            entities["category"] = "Bestsellers"
        if "historical" in lower_text and "fiction" in lower_text:
            entities["genre"] = "Historical Fiction"
        if "female" in lower_text and "author" in lower_text:
            entities["author_attribute"] = "Female"
        if "contemporary" in lower_text:
            entities["genre"] = "Contemporary Fiction"
        if "hobbit" in lower_text:
            entities["similar_to"] = "The Hobbit"
        # --- End Simple Logic ---
        
        # IMPROVED: If the message exactly matches one of our suggestions, always treat it as a recommendation request
        suggestion_options = [
            "suggest fantasy books", "recommend sci-fi", "books like the hobbit",
            "mystery novels", "contemporary fiction", "bestsellers this year",
            "historical fiction", "books by female authors", "popular mystery novels"
        ]
        if lower_text in suggestion_options:
            intent = "REQUEST_RECOMMENDATION"
            print(f"NLP: Intent set to REQUEST_RECOMMENDATION based on exact match to suggestion: '{lower_text}'")

    nlp_result = {"intent": intent, "entities": entities, "refined_message": text} # Pass original message for now
    print(f"NLP Placeholder: Result: {nlp_result}")
    return nlp_result

@app.get("/")
async def root():
    return {"message": "Book Recommendation Bot API"}

async def _fetch_and_process_recommendations(preferences, history, max_recs, amazon_tag):
    """
    Helper to fetch recommendations from ChatGPT, then search Google Books and enrich results.
    Returns a list of book result dicts.
    """
    recommendation_ideas = await get_chatgpt_recommendations(
        preferences=preferences,
        history=history,
        max_recommendations=max_recs
    )

    book_results = []
    if recommendation_ideas:
        for idea in recommendation_ideas:
            print(f"Processing recommendation idea: {idea}")
            search_query = f"{idea.get('title', '')} {idea.get('author', '')}"
            search_results = await search_google_books(query=search_query.strip(), max_results=1)
            if search_results:
                book_id = search_results[0].get("id")
                if book_id:
                    book_details = await get_book_details_by_id(book_id)
                    if book_details:
                        book_details["reasoning"] = idea.get("reasoning", "No specific reason provided.")
                        isbn = book_details.get('isbn13', '')
                        if isbn:
                            book_details["amazon_link"] = f"https://www.amazon.com/s?k={isbn}&tag={amazon_tag}"
                        else:
                            book_details["amazon_link"] = None
                        book_results.append(book_details)
    return book_results

@app.post("/api/chat", response_model=ChatResponse)
async def handle_chat(request: ChatRequest):
    print(f"Received: user_id={request.user_id}, message='{request.message}'")  # Basic logging
    
    # Retrieve/Initialize State
    session_id = request.user_id
    user_state = session_states.get(session_id, {"history": [], "stage": "INIT", "details": {}})
    current_stage = user_state.get("stage", "INIT")
    print(f"User {session_id} - Current Stage: {current_stage}, State: {user_state}")
    
    # Append user message for context
    user_state["history"].append({"role": "user", "content": request.message})
    # Keep history concise for MVP if needed
    user_state["history"] = user_state["history"][-10:]  # Keep last 10 turns max for example
    
    # Process user message with NLP placeholder
    nlp_result = await process_nlp(request.message, current_stage)
    intent = nlp_result.get("intent", "UNKNOWN")
    entities = nlp_result.get("entities", {})
    refined_message = nlp_result.get("refined_message")

    print(f"NLP Result - Intent: {intent}, Entities: {entities}")

    # Initialize variables for response
    bot_message = ""
    response_suggestions = []
    
    # Core Conversation Logic - State Machine
    if intent == "GREETING" and current_stage == "INIT":
        # Handle simple initial greeting
        bot_message = "Hi! I'm here to help you discover your next great read. How can I help? You can tell me about genres you like, authors, or a book you recently enjoyed."
        response_suggestions = [
            "Suggest Fantasy Books", 
            "Recommend Sci-Fi", 
            "Books like The Hobbit",
            "Mystery Novels", 
            "Contemporary Fiction",
            "Bestsellers This Year",
            "Historical Fiction",
            "Books by Female Authors"
        ]
        user_state["stage"] = "AWAITING_PREFERENCES"

    elif intent == "REQUEST_RECOMMENDATION" and (current_stage == "INIT" or current_stage == "AWAITING_PREFERENCES"):
        # --- ENHANCED VAGUENESS CHECK ---
        is_vague = True  # Default assumption
        
        # Check message length - longer messages tend to have more context
        message_words = request.message.split()
        message_len = len(message_words)
        lower_message = request.message.lower()
        
        # 1. Check for specific entities from NLP
        has_entities = bool(entities.get("genre") or entities.get("author") or entities.get("similar_book"))
        
        # 2. Check for genre keywords - expanded list
        genre_keywords = [
            "fiction", "mystery", "romance", "biography", "history", 
            "children", "young adult", "ya", "fantasy", "sci-fi", 
            "science fiction", "thriller", "horror", "literary", 
            "contemporary", "classic", "crime", "non-fiction", 
            "memoir", "poetry", "adventure", "dystopian", "historical"
        ]
        has_genre = any(word in lower_message for word in genre_keywords)
        
        # 3. Check for author references
        author_phrases = [
            "by author", "written by", "books by", "author", "writer", 
            "novels by", "works by", "published by", "wrote"
        ]
        has_author = any(phrase in lower_message for phrase in author_phrases)
        
        # 4. Check for specific book references or "similar to" phrases
        book_reference_phrases = [
            "like", "similar to", "resembles", "reminds me of", "same as", 
            "in the style of", "comparable to", "books like", "series like",
            "enjoyed", "loved", "read", "finished", "recommend"
        ]
        has_book_reference = any(phrase in lower_message for phrase in book_reference_phrases) and message_len > 3
        
        # 5. Check for mood/tone preferences
        mood_phrases = [
            "happy", "sad", "uplifting", "dark", "funny", "humorous", 
            "serious", "light", "deep", "thought-provoking", "inspiring", 
            "relaxing", "exciting", "suspenseful", "scary", "romantic"
        ]
        has_mood = any(phrase in lower_message for phrase in mood_phrases)
        
        # 6. Check for time period references
        time_phrases = [
            "modern", "contemporary", "classic", "ancient", "medieval", 
            "19th century", "20th century", "victorian", "recent", 
            "new", "old", "latest", "antique", "retro", "futuristic"
        ]
        has_time_reference = any(phrase in lower_message for phrase in time_phrases)
        
        # 7. Check if message is longer than threshold
        is_detailed_request = message_len > 6
        
        # Determine if request has sufficient context based on multiple factors
        if has_entities or has_genre or has_author or has_book_reference or has_mood or has_time_reference or is_detailed_request:
            is_vague = False
            
        # Log the vagueness check results
        print(f"Vagueness check: is_vague={is_vague}, has_entities={has_entities}, has_genre={has_genre}, " 
              f"has_author={has_author}, has_book_reference={has_book_reference}, has_mood={has_mood}, "
              f"has_time_reference={has_time_reference}, is_detailed_request={is_detailed_request}")
        
        if is_vague:
            # Request is too vague, ask for clarification with enhanced options
            bot_message = "I'd love to help you find your next great read! To provide the most relevant recommendations, could you tell me a bit more about what you're looking for?"
            
            # Create dynamic rotating suggestion options based on current timestamp
            # This ensures different options appear each time
            import time
            seed = int(time.time()) % 4  # Use time as a simple rotation mechanism (0-3)
            
            # Define suggestion sets
            genre_suggestions = [
                "I enjoy fantasy books with dragons",
                "I'm looking for historical fiction set in ancient Rome",
                "Recommend me a cozy mystery novel",
                "I want a science fiction book about space exploration"
            ]
            
            author_suggestions = [
                "I like books similar to Neil Gaiman's style",
                "Recommend something by Agatha Christie",
                "I enjoy authors like Brandon Sanderson",
                "Books written by female science fiction authors"
            ]
            
            mood_suggestions = [
                "I need an uplifting book that's not too long",
                "Looking for a suspenseful thriller with unexpected twists",
                "Something funny and lighthearted for vacation",
                "A thought-provoking book about philosophy"
            ]
            
            specific_suggestions = [
                "Books like The Night Circus but with more adventure",
                "Fantasy series with well-developed magic systems",
                "A standalone novel with beautiful prose and character development",
                "Recent award-winning fiction books from the last 2 years"
            ]
            
            # Rotate each category based on the seed
            response_suggestions = [
                genre_suggestions[seed],
                author_suggestions[(seed + 1) % 4],
                mood_suggestions[(seed + 2) % 4],
                specific_suggestions[(seed + 3) % 4]
            ]
            
            user_state["stage"] = "AWAITING_PREFERENCES"  # Remain in this stage
            # Store the vague request in history
            user_state["details"]["last_vague_request"] = request.message
        else:
            bot_message = f"Okay, searching for recommendations based on: '{request.message}'..."
            user_state["details"]["preferences_text"] = request.message
            user_state["details"]["nlp_entities"] = entities

            # --- Use helper function for recommendations ---
            book_results = await _fetch_and_process_recommendations(
                entities or {"raw_query": request.message},
                user_state["history"],
                5,
                os.getenv('AMAZON_ASSOCIATE_TAG', 'bookgpt-20')
            )

            if book_results:
                bot_message = "Here are a few recommendations I found based on your request:"
                user_state["details"]["last_recommendations"] = book_results
                response_suggestions = ["Tell me more about #1", "Show different recommendations", "Start Over"]
                user_state["stage"] = "SHOWING_RECOMMENDATIONS"
            else:
                bot_message = "I came up with some ideas, but couldn't find specific book details for them right now. Could you try rephrasing your request or specifying different criteria?"
                response_suggestions = ["Try Fantasy genre", "Suggest popular Sci-Fi", "Recommend Thriller books"]
                user_state["stage"] = "AWAITING_PREFERENCES"

    elif current_stage == "SHOWING_RECOMMENDATIONS":
        # Handle follow-ups after showing recommendations
        lower_message = request.message.lower()

        if "more" in lower_message or "detail" in lower_message or "#1" in lower_message:
            # Attempt to retrieve stored recommendations
            last_recs = user_state["details"].get("last_recommendations", [])
            if last_recs:
                 # Extract detail based on number if possible - crude example:
                 num_match = [int(s) for s in request.message if s.isdigit()]
                 idx = num_match[0] - 1 if num_match and 0 <= num_match[0]-1 < len(last_recs) else 0
                 selected_book = last_recs[idx]
                 bot_message = f"Okay, about '{selected_book.get('title', 'that book')}': {selected_book.get('description', 'No further details available right now.')}"
            else:
                 bot_message = "I don't have the previous recommendations handy to give more detail. Could you ask for new ones?"
            response_suggestions = ["Show different recommendations", "Start Over"]
            # Keep stage SHOWING_RECOMMENDATIONS

        elif "different" in lower_message or "other" in lower_message or "new" in lower_message:
            bot_message = "Okay, what else are you looking for? Please tell me about genres, authors, or books you enjoy."
            response_suggestions = ["Fantasy recommendations", "Sci-Fi books", "Popular Thrillers"]
            user_state["stage"] = "AWAITING_PREFERENCES"

        elif "start" in lower_message or "reset" in lower_message or "over" in lower_message:
            user_state = {"history": [{"role": "user", "content": request.message}], "stage": "INIT", "details": {}} # Keep user message for context maybe?
            bot_message = "Let's start over! How can I help you find your next great read?"
            response_suggestions = [
                "Suggest Fantasy Books", 
                "Recommend Sci-Fi", 
                "Books like The Hobbit",
                "Mystery Novels", 
                "Contemporary Fiction",
                "Bestsellers This Year",
                "Historical Fiction",
                "Books by Female Authors"
            ]
            user_state["stage"] = "AWAITING_PREFERENCES"

        else:
            # If input after showing recommendations doesn't match follow-ups, assume it's a new request
            bot_message = f"Okay, let me see if I can find recommendations based on: '{request.message}'..."
            user_state["details"]["preferences_text"] = request.message
            user_state["details"]["nlp_entities"] = entities

            # --- Use helper function for recommendations ---
            book_results = await _fetch_and_process_recommendations(
                entities or {"raw_query": request.message},
                user_state["history"],
                5,
                os.getenv('AMAZON_ASSOCIATE_TAG', 'bookgpt-20')
            )

            if book_results:
                bot_message = "Based on your new request, here are some recommendations:"
                user_state["details"]["last_recommendations"] = book_results
                response_suggestions = ["Tell me more about #1", "Show different recommendations", "Start Over"]
                user_state["stage"] = "SHOWING_RECOMMENDATIONS"
            else:
                bot_message = "Sorry, I couldn't find specific details for that new request..."
                response_suggestions = ["Try Fantasy genre", "Suggest popular Sci-Fi"]
                user_state["stage"] = "AWAITING_PREFERENCES" # Go back

    else:
        # IMPROVED FALLBACK LOGIC:
        # Check if the message matches any of our common suggestion buttons
        # This acts as a safety net in case our NLP process failed to catch the intent
        lower_message = request.message.lower()
        suggestion_matches = [
            "suggest fantasy books", "recommend sci-fi", "books like the hobbit",
            "mystery novels", "contemporary fiction", "bestsellers this year",
            "historical fiction", "books by female authors", "popular mystery novels"
        ]
        if any(suggestion.lower() == lower_message for suggestion in suggestion_matches):
            # This is a button click that our NLP missed - treat it as a recommendation request
            print(f"Fallback logic: Recognized '{request.message}' as a suggestion button click")
            bot_message = f"Looking for {request.message}, one moment..."
            # Extract appropriate entities based on the message
            if "fantasy" in lower_message:
                entities["genre"] = "Fantasy"
            elif "sci-fi" in lower_message:
                entities["genre"] = "Science Fiction"
            elif "hobbit" in lower_message:
                entities["similar_to"] = "The Hobbit"
            elif "mystery" in lower_message:
                entities["genre"] = "Mystery"
            elif "contemporary" in lower_message:
                entities["genre"] = "Contemporary Fiction"
            elif "bestseller" in lower_message or "this year" in lower_message:
                entities["category"] = "Bestsellers"
            elif "historical" in lower_message:
                entities["genre"] = "Historical Fiction"
            elif "female" in lower_message and "author" in lower_message:
                entities["author_attribute"] = "Female"
            # Process as a recommendation request with the extracted entity
            user_state["details"]["preferences_text"] = request.message
            user_state["details"]["nlp_entities"] = entities
            # Use helper function for recommendations
            book_results = await _fetch_and_process_recommendations(
                entities or {"raw_query": request.message},
                user_state["history"],
                5,
                os.getenv('AMAZON_ASSOCIATE_TAG', 'bookgpt-20')
            )
            if book_results:
                bot_message = f"Here are some {request.message} that you might enjoy:"
                user_state["details"]["last_recommendations"] = book_results
                response_suggestions = ["Tell me more about #1", "Show different recommendations", "Start Over"]
                user_state["stage"] = "SHOWING_RECOMMENDATIONS"
            else:
                bot_message = f"I'm sorry, I couldn't find specific {request.message} at the moment. Could you try another category?"
                response_suggestions = ["Fantasy Books", "Mystery Novels", "Books by Female Authors"]
                user_state["stage"] = "AWAITING_PREFERENCES"
        else:
            # Default / Real Fallback for any unhandled stage/intent combination
            bot_message = "Sorry, I wasn't sure how to proceed from there. Could you clarify? You can ask for recommendations by genre, author, or similar books."
            # Provide more diverse options to maintain a better chat flow
            response_suggestions = [
                "Suggest Fantasy Books", 
                "Recommend Sci-Fi", 
                "Books like The Hobbit",
                "Popular mystery novels"
            ]
            user_state["stage"] = "AWAITING_PREFERENCES" # Default back to expecting preferences
    # Prepare final response
    final_books_data = user_state["details"].get("last_recommendations", []) if user_state["stage"] == "SHOWING_RECOMMENDATIONS" else []
    # Append bot response to history
    user_state["history"].append({"role": "assistant", "content": bot_message})
    # Save updated state
    session_states[session_id] = user_state
    print(f"User {session_id} - Saving New State: {user_state}")
    return ChatResponse(
        user_id=session_id,
        bot_message=bot_message,
        suggestions=response_suggestions,
        books=final_books_data  # Send book data only when showing recommendations
    )

# --- Mocked Google Books API Interface ---
# These functions simulate calls to the Google Books API.
# Their internal logic will be replaced with actual API calls in Prompt 12.

async def search_google_books(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Searches the Google Books API v1 for books matching a query.
    Returns a list of book summaries (id, title, authors).
    """
    if not google_books_api_key:
        print("Error: Google Books API key not configured.")
        return []

    search_url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        'q': query,
        'key': google_books_api_key,
        'maxResults': min(max_results, 40),  # Google API max is 40
        'projection': 'lite'  # Request less data for search results
    }
    print(f"Google Books API: Searching for '{query}'")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(search_url, params=params) as response:
                response.raise_for_status()  # Raise exception for bad status codes (4xx or 5xx)
                data = await response.json()

                items = data.get('items', [])
                results = []
                for item in items:
                    volume_info = item.get('volumeInfo', {})
                    results.append({
                        'id': item.get('id'),
                        'title': volume_info.get('title'),
                        'authors': volume_info.get('authors', []),  # Authors is a list
                    })
                print(f"Google Books API: Found {len(results)} results.")
                return results[:max_results]  # Limit to requested number

    except aiohttp.ClientResponseError as e:
        print(f"Google Books API Error (Search): HTTP Status {e.status} - {e.message}")
    except aiohttp.ClientConnectionError as e:
        print(f"Google Books API Error (Search): Connection Error - {e}")
    except json.JSONDecodeError:
        print(f"Google Books API Error (Search): Could not decode JSON response")
    except Exception as e:
        print(f"Google Books API Error (Search): An unexpected error occurred: {e}")

    return []  # Return empty list on error

async def get_book_details_by_id(book_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches detailed information for a specific book ID from Google Books API v1.
    Returns a dictionary with details or None if not found or error.
    """
    if not google_books_api_key:
        print("Error: Google Books API key not configured.")
        return None
    if not book_id:  # Prevent calling with empty ID
        return None

    detail_url = f"https://www.googleapis.com/books/v1/volumes/{book_id}"
    params = {'key': google_books_api_key}
    print(f"Google Books API: Getting details for book_id '{book_id}'")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(detail_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                volume_info = data.get('volumeInfo', {})
                isbn13 = None
                identifiers = volume_info.get('industryIdentifiers', [])
                for identifier in identifiers:
                    if identifier.get('type') == 'ISBN_13':
                        isbn13 = identifier.get('identifier')
                        break  # Prefer ISBN_13

                details = {
                    'id': data.get('id'),
                    'title': volume_info.get('title'),
                    'authors': volume_info.get('authors', []),
                    'description': volume_info.get('description'),
                    'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail') or \
                                volume_info.get('imageLinks', {}).get('smallThumbnail'),  # Get best available thumbnail
                    'isbn13': isbn13,
                    'categories': volume_info.get('categories', [])
                    # Add other fields if needed e.g., publishedDate, averageRating etc.
                }
                print(f"Google Books API: Details found for {book_id}.")
                return details

    except aiohttp.ClientResponseError as e:
        # Specifically handle 404 Not Found if needed
        if e.status == 404:
            print(f"Google Books API: Book ID '{book_id}' not found (404).")
        else:
            print(f"Google Books API Error (Details): HTTP Status {e.status} - {e.message}")
    except aiohttp.ClientConnectionError as e:
        print(f"Google Books API Error (Details): Connection Error - {e}")
    except json.JSONDecodeError:
        print(f"Google Books API Error (Details): Could not decode JSON response")
    except Exception as e:
        print(f"Google Books API Error (Details): An unexpected error occurred: {e}")

    return None  # Return None if details not found or error occurs

# --- End Mocked Interface ---

async def get_chatgpt_recommendations(
    preferences: Dict[str, Any],
    history: List[Dict[str, str]],
    max_recommendations: int = 5
) -> List[Dict[str, Any]]:
    """
    Calls ChatGPT to get book recommendation ideas based on user preferences and history.
    Input:
        preferences: Dict containing extracted entities like {'genre': 'sci-fi', 'liked_book': 'Dune'}
        history: List of recent conversation turns [{'role': 'user', 'content': '...'}, ...]
        max_recommendations: How many distinct book ideas to ask for.
    Output:
        List of dictionaries, each containing 'title', 'author', and 'reasoning' fields.
        Returns empty list on error.
    """
    if not client:  # Handle missing API key case
        print("Error: OpenAI client not initialized.")
        return []

    print(f"LLM: Getting recommendations based on preferences: {preferences}")
    
    # Convert preferences to a string for the prompt
    preferences_str = json.dumps(preferences)
    
    # --- Construct Prompt with JSON structure requirement ---
    system_prompt = """You are a helpful book recommendation assistant. Analyze the user's preferences and suggest relevant books.
Respond ONLY with a valid JSON object containing a 'recommendations' array. Do NOT include any introductory text or markdown formatting.
Each object in the array must have the following keys:
- "title": The exact book title.
- "author": The author(s) of the book.
- "reasoning": A short explanation (1-2 sentences) specifically explaining WHY this book fits the user's provided preferences."""

    user_prompt = f"""Based ONLY on the following user preferences: {preferences_str}
Suggest {max_recommendations} diverse book recommendations. Provide the title, author, and reasoning for each suggestion in the specified JSON format.
Make sure your response is a valid parsable JSON object with a 'recommendations' key containing the array of book recommendations."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    print(f"LLM: Sending prompt to ChatGPT requesting JSON structure")
    
    # --- Call OpenAI API with JSON mode ---
    try:
        response = await client.chat.completions.create(
            model="gpt-3.5-turbo-1106",  # Model with JSON mode support
            response_format={"type": "json_object"},  # Enable JSON mode
            messages=messages,
            temperature=0.6,  # Slightly lower temperature for more structured output
            max_tokens=250 * max_recommendations,  # Adjust tokens based on expected output size
            n=1,
            stop=None
        )
        content = response.choices[0].message.content
        print(f"LLM Raw JSON Response: {content}")

        # --- Parse JSON Response ---
        try:
            # Parse the JSON response
            data = json.loads(content)
            # Extract the recommendations list
            recommendations = data.get("recommendations", [])
            print(f"LLM Parsed Recommendations (JSON): {recommendations}")
            # Return the list of recommendation dictionaries
            return recommendations[:max_recommendations]
            
        except json.JSONDecodeError:
            print("LLM Error: Failed to parse JSON response from LLM")
            # Fallback to empty list if JSON parsing fails
        except TypeError:
            print("LLM Error: Response content might not be JSON string.")

    except openai.APIError as e:
        print(f"LLM Error: OpenAI API returned an API Error: {e}")
    except Exception as e:
        print(f"LLM Error: An unexpected error occurred: {e}")

    return []  # Return empty list on error

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)
