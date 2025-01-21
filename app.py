from flask import Flask, request, jsonify, render_template
import json
import redis
from datetime import datetime, timedelta
from combine_scraper import scrape_and_collect, find_relevant_matches
from difflib import SequenceMatcher
import os

app = Flask(__name__)

# Initialize Redis connection
redis_client = redis.Redis(host='redis-13931.c265.us-east-1-2.ec2.redns.redis-cloud.com',
    port=13931,
    decode_responses=True,
    username="default",
    password="q0wltEKsz3VM5rzH7po8S1ZYK9OINlCb",
)

# Helper function to check if queries are related
def are_queries_related(query1, query2):
    # Convert both to lowercase for case-insensitive comparison
    query1, query2 = query1.lower(), query2.lower()
    
    # Split queries into words
    words1 = set(query1.split())
    words2 = set(query2.split())
    
    # Check for common words or substrings
    common_words = words1 & words2
    
    # Check for partial matches using sequence matcher
    for w1 in words1:
        for w2 in words2:
            # Use sequence matcher to find similarity ratio
            similarity = SequenceMatcher(None, w1, w2).ratio()
            if similarity > 0.75:  # If words are 80% similar
                return True
                
    return bool(common_words) or \
           any(w1 in w2 or w2 in w1 for w1 in words1 for w2 in words2) or \
           query1 in query2 or query2 in query1

# Helper function to search database for matching queries
def search_db_for_query(query):
    matches = []
    # Get all search keys
    search_keys = redis_client.keys('search:*')
    
    for key in search_keys:
        stored_data = json.loads(redis_client.get(key))
        stored_query = stored_data.get('query')
        if are_queries_related(query, stored_query):
            results = stored_data.get('results', {})
            if 'matches' in results:
                matches.extend(results['matches'])
    
    if matches:
        return {
            'matches': matches
        }
    return None

@app.route('/')
def home():
    return render_template('Untitled-1.html')

@app.route('/get_past_results', methods=['GET'])
def get_past_results():
    try:
        past_results = {
            'matches': []
        }
        
        # Get last 10 searches sorted by timestamp
        search_keys = redis_client.keys('search:*')
        searches = []
        for key in search_keys:
            search_data = json.loads(redis_client.get(key))
            searches.append(search_data)
        
        # Sort by timestamp descending and take first 10
        searches.sort(key=lambda x: x['timestamp'], reverse=True)
        searches = searches[:10]

        if not searches:
            return jsonify({
                'success': False,
                'errorMessage': 'No past results found'
            })

        # Format the results
        for search in searches:
            query = search['query']
            # Use get() with default values for location and pincode
            location = search.get('location', '')
            pincode = search.get('pincode', '')
            results = search.get('results', {})
            matches = results.get('matches', [])
            
            if isinstance(matches, list):
                for match in matches:
                    if isinstance(match, dict):
                        match['search_query'] = query
                        match['location'] = location
                        match['pincode'] = pincode
                        past_results['matches'].append(match)

        print(f"Returning {len(past_results['matches'])} matches")
        
        return jsonify({
            'success': True,
            'results': past_results
        })

    except Exception as e:
        print(f"Database error: {str(e)}")
        return jsonify({
            'success': False,
            'errorMessage': f'Error loading past results: {str(e)}'
        }), 500

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query', '').strip()
    location = data.get('location', '').strip()
    pincode = data.get('pincode', '').strip()
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'No query provided',
            'errorMessage': 'Please enter a search term'
        }), 400

    try:
        # First check if we have related results in the database
        cached_results = search_db_for_query(query)
        
        if cached_results:
            print(f"Found cached results for query: {query}")
            # Add query, location and pincode to each match for display
            for match in cached_results['matches']:
                match['search_query'] = query
                match['location'] = location
                match['pincode'] = pincode
            
            return jsonify({
                'success': True,
                'results': cached_results,
                'query': query,
                'location': location,
                'pincode': pincode,
                'source': 'cache'
            })

        # If no cached results, run the scraper
        print(f"No cached results found, running scraper for query: {query}")
        scraped_data = scrape_and_collect(query, location, pincode)
        matches = find_relevant_matches(scraped_data["matches"], query)

        # Add query, location and pincode to each match for display
        for match in matches:
            match['search_query'] = query
            match['location'] = location
            match['pincode'] = pincode

        # Wrap matches in a dictionary format
        results = {'matches': matches}
        
        # Store results in Redis
        timestamp = datetime.now().isoformat()
        search_data = {
            'query': query,
            'location': location,
            'pincode': pincode,
            'timestamp': timestamp,
            'results': results
        }
        
        # Use timestamp as unique identifier in key
        redis_client.set(f'search:{timestamp}', json.dumps(search_data))
        
        return jsonify({
            'success': True,
            'results': results,
            'query': query,
            'location': location,
            'pincode': pincode,
            'source': 'scraper'
        })
        
    except Exception as e:
        print(f"Error during search: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'errorMessage': 'An error occurred while processing your request'
        }), 500

if __name__ == "__main__":
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 8080))
    host = os.getenv('HOST', '0.0.0.0')
    app.run(host=host, port=port)
